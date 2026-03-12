#!/bin/bash
set -e

echo "=========================================="
echo "  EPL Thesis Watcher"
echo "=========================================="

# Start the web control server in background
echo "[*] Starting web control server on port 5050..."
python /app/server.py &

# Start the main watcher
echo "[*] Starting thesis watcher..."
python /app/watcher.py
