# SOC Sentinel Configuration Reference

SOC Sentinel v0.9.0 is configured through environment variables. Do not edit
Python source code to switch between localhost, LAN, or cloud deployments.

## Server Variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `FLASK_CONFIG` | No | `development` | `development` or `production`. |
| `SECRET_KEY` | Production | `change-this-secret-key-before-production` | Flask session signing secret. Set a long random value in production. |
| `DATABASE_URL` | No | empty | SQLAlchemy database URI. Use for PostgreSQL or an explicit SQLite URI. |
| `DATABASE_PATH` | No | `soc_server/database/soc_sentinel.db` | SQLite database path when `DATABASE_URL` is empty. Relative paths resolve from the project root. |
| `LOG_DIR` | No | `soc_server/logs` | Application log directory. Relative paths resolve from the project root. |
| `SERVER_HOST` | No | `127.0.0.1` | Bind address for `python app.py`. Use `0.0.0.0` for LAN/cloud VM binding. |
| `SERVER_PORT` | No | `5000` | Server port. |
| `SERVER_URL` | Production | inferred from request | External URL agents and users should use. Example: `https://soc.example.com`. |
| `PUBLIC_URL` | No | compatibility alias | Older alias for `SERVER_URL`. |
| `LOG_LEVEL` | No | `INFO` | Python logging level. |
| `SESSION_TIMEOUT` | No | `3600` | Flask session lifetime in seconds. |

Legacy `SOC_SENTINEL_HOST` and `SOC_SENTINEL_PORT` still work, but new
deployments should use `SERVER_HOST` and `SERVER_PORT`.

## Database URLs

SQLite default:

```text
DATABASE_PATH=soc_server/database/soc_sentinel.db
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
