from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_url: str = Field(default="sqlite:///./monitor.db")
    jwt_secret_key: str = Field(default="change-this-in-production")
    jwt_expire_minutes: int = Field(default=480, ge=5, le=10080)
    admin_username: str = Field(default="admin", min_length=1, max_length=64)
    admin_password: str = Field(default="admin123", min_length=6, max_length=128)
    default_interval_seconds: int = Field(default=60, ge=10, le=3600)
    default_timeout_seconds: int = Field(default=10, ge=1, le=120)
    alert_webhook_wechat: str = Field(default="")
    alert_webhook_dingtalk: str = Field(default="")
    alert_email_enabled: bool = Field(default=False)
    alert_email_host: str = Field(default="")
    alert_email_port: int = Field(default=25, ge=1, le=65535)
    alert_email_user: str = Field(default="")
    alert_email_password: str = Field(default="")
    alert_email_from: str = Field(default="")
    alert_email_to: list[str] = Field(default_factory=list)
    alert_email_use_tls: bool = Field(default=False)


CONFIG_PATH = Path(os.getenv("APP_CONFIG_PATH", "config/settings.json"))
_ENV_KEYS = {
    "database_url": "DATABASE_URL",
    "jwt_secret_key": "JWT_SECRET_KEY",
    "jwt_expire_minutes": "JWT_EXPIRE_MINUTES",
    "admin_username": "ADMIN_USERNAME",
    "admin_password": "ADMIN_PASSWORD",
    "default_interval_seconds": "DEFAULT_INTERVAL_SECONDS",
    "default_timeout_seconds": "DEFAULT_TIMEOUT_SECONDS",
    "alert_webhook_wechat": "ALERT_WEBHOOK_WECHAT",
    "alert_webhook_dingtalk": "ALERT_WEBHOOK_DINGTALK",
    "alert_email_enabled": "ALERT_EMAIL_ENABLED",
    "alert_email_host": "ALERT_EMAIL_HOST",
    "alert_email_port": "ALERT_EMAIL_PORT",
    "alert_email_user": "ALERT_EMAIL_USER",
    "alert_email_password": "ALERT_EMAIL_PASSWORD",
    "alert_email_from": "ALERT_EMAIL_FROM",
    "alert_email_to": "ALERT_EMAIL_TO",
    "alert_email_use_tls": "ALERT_EMAIL_USE_TLS",
}


def _coerce_env_value(field_name: str, value: str) -> Any:
    if field_name in {"jwt_expire_minutes", "default_interval_seconds", "default_timeout_seconds", "alert_email_port"}:
        return int(value)
    if field_name in {"alert_email_enabled", "alert_email_use_tls"}:
        return value.lower() in {"1", "true", "yes"}
    if field_name == "alert_email_to":
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _settings_from_env() -> RuntimeSettings:
    payload: dict[str, Any] = {}
    for field_name, env_name in _ENV_KEYS.items():
        raw = os.getenv(env_name)
        if raw is not None and raw != "":
            payload[field_name] = _coerce_env_value(field_name, raw)
    return RuntimeSettings(**payload)


def _ensure_parent_dir() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_json(settings: RuntimeSettings) -> None:
    _ensure_parent_dir()
    CONFIG_PATH.write_text(
        json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return RuntimeSettings.model_validate(data)

    settings = _settings_from_env()
    _write_json(settings)
    return settings


def save_settings(settings: RuntimeSettings) -> RuntimeSettings:
    _write_json(settings)
    get_settings.cache_clear()
    return get_settings()


def update_settings(updates: dict[str, Any]) -> RuntimeSettings:
    current = get_settings()
    merged = current.model_dump()
    merged.update(updates)
    updated = RuntimeSettings.model_validate(merged)
    return save_settings(updated)

