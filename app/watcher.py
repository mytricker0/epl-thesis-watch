"""
EPL Thesis Watcher
Monitors https://eplapps.info.ucl.ac.be/thesis/list every 10 minutes.
- If forbidden/session expired → opens Playwright browser for re-login
- If thesis list appears → spams notifications every 2 min until user replies STOP
- Daily "still waiting" message at 9:00 AM
"""

import os
import json
import time
import asyncio
import logging
import smtplib
import requests
import schedule
import threading
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright

# ─── CONFIG ────────────────────────────────────────────────────────────────────
TARGET_URL       = "https://eplapps.info.ucl.ac.be/thesis/list"
LOGIN_URL        = "https://eplapps.info.ucl.ac.be/"
COOKIES_FILE     = "/app/cookies/session.json"
STOP_FILE        = "/app/cookies/STOP"

CALLMEBOT_PHONE  = os.environ["CALLMEBOT_PHONE"]    # e.g. +32477123456
CALLMEBOT_APIKEY = os.environ["CALLMEBOT_APIKEY"]   # from callmebot.com

GMAIL_USER       = os.environ["GMAIL_USER"]         # your@gmail.com
GMAIL_APP_PASS   = os.environ["GMAIL_APP_PASS"]     # 16-char app password
NOTIFY_EMAIL     = os.environ["NOTIFY_EMAIL"]        # where to send alerts (can be same)

CHECK_INTERVAL_MIN   = 10
SPAM_INTERVAL_MIN    = 2
DAILY_REPORT_TIME    = "09:00"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/cookies/watcher.log")
    ]
)
log = logging.getLogger(__name__)

# ─── STATE ─────────────────────────────────────────────────────────────────────
spam_active = False
spam_thread = None

# ─── COOKIES ───────────────────────────────────────────────────────────────────
def load_cookies() -> list:
    if Path(COOKIES_FILE).exists():
        with open(COOKIES_FILE) as f:
            return json.load(f)
    return []

def save_cookies(cookies: list):
    Path(COOKIES_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    log.info("Cookies saved.")

def cookies_to_requests(cookies: list) -> dict:
    return {c["name"]: c["value"] for c in cookies}

# ─── NOTIFICATIONS ─────────────────────────────────────────────────────────────
def send_whatsapp(message: str):
    try:
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={CALLMEBOT_PHONE}"
            f"&text={requests.utils.quote(message)}"
            f"&apikey={CALLMEBOT_APIKEY}"
        )
        r = requests.get(url, timeout=15)
        log.info(f"WhatsApp sent: {r.status_code}")
    except Exception as e:
        log.error(f"WhatsApp error: {e}")

def send_email(subject: str, body: str):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = NOTIFY_EMAIL
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
        log.info("Email sent.")
    except Exception as e:
        log.error(f"Email error: {e}")

def notify(subject: str, message: str):
    send_whatsapp(message)
    send_email(subject, f"<p>{message.replace(chr(10), '<br>')}</p>")

# ─── SPAM LOOP ─────────────────────────────────────────────────────────────────
def spam_loop():
    global spam_active
    log.info("🚨 Spam loop started!")
    count = 0
    while spam_active:
        if Path(STOP_FILE).exists():
            log.info("STOP file detected, ending spam.")
            spam_active = False
            Path(STOP_FILE).unlink(missing_ok=True)
            send_whatsapp("✅ Got it! Spam stopped. Good luck with your thesis topic! 🎓")
            break
        count += 1
        msg = (
            f"🚨 ALERT #{count} — EPL THESIS LIST IS NOW AVAILABLE! 🎓\n"
            f"👉 {TARGET_URL}\n"
            f"Reply STOP to this number via CallMeBot or create the STOP file to silence."
        )
        notify("🚨 EPL THESIS LIST AVAILABLE NOW!", msg)
        time.sleep(SPAM_INTERVAL_MIN * 60)

def start_spam():
    global spam_active, spam_thread
    if spam_active:
        return
    spam_active = True
    # Remove any leftover STOP file
    Path(STOP_FILE).unlink(missing_ok=True)
    spam_thread = threading.Thread(target=spam_loop, daemon=True)
    spam_thread.start()

