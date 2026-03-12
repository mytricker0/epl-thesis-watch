# 📡 EPL Thesis Watcher

Monitors `https://eplapps.info.ucl.ac.be/thesis/list` and alerts you the **instant** the master thesis list goes live — via WhatsApp + Email.

---

## 🗂️ Project Structure

```
epl-watcher/
├── app/
│   ├── watcher.py        # Main monitoring loop
│   ├── server.py         # Web control panel (STOP button)
│   ├── entrypoint.sh     # Starts both services
│   └── requirements.txt
├── cookies/              # Auto-created — stores session + logs
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Setup (one-time)

### 1. Get your CallMeBot API key (free WhatsApp notifications)

1. Save the number **+34 644 44 00 96** in your phone contacts as "CallMeBot"
2. Send this message via WhatsApp to that number:
   ```
   I allow callmebot to send me messages
   ```
3. You'll receive a reply with your personal **API key**

### 2. Get a Gmail App Password

1. Enable 2-Factor Authentication on your Google account
2. Go to → https://myaccount.google.com/apppasswords
3. Create a new app password (name it "EPL Watcher")
4. Copy the 16-character password

### 3. Edit docker-compose.yml

Fill in your details in the `environment` section:

```yaml
CALLMEBOT_PHONE:   "+32477123456"        # your WhatsApp number
CALLMEBOT_APIKEY:  "1234567"             # from step 1
GMAIL_USER:        "you@gmail.com"
GMAIL_APP_PASS:    "abcd efgh ijkl mnop" # from step 2
NOTIFY_EMAIL:      "you@gmail.com"
```

### 4. First login — import your session cookies

Before the watcher can check the page, it needs your UCLouvain session.

**Option A — Automatic (recommended):**
```bash
docker compose up --build
```
On first run with no cookies, the watcher will:
1. Send you a WhatsApp + email saying "login needed"
2. Open a Chromium browser window (visible via VNC — see below)
3. Wait for you to log in manually
4. Save your cookies automatically

**Option B — Export cookies manually from your browser:**
1. Install the [Cookie-Editor](https://cookie-editor.cgagnier.ca/) browser extension
2. Visit `https://eplapps.info.ucl.ac.be/thesis/list` while logged in
3. Click the extension → Export → Copy JSON
4. Paste into `cookies/session.json`
5. Start the watcher: `docker compose up --build`

---

## 🚀 Running

```bash
# Start (detached, runs 24/7)
docker compose up -d --build

# View live logs
docker compose logs -f

# Stop the container
docker compose down
```

---

## 📺 Viewing the browser (when login is needed)

The container runs a virtual display with VNC. Connect with any VNC client:

- **Address:** `YOUR_SERVER_IP:5900`
- **Password:** none (open)

Free VNC clients:
- Mac: built-in Screen Sharing, or [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)
- Windows: [TightVNC](https://www.tightvnc.com/)
- Phone: [VNC Viewer app](https://www.realvnc.com/en/connect/download/viewer/android/)

> ⚠️ If your server is remote, tunnel VNC securely:
> ```bash
> ssh -L 5900:localhost:5900 user@your-server
> ```
> Then connect to `localhost:5900` from your local machine.

---

## 🛑 Stopping the spam

When the thesis list appears, you'll get notified **every 2 minutes** until you stop it.

**From your phone browser:**
```
http://YOUR_SERVER_IP:5050/stop
```

**From the server directly:**
```bash
touch cookies/STOP
```

---

## 📊 Web Control Panel

Visit `http://YOUR_SERVER_IP:5050` for a simple control panel.

| Endpoint | Description |
|---|---|
| `GET /` | Control panel with STOP button |
| `POST /stop` | Stop spam notifications |
| `GET /status` | JSON status |
| `GET /health` | Health check |

---

## 📅 Notification Schedule

| Event | Action |
|---|---|
| Thesis list appears | WhatsApp + Email every **2 minutes** until STOP |
| Session expired | WhatsApp + Email → browser opens for re-login |
| After re-login | WhatsApp "cookies updated, still watching" |
| Every day at 9:00 AM | WhatsApp + Email "still not available" |

---

## 🔧 Troubleshooting

**Container crashes immediately:**
```bash
docker compose logs epl-watcher
```

**No WhatsApp received:**
- Make sure you completed the CallMeBot activation (step 1)
- Check the number format includes `+` and country code

**Browser doesn't open:**
- Connect via VNC to `YOUR_SERVER:5900` to see what's happening
- Check logs: `docker compose logs -f`
