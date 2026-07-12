# SOC Sentinel Architecture

```mermaid
flowchart LR
    Agent["Windows SOC Agent"] -->|"register / heartbeat / telemetry"| Nginx["Nginx reverse proxy"]
    Analyst["SOC Analyst Browser"] -->|"HTTPS / HTTP"| Nginx
    Nginx -->|"127.0.0.1:5000"| Gunicorn["Gunicorn WSGI"]
    Gunicorn --> Flask["Flask Application Factory"]
    Flask --> Routes["Dashboard Routes"]
    Flask --> APIs["REST APIs"]
    APIs --> Services["Service Layer"]
    Routes --> Services
    Services --> Detection["Detection Engine"]
    Services --> Correlation["Correlation Engine"]
    Services --> SQLite["SQLite Database"]
    Flask --> Logs["Rotating Application, Error, and Access Logs"]
```

Production process flow:

```text
EC2 boot
  -> systemd starts nginx
  -> systemd starts soc-sentinel.service
  -> Gunicorn loads soc_server/wsgi.py
  -> Flask creates the SOC Sentinel app
  -> Nginx proxies public traffic to 127.0.0.1:5000
```
