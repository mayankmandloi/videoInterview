#!/bin/bash
# Run this script on the Azure VM as root or with sudo
# Usage: bash setup.sh

set -e

APP_DIR=/home/azureuser/videoInterview
SERVICE_USER=azureuser

echo "==> Updating system packages..."
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3.11-dev git nginx

echo "==> Cloning repo (skip if already done)..."
if [ ! -d "$APP_DIR" ]; then
  git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git "$APP_DIR"
  chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
fi

echo "==> Creating virtualenv..."
cd "$APP_DIR"
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> Setting up .env (make sure it exists with all keys filled)..."
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: $APP_DIR/.env not found. Copy your .env file to the VM first."
  exit 1
fi

echo "==> Updating APP_BASE_URL in .env to match your VM public IP or domain..."
# Edit .env manually or use sed to set APP_BASE_URL:
# sed -i 's|APP_BASE_URL=.*|APP_BASE_URL=http://YOUR_VM_IP|' "$APP_DIR/.env"

echo "==> Installing systemd services..."
cp deploy/videoInterview-web.service /etc/systemd/system/
cp deploy/videoInterview-agent.service /etc/systemd/system/
systemctl daemon-reload

systemctl enable videoInterview-web
systemctl enable videoInterview-agent
systemctl restart videoInterview-web
systemctl restart videoInterview-agent

echo "==> Service status:"
systemctl status videoInterview-web --no-pager
systemctl status videoInterview-agent --no-pager

echo "==> Configuring nginx reverse proxy on port 80..."
cat > /etc/nginx/sites-available/videoInterview <<'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/videoInterview /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "==> Done! App is running at http://$(curl -s ifconfig.me)"
echo "    Logs: journalctl -u videoInterview-web -f"
echo "    Agent logs: journalctl -u videoInterview-agent -f"
