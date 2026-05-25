from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config_store import get_settings
from app.database import get_db
from app.models import AdminUser


SETTINGS = get_settings()
JWT_SECRET_KEY = SETTINGS.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = SETTINGS.jwt_expire_minutes
DEFAULT_ADMIN_USERNAME = SETTINGS.admin_username
DEFAULT_ADMIN_PASSWORD = SETTINGS.admin_password

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt_value}${hashed.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _, salt, expected_hex = password_hash.split("$", 2)
    except ValueError:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return hmac.compare_digest(candidate, expected_hex)


def create_access_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token subject")
    return username


def authenticate_admin(db: Session, username: str, password: str) -> AdminUser | None:
    admin = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active.is_(True)).first()
    if not admin:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin


def ensure_default_admin(db: Session) -> None:
    exists = db.query(AdminUser).filter(AdminUser.username == DEFAULT_ADMIN_USERNAME).first()
    if exists:
        return

    admin = AdminUser(
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        is_active=True,
    )
    db.add(admin)
    db.commit()


def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> AdminUser:
    username = decode_access_token(token)
    admin = db.query(AdminUser).filter(AdminUser.username == username, AdminUser.is_active.is_(True)).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin not found or inactive")
    return admin

