# SOC Sentinel AWS EC2 Deployment Guide

This guide documents the production deployment used for SOC Sentinel on AWS EC2 with Ubuntu 26.04, Python 3.14, Nginx, Gunicorn, systemd, Flask, and SQLite.

Set one deployment path and reuse it in every command:

```bash
export SOC_SENTINEL_HOME=/srv/soc-sentinel/current
export SOC_SENTINEL_REPO=https://github.com/anujprajapati2109/SOC-Sentinel.git
```

## Ubuntu Setup

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git nginx python3.14 python3.14-venv python3-pip ufw
```

## Dedicated User

```bash
sudo useradd --system --home /srv/soc-sentinel --shell /usr/sbin/nologin soc-sentinel || true
sudo mkdir -p "$(dirname "$SOC_SENTINEL_HOME")"
sudo chown -R soc-sentinel:soc-sentinel "$(dirname "$SOC_SENTINEL_HOME")"
```

## Git Clone

```bash
sudo -u soc-sentinel git clone "$SOC_SENTINEL_REPO" "$SOC_SENTINEL_HOME"
cd "$SOC_SENTINEL_HOME"
```

## Python Virtual Environment

```bash
sudo -u soc-sentinel python3.14 -m venv "$SOC_SENTINEL_HOME/.venv"
sudo -u soc-sentinel "$SOC_SENTINEL_HOME/.venv/bin/python" -m pip install --upgrade pip
sudo -u soc-sentinel "$SOC_SENTINEL_HOME/.venv/bin/pip" install -r "$SOC_SENTINEL_HOME/soc_server/requirements.txt"
```

## Environment

```bash
sudo cp "$SOC_SENTINEL_HOME/.env.example" "$SOC_SENTINEL_HOME/.env"
sudo nano "$SOC_SENTINEL_HOME/.env"
sudo chown soc-sentinel:soc-sentinel "$SOC_SENTINEL_HOME/.env"
sudo chmod 600 "$SOC_SENTINEL_HOME/.env"
```

Minimum production values:

```text
SOC_SENTINEL_ENV=production
SOC_SENTINEL_HOME=/srv/soc-sentinel/current
SECRET_KEY=<generated-secret>
DATABASE_URL=
DATABASE_PATH=soc_server/database/soc_sentinel.db
LOG_DIR=soc_server/logs
HOST=127.0.0.1
PORT=5000
LOG_LEVEL=INFO
SERVER_URL=http://<public-ip-or-domain>
SESSION_TIMEOUT=3600
```

Generate a secret:

```bash
python3.14 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

## Gunicorn

The WSGI entrypoint is:

```text
soc_server/wsgi.py -> application
```

Run manually:

```bash
cd "$SOC_SENTINEL_HOME/soc_server"
"$SOC_SENTINEL_HOME/.venv/bin/gunicorn" \
  --workers 3 \
  --bind 127.0.0.1:5000 \
  --access-logfile - \
  --error-logfile - \
  --timeout 120 \
  wsgi:application
```

## systemd

Install the systemd template after replacing `__SOC_SENTINEL_HOME__`:

```bash
sudo sed "s#__SOC_SENTINEL_HOME__#$SOC_SENTINEL_HOME#g" \
  "$SOC_SENTINEL_HOME/deploy/systemd/soc-sentinel.service" \
  | sudo tee /etc/systemd/system/soc-sentinel.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable soc-sentinel
sudo systemctl restart soc-sentinel
sudo systemctl status soc-sentinel --no-pager
```

Confirm automatic boot startup is enabled:

```bash
systemctl is-enabled soc-sentinel
```

## Nginx

Install the Nginx template after replacing `__SOC_SENTINEL_HOME__`:

```bash
sudo sed "s#__SOC_SENTINEL_HOME__#$SOC_SENTINEL_HOME#g" \
  "$SOC_SENTINEL_HOME/deploy/nginx/soc-sentinel.conf" \
  | sudo tee /etc/nginx/sites-available/soc-sentinel > /dev/null

sudo ln -sf /etc/nginx/sites-available/soc-sentinel /etc/nginx/sites-enabled/soc-sentinel
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
```

For a DNS name, edit `server_name` in `/etc/nginx/sites-available/soc-sentinel`.

## Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

AWS security group:

- TCP 22 from your admin IP only.
- TCP 80 from the internet.
- TCP 443 from the internet when HTTPS is enabled.
- Do not expose TCP 5000 publicly.

## Health Checks

```bash
curl http://127.0.0.1:5000/health
curl http://<public-ip-or-domain>/health
```

Expected result includes:

```json
{
  "status": "ok",
  "application_mode": "production",
  "database_status": "online"
}
```

## Updating

```bash
cd "$SOC_SENTINEL_HOME"
sudo -u soc-sentinel git pull
sudo -u soc-sentinel "$SOC_SENTINEL_HOME/.venv/bin/pip" install -r "$SOC_SENTINEL_HOME/soc_server/requirements.txt"
sudo systemctl restart soc-sentinel
sudo systemctl reload nginx
```

## Restarting

```bash
sudo systemctl restart soc-sentinel
sudo systemctl status soc-sentinel --no-pager
sudo nginx -t
sudo systemctl reload nginx
```

## Logs

```bash
sudo journalctl -u soc-sentinel -f
sudo tail -f "$SOC_SENTINEL_HOME/soc_server/logs/application.log"
sudo tail -f "$SOC_SENTINEL_HOME/soc_server/logs/error.log"
sudo tail -f "$SOC_SENTINEL_HOME/soc_server/logs/access.log"
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

```bash
sudo systemctl status soc-sentinel --no-pager
sudo journalctl -u soc-sentinel -n 100 --no-pager
ss -ltnp | grep 5000
sudo nginx -t
curl http://127.0.0.1:5000/health
```

Common failures:

- `502 Bad Gateway`: Gunicorn is not running, or Nginx points at the wrong port.
- `database error`: database path is wrong, or `soc-sentinel` lacks write permission.
- static files missing: Nginx static alias was installed with the wrong `SOC_SENTINEL_HOME`.
- placeholder public URL: set `SERVER_URL` in `.env`, or access through Nginx so Flask can infer the public host.

## Deployment Verification Checklist

- `nginx` is enabled and active.
- `soc-sentinel.service` is enabled and active.
- Gunicorn is listening only on `127.0.0.1:5000`.
- Nginx is the only public HTTP entry point.
- `/health` returns `status: ok`.
- Dashboard loads from the EC2 public IP or domain.
- Static CSS and JavaScript load with HTTP 200.
- `.env` contains a real `SECRET_KEY`.
- `.env` contains a real `SERVER_URL` or the dashboard correctly infers the request URL.
- Windows agent config points to the public deployment URL.
