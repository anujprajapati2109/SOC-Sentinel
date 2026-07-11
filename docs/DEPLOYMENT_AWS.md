# SOC Sentinel AWS EC2 Deployment Guide

This guide prepares SOC Sentinel for production deployment on AWS EC2 running Ubuntu 26.04 LTS, Python 3.14, Gunicorn, and Nginx.

The repository is prepared only. Deployment still requires you to create the EC2 instance, DNS record, firewall rules, and production secrets.

## 1. EC2 Baseline

Recommended starting point:

- Ubuntu 26.04 LTS
- 2 vCPU
- 2 GB RAM minimum
- 20 GB disk minimum
- Security group allowing SSH, HTTP, and HTTPS

Update the host:

```bash
sudo apt update
sudo apt upgrade -y
```

Install system packages:

```bash
sudo apt install -y git nginx python3.14 python3.14-venv python3-pip ufw
```

## 2. Dedicated User

Create a non-login service user:

```bash
sudo useradd --system --home /opt/soc-sentinel --shell /usr/sbin/nologin soc-sentinel
sudo mkdir -p /opt/soc-sentinel
sudo chown soc-sentinel:soc-sentinel /opt/soc-sentinel
```

## 3. Clone Repository

```bash
sudo -u soc-sentinel git clone https://github.com/anujprajapati2109/SOC-Sentinel.git /opt/soc-sentinel/SOC-Sentinel
cd /opt/soc-sentinel/SOC-Sentinel
```

## 4. Python Virtual Environment

```bash
sudo -u soc-sentinel python3.14 -m venv /opt/soc-sentinel/SOC-Sentinel/.venv
sudo -u soc-sentinel /opt/soc-sentinel/SOC-Sentinel/.venv/bin/python -m pip install --upgrade pip
sudo -u soc-sentinel /opt/soc-sentinel/SOC-Sentinel/.venv/bin/pip install -r /opt/soc-sentinel/SOC-Sentinel/soc_server/requirements.txt
```

## 5. Environment Configuration

Create the production environment file:

```bash
sudo cp /opt/soc-sentinel/SOC-Sentinel/.env.example /opt/soc-sentinel/SOC-Sentinel/.env
sudo nano /opt/soc-sentinel/SOC-Sentinel/.env
sudo chown soc-sentinel:soc-sentinel /opt/soc-sentinel/SOC-Sentinel/.env
sudo chmod 600 /opt/soc-sentinel/SOC-Sentinel/.env
```

Minimum production values:

```text
SOC_SENTINEL_ENV=production
SECRET_KEY=<generate-a-long-random-secret>
DATABASE_URL=sqlite:////opt/soc-sentinel/SOC-Sentinel/soc_server/database/soc_sentinel.db
HOST=127.0.0.1
PORT=5000
LOG_LEVEL=INFO
SERVER_URL=https://your-domain.example.com
SESSION_TIMEOUT=3600
```

Generate a secret:

```bash
python3.14 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

For PostgreSQL, use a SQLAlchemy URL such as:

```text
DATABASE_URL=postgresql://soc_user:strong-password@db-host:5432/soc_sentinel
```

## 6. Systemd Service

Install the service unit:

```bash
sudo cp /opt/soc-sentinel/SOC-Sentinel/deploy/systemd/soc-sentinel.service /etc/systemd/system/soc-sentinel.service
sudo systemctl daemon-reload
sudo systemctl enable soc-sentinel
sudo systemctl start soc-sentinel
```

Check status:

```bash
sudo systemctl status soc-sentinel --no-pager
journalctl -u soc-sentinel -f
```

## 7. Nginx Reverse Proxy

Install the Nginx site:

```bash
sudo cp /opt/soc-sentinel/SOC-Sentinel/deploy/nginx/soc-sentinel.conf /etc/nginx/sites-available/soc-sentinel
sudo ln -s /etc/nginx/sites-available/soc-sentinel /etc/nginx/sites-enabled/soc-sentinel
sudo nginx -t
sudo systemctl reload nginx
```

Edit `server_name` before production use:

```bash
sudo nano /etc/nginx/sites-available/soc-sentinel
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example.com
```

After HTTPS is enabled, set:

```text
SERVER_URL=https://your-domain.example.com
PUBLIC_URL=https://your-domain.example.com
```

Restart:

```bash
sudo systemctl restart soc-sentinel
```

## 9. Firewall

Enable UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

AWS security group should allow:

- TCP 22 from your admin IP only
- TCP 80 from the internet
- TCP 443 from the internet

Do not expose port `5000` publicly. Gunicorn should bind to `127.0.0.1:5000`.

## 10. Health Check

Local check:

```bash
curl http://127.0.0.1:5000/health
```

Public check:

```bash
curl https://your-domain.example.com/health
```

Expected fields:

```json
{
  "status": "ok",
  "version": "0.9.0",
  "uptime": "1 min",
  "database": "online"
}
```

## 11. Running Manually

Manual Linux startup:

```bash
cd /opt/soc-sentinel/SOC-Sentinel
chmod +x start.sh
./start.sh
```

Systemd is preferred for production.

## 12. Updating

```bash
cd /opt/soc-sentinel/SOC-Sentinel
sudo -u soc-sentinel git pull
sudo -u soc-sentinel ./.venv/bin/pip install -r soc_server/requirements.txt
sudo systemctl restart soc-sentinel
```

## 13. Restarting

```bash
sudo systemctl restart soc-sentinel
sudo systemctl status soc-sentinel --no-pager
```

Reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 14. Logs

Application logs:

```bash
sudo ls -lah /opt/soc-sentinel/SOC-Sentinel/soc_server/logs
sudo tail -f /opt/soc-sentinel/SOC-Sentinel/soc_server/logs/application.log
sudo tail -f /opt/soc-sentinel/SOC-Sentinel/soc_server/logs/error.log
sudo tail -f /opt/soc-sentinel/SOC-Sentinel/soc_server/logs/access.log
```

System service logs:

```bash
journalctl -u soc-sentinel -f
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 15. Troubleshooting

Check service startup:

```bash
sudo systemctl status soc-sentinel --no-pager
journalctl -u soc-sentinel -n 100 --no-pager
```

Check Gunicorn port:

```bash
ss -ltnp | grep 5000
```

Check Nginx config:

```bash
sudo nginx -t
```

Check database file permissions:

```bash
sudo chown -R soc-sentinel:soc-sentinel /opt/soc-sentinel/SOC-Sentinel/soc_server/database
```

Common failures:

- `502 Bad Gateway`: Gunicorn is not running or Nginx points to the wrong port.
- `database error`: database path is wrong or service user lacks permission.
- static files missing: Nginx `alias` path does not match the clone path.
- health endpoint fails: check `.env`, service logs, and database connectivity.

## Deployment Verification Checklist

- EC2 security group exposes only SSH, HTTP, and HTTPS.
- `soc-sentinel` Linux user exists.
- Repository is cloned under `/opt/soc-sentinel/SOC-Sentinel`.
- `.env` exists and is not committed to Git.
- `SECRET_KEY` is changed from the example value.
- `SERVER_URL` uses the real public URL.
- Python virtual environment is created.
- `soc_server/requirements.txt` installs successfully.
- `soc-sentinel.service` is enabled.
- `systemctl status soc-sentinel` is healthy.
- Nginx config passes `nginx -t`.
- Public `/health` returns `status: ok`.
- Dashboard opens through HTTPS.
- Agent config points to the production `SERVER_URL`.
- Port `5000` is not open to the internet.
