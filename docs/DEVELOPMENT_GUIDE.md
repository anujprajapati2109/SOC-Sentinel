# SOC Sentinel Development Guide

## Local Development

From `soc_server`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FLASK_CONFIG = "development"
$env:SERVER_HOST = "127.0.0.1"
$env:SERVER_PORT = "5000"
.\.venv\Scripts\python.exe app.py
```

Open:

```text
http://127.0.0.1:5000
```

## LAN Testing

Use a LAN bind address on the server:

```powershell
$env:FLASK_CONFIG = "development"
$env:SERVER_HOST = "0.0.0.0"
$env:SERVER_PORT = "5000"
$env:PUBLIC_URL = "http://<server-lan-ip>:5000"
.\.venv\Scripts\python.exe app.py
```

On each agent machine, set `agent/config.json` or `agent/dist/config.json`:

```json
{
  "server_url": "http://<server-lan-ip>:5000"
}
```

Open Windows Firewall for TCP `5000` only on trusted lab networks.

## Health Check

```powershell
Invoke-WebRequest http://127.0.0.1:5000/api/v1/health -UseBasicParsing
```

## Logs

Server logs are written to:

```text
soc_server/logs/application.log
soc_server/logs/access.log
soc_server/logs/error.log
```

Agent logs are written to:

```text
agent/logs/agent.log
agent/dist/logs/agent.log
```
