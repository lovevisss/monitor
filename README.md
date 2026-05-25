# Campus Service Monitor

A lightweight campus intranet monitoring system for services like portal, academic affairs, and campus card.

## Features

- 24x7 scheduled checks (HTTP/TCP)
- Keyword validation for fake-200 pages
- Failure threshold alerting (3 consecutive failures)
- Re-alert every 6 hours while unresolved
- Availability and latency dashboard API
- SQLite by default, can switch to MySQL with one env var

## Project Structure

- `app/main.py`: FastAPI application and routes
- `app/monitor_engine.py`: APScheduler jobs and health state logic
- `app/checkers.py`: HTTP/TCP checker implementations
- `app/models.py`: SQLAlchemy ORM models
- `app/database.py`: DB initialization and session management
- `docs/IMPLEMENTATION.md`: full implementation document (Chinese)
- `docs/MYSQL_DEPLOY.md`: MySQL deployment and migration guide
- `docs/MYSQL_INIT.sql`: MySQL table initialization script
- `frontend/`: Vue3 + Element Plus + ECharts dashboard
- `tests/test_smoke.py`: smoke tests

## Quick Start

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong\frontend"
npm install
npm run build
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- `http://127.0.0.1:8000/` (frontend operation page)
- `http://127.0.0.1:8000/docs` (API documentation)

Frontend operation menus:
- `总览`: status chart, latency chart, alert list
- `服务管理`: add/edit/delete services, set tags, filter by tag, run-now checks, history, and maintenance diary
- `服务管理`: supports one-click patrol for all enabled services
- Monitoring types include `http`, `tcp`, `ping`, and `zufe_route` (www.zufe.edu.cn route health)
- `告警配置`: WeCom/DingTalk/Email alert settings + one-click test alert
- `系统配置`: runtime settings (persisted to `config/settings.json`)

Note: `0.0.0.0` is the bind address for the server, not the browser address. If you open it locally, use `http://127.0.0.1:8000`; if you access it from another machine, use the server's LAN IP.

## Environment Variables

- `DATABASE_URL` (default: `sqlite:///./monitor.db`)
- `DEFAULT_INTERVAL_SECONDS` (default: `60`)
- `DEFAULT_TIMEOUT_SECONDS` (default: `10`)
- `JWT_SECRET_KEY` (recommended to set in production)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` (default admin auto-created on startup)
- `ALERT_WEBHOOK_WECHAT` / `ALERT_WEBHOOK_DINGTALK` (robot webhook URLs)
- `ALERT_EMAIL_*` (SMTP alert channel settings)
- Runtime settings are persisted in `config/settings.json` and loaded on startup.

Example MySQL (your campus DB):

```powershell
$env:DATABASE_URL="mysql+pymysql://root:7488@10.1.12.162:3306/jiankong?charset=utf8mb4"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Initialize tables:

```powershell
mysql -h 10.1.12.162 -P 3306 -u root -p7488 < docs\MYSQL_INIT.sql
```

## Run Tests

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pytest -q
```

## Frontend Dashboard

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong\frontend"
npm install
npm run dev
```

Open:
- `http://127.0.0.1:5173`

## Auth and Audit APIs

- `POST /api/auth/login` -> get bearer token
- `GET /api/auth/me` -> current admin profile
- `POST /api/auth/change-password` -> change password
- `GET /api/audit-logs` -> operation audit logs (admin only)
- `GET /api/settings` -> load runtime settings (admin only)
- `PUT /api/settings` -> save runtime settings (admin only)
- `POST /api/alerts/test` -> send test alert (admin only)
- `GET /api/maintenance-logs` -> list maintenance diary entries (admin only)
- `POST /api/maintenance-logs` -> create maintenance diary entry (admin only)

Protected APIs (require `Authorization: Bearer <token>`):

- `POST /api/services`
- `PUT /api/services/{service_id}`
- `DELETE /api/services/{service_id}`
- `POST /api/services/{service_id}/run-now`
- `POST /api/services/run-all-now`

