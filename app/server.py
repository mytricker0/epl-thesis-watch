"""
Simple HTTP server so you can stop the spam from your phone browser.
Visit http://YOUR_SERVER_IP:5050/stop to drop the STOP file.
"""

from flask import Flask, jsonify, render_template_string
from pathlib import Path

app = Flask(__name__)
STOP_FILE = "/app/cookies/STOP"
COOKIES_FILE = "/app/cookies/session.json"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EPL Watcher Control</title>
  <style>
    body { font-family: sans-serif; background: #0d1b2a; color: white;
           display: flex; flex-direction: column; align-items: center;
           justify-content: center; height: 100vh; margin: 0; }
    h1 { color: #00e5b0; }
    .btn { padding: 20px 40px; font-size: 1.4rem; border: none;
           border-radius: 12px; cursor: pointer; margin: 10px; }
    .stop  { background: #e74c3c; color: white; }
    .status { background: #2980b9; color: white; }
    p { color: #aaa; text-align: center; max-width: 400px; }
  </style>
</head>
<body>
  <h1>📡 EPL Watcher</h1>
  <p>{{ status }}</p>
  <form action="/stop" method="post">
    <button class="btn stop" type="submit">🛑 STOP Spam</button>
  </form>
  <a href="/status"><button class="btn status" type="button">📊 Check Status</button></a>
</body>
</html>
"""

@app.route("/")
def index():
    stop_exists = Path(STOP_FILE).exists()
    status = "🚨 Spam is ACTIVE — click STOP to silence." if not stop_exists else "✅ Spam is stopped."
    return render_template_string(HTML, status=status)

@app.route("/stop", methods=["GET", "POST"])
def stop():
    Path(STOP_FILE).touch()
    return render_template_string(HTML, status="✅ STOP signal sent! Spam will stop within 30 seconds.")

@app.route("/status")
def status():
    stop_exists = Path(STOP_FILE).exists()
    cookies_exist = Path(COOKIES_FILE).exists()
    return jsonify({
        "spam_stopped": stop_exists,
        "cookies_present": cookies_exist,
        "message": "Spam stopped" if stop_exists else "Spam active or waiting"
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
