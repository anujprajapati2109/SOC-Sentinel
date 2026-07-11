# Oracle Cloud Deployment Guide

This guide targets an Oracle Cloud Infrastructure Ubuntu VM.

## 1. Create VM

Use Ubuntu LTS with a public IP. Add an ingress rule in the OCI Security List or
Network Security Group:

| Port | Purpose |
| --- | --- |
| 22 | SSH |
| 80 | HTTP for Let's Encrypt |
| 443 | HTTPS |

Do not expose port `5000` publicly if Nginx is used.

## 2. Install Runtime

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
```

## 3. Deploy Application

```bash
git clone <your-repository-url> soc-sentinel
cd soc-sentinel/soc_server
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## 4. Configure Environment

```bash
export FLASK_CONFIG=production
export SECRET_KEY='<long-random-secret>'
export SERVER_HOST=127.0.0.1
export SERVER_PORT=5000
export PUBLIC_URL='https://soc.example.com'
```

For PostgreSQL:

```bash
export DATABASE_URL='postgresql://soc_user:strong-password@db-host:5432/soc_sentinel'
```

For SQLite, omit `DATABASE_URL`.

## 5. Run Gunicorn

```bash
./.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 wsgi:application
```

For a real deployment, run this under `systemd`.

## 6. Configure Nginx

Create `/etc/nginx/sites-available/soc-sentinel` using the Nginx config from
`DEPLOYMENT_GUIDE.md`, then enable it:

```bash
sudo ln -s /etc/nginx/sites-available/soc-sentinel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 7. HTTPS

Use Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d soc.example.com
```

## 8. Agent Configuration

On each endpoint:

```json
{
  "server_url": "https://soc.example.com"
}
```

The agent does not need code changes when moving from localhost to Oracle Cloud.