# ─── LOGIN VIA PLAYWRIGHT ──────────────────────────────────────────────────────
def do_playwright_login():
    """
    Opens a visible Chromium browser so the user can log in manually.
    Once logged in, captures cookies and saves them.
    """
    log.info("Opening browser for manual login...")
    notify(
        "🔐 EPL Watcher: Login Required",
        (
            "⚠️ Your EPL session has expired!\n"
            "A browser window is opening on the server for you to log in.\n"
            "If you're running headless/remote, check the VNC or use the "
            "DISPLAY env var.\n"
            f"Login URL: {LOGIN_URL}"
        )
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LOGIN_URL)

        log.info("Waiting for user to log in... (watching for /thesis/ in URL or up to 5 min)")
        try:
            # Wait until the URL contains 'thesis' or a known post-login path
            page.wait_for_url("**/thesis/**", timeout=300_000)
        except Exception:
            log.warning("Timed out waiting for login. Trying to grab cookies anyway.")

        # Extra wait to ensure all cookies are set
        time.sleep(3)
        cookies = context.cookies()
        browser.close()

    if cookies:
        save_cookies(cookies)
        notify(
            "✅ EPL Watcher: Cookies Updated",
            "✅ Login successful! Cookies updated. Still watching for thesis topics... 👀"
        )
        log.info("Login complete, cookies saved.")
    else:
        log.error("No cookies captured after login!")

# ─── PAGE CHECK ────────────────────────────────────────────────────────────────
def check_page():
    global spam_active
    log.info(f"Checking {TARGET_URL}...")

    cookies = load_cookies()
    if not cookies:
        log.warning("No cookies found. Triggering login.")
        do_playwright_login()
        return

    session = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

    try:
        resp = session.get(TARGET_URL, timeout=20, allow_redirects=True)
        html = resp.text
        log.info(f"Status: {resp.status_code} | URL: {resp.url}")
    except Exception as e:
        log.error(f"Request failed: {e}")
        return

    # ── Detect session expiry / redirect to login ──
    login_indicators = [
        "login" in resp.url.lower(),
        "sign in" in html.lower(),
        "connexion" in html.lower(),
        resp.status_code in (401, 403) and "forbidden" in html.lower() and "login" in html.lower(),
    ]

    # ── Detect thesis list visible ──
    thesis_visible = (
        resp.status_code == 200
        and "forbidden" not in html.lower()
        and ("thesis" in html.lower() or "mémoire" in html.lower() or "master" in html.lower())
        and "The list of master thesis topics is not available" not in html
    )

    if any(login_indicators):
        log.warning("Session expired — need to re-login.")
        do_playwright_login()

    elif thesis_visible:
        log.info("🎉 THESIS LIST IS AVAILABLE!")
        if not spam_active:
            start_spam()

    else:
        log.info("Still forbidden / not available yet.")

# ─── DAILY STATUS ──────────────────────────────────────────────────────────────
def daily_status():
    if spam_active:
        return  # no need for "still waiting" if we're already spamming
    msg = (
        f"📅 Daily EPL Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"❌ Thesis list still not available.\n"
        f"Still checking every {CHECK_INTERVAL_MIN} min. I'll alert you the moment it's up! 👀"
    )
    notify("📅 EPL Watcher: Still Waiting", msg)

# ─── STOP ENDPOINT (simple file-based) ────────────────────────────────────────
def watch_stop_file():
    """Poll for STOP file in a background thread."""
    global spam_active
    while True:
        if Path(STOP_FILE).exists() and spam_active:
            log.info("STOP file found, stopping spam.")
            spam_active = False
        time.sleep(10)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("EPL Thesis Watcher starting up...")
    log.info(f"Target: {TARGET_URL}")
    log.info(f"Check interval: {CHECK_INTERVAL_MIN} min")
    log.info("=" * 60)

    # Start STOP file watcher
    stop_watcher = threading.Thread(target=watch_stop_file, daemon=True)
    stop_watcher.start()

    # Run once immediately
    check_page()

    # Schedule recurring checks
    schedule.every(CHECK_INTERVAL_MIN).minutes.do(check_page)
    schedule.every().day.at(DAILY_REPORT_TIME).do(daily_status)

    log.info("Scheduler running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
