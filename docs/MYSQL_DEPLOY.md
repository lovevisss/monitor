# MySQL Deployment and Migration Guide

## 1. Target Database

- Host: `10.1.12.162`
- User: `root`
- Database: `jiankong`

## 2. Install Dependencies

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Initialize MySQL Tables

If your machine has MySQL CLI:

```powershell
mysql -h 10.1.12.162 -P 3306 -u root -p7488 < docs\MYSQL_INIT.sql
```

If MySQL CLI is unavailable, you can still let SQLAlchemy auto-create tables on startup after setting `DATABASE_URL`.

## 4. Configure Backend

PowerShell session-based setup:

```powershell
$env:DATABASE_URL="mysql+pymysql://root:7488@10.1.12.162:3306/jiankong?charset=utf8mb4"
$env:JWT_SECRET_KEY="change-this-in-production"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="admin123"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Default admin is auto-created on first startup using `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

Optional alert channels:

```powershell
$env:ALERT_WEBHOOK_WECHAT="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
$env:ALERT_WEBHOOK_DINGTALK="https://oapi.dingtalk.com/robot/send?access_token=..."
$env:ALERT_EMAIL_ENABLED="true"
$env:ALERT_EMAIL_HOST="smtp.example.com"
$env:ALERT_EMAIL_PORT="587"
$env:ALERT_EMAIL_USER="ops@example.com"
$env:ALERT_EMAIL_PASSWORD="your-password"
$env:ALERT_EMAIL_FROM="ops@example.com"
$env:ALERT_EMAIL_TO="admin1@example.com,admin2@example.com"
$env:ALERT_EMAIL_USE_TLS="true"
```

## 5. Migrate from Local SQLite (Optional)

1. Keep current `monitor.db` as backup.
2. Start backend with MySQL `DATABASE_URL`.
3. Re-create service configs through API or import scripts.

A lightweight import script can be added later if you want one-click SQLite to MySQL migration.

## 6. Verify Connection

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/services
```

