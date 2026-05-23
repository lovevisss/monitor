# Campus Service Monitor

A lightweight campus intranet monitoring system for services like portal, academic affairs, and campus card.

## Features

- 24x7 scheduled checks (HTTP/TCP)
- Keyword validation for fake-200 pages
- Failure threshold alerting (3 consecutive failures)
- Alert dedup within 5 minutes
- Availability and latency dashboard API
- SQLite by default, can switch to MySQL with one env var

## Project Structure

- `app/main.py`: FastAPI application and routes
- `app/monitor_engine.py`: APScheduler jobs and health state logic
- `app/checkers.py`: HTTP/TCP checker implementations
- `app/models.py`: SQLAlchemy ORM models
- `app/database.py`: DB initialization and session management
- `docs/IMPLEMENTATION.md`: full implementation document (Chinese)
- `tests/test_smoke.py`: smoke tests

## Quick Start

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:
- `http://127.0.0.1:8000/docs`

## Environment Variables

- `DATABASE_URL` (default: `sqlite:///./monitor.db`)
- `DEFAULT_INTERVAL_SECONDS` (default: `60`)
- `DEFAULT_TIMEOUT_SECONDS` (default: `10`)

Example MySQL:

```powershell
$env:DATABASE_URL="mysql+pymysql://user:password@127.0.0.1:3306/monitor"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Run Tests

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pytest -q
```

