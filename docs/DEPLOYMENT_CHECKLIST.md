# SOC Sentinel Deployment Verification Checklist

Use this checklist before exposing SOC Sentinel on the internet.

## Repository

- [ ] Deployment branch is up to date.
- [ ] `.env` exists on the server and is not committed.
- [ ] No logs, databases, virtual environments, or binaries are committed.
- [ ] `soc_server/requirements.txt` installs successfully.

## AWS EC2

- [ ] Instance is running Ubuntu 26.04 LTS.
- [ ] Security group allows SSH only from trusted admin IPs.
- [ ] Security group allows HTTP and HTTPS.
- [ ] Port `5000` is not open publicly.
- [ ] System packages are updated.

## Python

- [ ] Python 3.14 is installed.
- [ ] Virtual environment exists at `/opt/soc-sentinel/SOC-Sentinel/.venv`.
- [ ] Production dependencies are installed.
- [ ] Gunicorn is available inside the virtual environment.

## Configuration

- [ ] `SOC_SENTINEL_ENV=production`.
- [ ] `SECRET_KEY` is a strong generated value.
- [ ] `DATABASE_URL` points to the intended database.
- [ ] `HOST=127.0.0.1`.
- [ ] `PORT=5000`.
- [ ] `SERVER_URL` uses the public HTTPS URL.
- [ ] `LOG_LEVEL=INFO` or stricter.
- [ ] `SESSION_TIMEOUT` is set.

## Service

- [ ] Dedicated `soc-sentinel` user exists.
- [ ] `soc-sentinel.service` is installed.
- [ ] `systemctl enable soc-sentinel` has been run.
- [ ] `systemctl status soc-sentinel` shows active.
- [ ] Service restarts automatically after failure.

## Nginx

- [ ] Nginx site config is installed.
- [ ] `server_name` is set to the real domain.
- [ ] `nginx -t` passes.
- [ ] Reverse proxy points to `127.0.0.1:5000`.
- [ ] Static file caching is enabled.
- [ ] Compression is enabled.
- [ ] Security headers are present.

## HTTPS

- [ ] TLS certificate is installed.
- [ ] HTTP redirects to HTTPS if configured.
- [ ] `SERVER_URL` and `PUBLIC_URL` use `https://`.

## Health

- [ ] `curl http://127.0.0.1:5000/health` returns `status: ok`.
- [ ] `curl https://your-domain.example.com/health` returns `status: ok`.
- [ ] `database` reports `online`.
- [ ] Dashboard loads through the public URL.

## Agent

- [ ] Agent `server_url` points to the production HTTPS URL.
- [ ] New endpoint registration succeeds.
- [ ] Heartbeats update endpoint status.
- [ ] Telemetry reaches the dashboard.

## Operations

- [ ] Application log exists.
- [ ] Error log exists.
- [ ] Access log exists.
- [ ] Log rotation settings are configured.
- [ ] Backup strategy is documented for the selected database.
