FROM python:3.11-slim

# System deps for Playwright (Chromium)
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libpango-1.0-0 libcairo2 \
    fonts-liberation libappindicator3-1 \
    xvfb x11vnc fluxbox \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN chmod +x /app/entrypoint.sh

# Cookies & logs volume
VOLUME ["/app/cookies"]

# Web control panel
EXPOSE 5050

# VNC for browser visibility (optional, port 5900)
EXPOSE 5900

CMD ["/app/entrypoint.sh"]
