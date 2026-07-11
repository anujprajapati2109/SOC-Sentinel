# SOC Sentinel Deployment Guide

SOC Sentinel v0.9.0 supports localhost, LAN, and cloud deployment through
configuration. This release does not implement authentication, so do not expose
it directly to the public internet without an external access control layer.

## Windows Production With Waitress

From `soc_server`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FLASK_CONFIG = "production"
$env:SECRET_KEY = "<long-random-secret>"
$env:SERVER_HOST = "0.0.0.0"
$env:SERVER_PORT = "5000"
$env:PUBLIC_URL = "https://soc.example.com"
.\.venv\Scripts\waitress-serve.exe --listen=0.0.0.0:5000 wsgi:application
```

## Linux Production With Gunicorn

From `soc_server`:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
export FLASK_CONFIG=production
export SECRET_KEY='<long-random-secret>'
export SERVER_HOST=0.0.0.0
export SERVER_PORT=5000
export PUBLIC_URL='https://soc.example.com'
./.venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 wsgi:application
```

Use `127.0.0.1:5000` behind Nginx. Use `0.0.0.0:5000` only for controlled LAN
testing or when a firewall restricts access.

## HTTPS Behind Nginx

Example reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name soc.example.com;

    ssl_certificate /etc/letsencrypt/live/soc.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/soc.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port 443;
    }
}
```

Set:

```bash
export PUBLIC_URL='https://soc.example.com'
```

## PostgreSQL

Set:

```bash
export DATABASE_URL='postgresql://soc_user:strong-password@127.0.0.1:5432/soc_sentinel'
```

SQLite backup download is disabled when PostgreSQL is configured. Use:

```bash
pg_dump "$DATABASE_URL" > soc_sentinel.sql
```

or provider-native snapshots.

## Health Endpoint

```text
GET /api/v1/health
```

Returns application status, version, database connectivity, uptime, mode, and
public URL.
