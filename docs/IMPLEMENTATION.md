# 校内业务系统服务监控系统实施文档

## 1. 项目目标与范围

本系统用于监控校内核心业务系统（教务、信息门户、一卡通、OA、图书馆等），实现：

- 7x24 自动巡检
- 秒级发现异常（依赖巡检间隔）
- 故障自动告警与恢复通知
- 历史可用性与故障统计

### 1.1 覆盖对象

- Web 服务：HTTPS/HTTP 页面、关键业务入口
- TCP 服务：IP+端口（适用于内网中间件、支付网关、接口服务）

### 1.2 默认策略

- 正常频率：60 秒
- 高峰频率：30 秒（通过修改 `service.interval_sec` 实现）
- 超时阈值：10 秒
- 故障判定：连续 3 次失败
- 告警抑制：同一故障 5 分钟内仅一次

## 2. 技术架构

- 后端：FastAPI
- 巡检调度：APScheduler
- 存储：SQLAlchemy + SQLite（默认）/MySQL（生产）
- 检测方式：HTTP/HTTPS + TCP
- 告警：当前为统一抽象接口（可接企业微信/钉钉/邮箱）
- 鉴权：管理员 JWT 登录鉴权
- 审计：配置变更写入 `audit_log`

系统分层：

1. 展示层：Vue3 + Element Plus + ECharts 监控大盘
2. 服务层：配置管理、查询统计、权限扩展点
3. 采集层：HTTP/TCP 检测、关键词校验、状态判定
4. 存储层：服务配置、巡检日志、告警日志

## 3. 数据库设计

### 3.1 `service`

- `id`: 主键
- `name`: 服务名称（唯一）
- `target`: URL 或 `host:port`
- `check_type`: `http` / `tcp`
- `keyword`: 关键词（HTTP 可选）
- `interval_sec`: 巡检间隔
- `timeout_sec`: 超时
- `enabled`: 启停
- `created_at` / `updated_at`

### 3.2 `monitor_log`

- `id`
- `service_id`
- `latency_ms`
- `http_code`
- `result_status`: `online` / `slow` / `abnormal` / `offline`
- `is_success`
- `error_msg`
- `checked_at`

### 3.3 `alert_log`

- `id`
- `service_id`
- `alert_type`: `down` / `recovered`
- `reason`
- `first_occur_at`
- `last_occur_at`
- `recovered_at`
- `alert_status`: `active` / `closed`

### 3.4 `admin_user`

- `id`
- `username`
- `password_hash`
- `is_active`
- `created_at` / `updated_at`

### 3.5 `audit_log`

- `id`
- `admin_username`
- `action`
- `target_type`
- `target_id`
- `detail`
- `created_at`

## 4. 状态判定规则

- `online`：探测成功，延时 <= timeout
- `slow`：探测成功，但延时 > timeout
- `abnormal`：HTTP 返回异常内容（关键词未匹配）
- `offline`：请求超时、连接失败、TCP 不通等

故障触发逻辑：

1. 单次失败仅记日志
2. 连续失败次数达到 3 次触发 `down` 告警
3. 告警后若恢复成功，触发 `recovered` 通知并关闭活动告警

## 5. 核心接口

- `GET /health`：服务健康检查
- `GET /api/services`：查询服务列表
- `POST /api/services`：新增服务
- `PUT /api/services/{service_id}`：更新服务
- `DELETE /api/services/{service_id}`：删除服务
- `POST /api/services/{service_id}/run-now`：立即巡检一次
- `GET /api/monitor/logs`：巡检日志查询
- `GET /api/alerts`：告警记录查询
- `GET /api/dashboard/overview`：总览统计
- `GET /api/dashboard/service-status`：每个服务的最新状态快照
- `POST /api/auth/login`：管理员登录
- `GET /api/auth/me`：管理员身份校验
- `POST /api/auth/change-password`：管理员改密
- `GET /api/audit-logs`：操作审计查询

## 6. 部署说明（校园内网）

### 6.1 开发/测试

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6.2 生产建议

- 运行于校园内网主机
- 使用 MySQL（`10.1.12.162` / `jiankong`）替换 SQLite
- 使用 `Nginx + uvicorn` 方式部署
- 启用日志轮转与数据库备份

### 6.3 本项目 MySQL 初始化

- 初始化脚本：`docs/MYSQL_INIT.sql`
- 部署说明：`docs/MYSQL_DEPLOY.md`

### 6.4 前端大盘运行

```powershell
Set-Location "C:\Users\Administrator\PycharmProjects\jiankong\frontend"
npm install
npm run dev
```

## 7. 实施计划

- 第 1 阶段：基础功能上线（服务配置、巡检、告警、日志）
- 第 2 阶段：接入企业微信/钉钉/邮件
- 第 3 阶段：前端大盘（Vue3 + ECharts）
- 第 4 阶段：权限控制与操作审计

## 8. 验收标准

- 新增服务后能按配置自动巡检
- 异常连续 3 次后生成告警
- 服务恢复后生成恢复记录
- 大盘接口能返回在线率、故障数量、平均延时
- 关键日志可追溯到服务与时间点

