# SOC Sentinel Configuration Reference

SOC Sentinel v0.9.0 is configured through environment variables. Do not edit
Python source code to switch between localhost, LAN, or cloud deployments.

## Server Variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `FLASK_CONFIG` | No | `development` | `development` or `production`. |
| `SECRET_KEY` | Production | `change-this-secret-key-before-production` | Flask session signing secret. Set a long random value in production. |
| `DATABASE_URL` | No | local SQLite | SQLAlchemy database URI. Supports SQLite and PostgreSQL. |
| `SERVER_HOST` | No | `127.0.0.1` | Bind address for `python app.py`. Use `0.0.0.0` for LAN/cloud VM binding. |
| `SERVER_PORT` | No | `5000` | Server port. |
| `PUBLIC_URL` | Production | `http://<host>:<port>` | External URL agents and users should use. Example: `https://soc.example.com`. |
| `LOG_LEVEL` | No | `INFO` | Python logging level. |

Legacy `SOC_SENTINEL_HOST` and `SOC_SENTINEL_PORT` still work, but new
deployments should use `SERVER_HOST` and `SERVER_PORT`.

## Database URLs

SQLite default:

```text
sqlite:///G:/SOCET/SEM 7/Minor Project/SOC-Sentinel/soc_server/database/soc_sentinel.db
```

PostgreSQL example:

```text
postgresql://soc_user:strong-password@127.0.0.1:5432/soc_sentinel
```

## Agent Configuration

The agent reads `config.json` beside the executable. Change only `server_url`
when moving between environments:

Localhost:

```json
{ "server_url": "http://127.0.0.1:5000" }
```

LAN:

```json
{ "server_url": "http://192.168.1.13:5000" }
```

Cloud HTTPS:

```json
{ "server_url": "https://soc.example.com" }
```

The agent also supports `SOC_SENTINEL_SERVER_URL` as the default when a new
`config.json` is created.
