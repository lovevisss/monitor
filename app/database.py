from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config_store import get_settings


DATABASE_URL = get_settings().database_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models

    models.Base.metadata.create_all(bind=engine)
    _ensure_service_tags_column()


def _ensure_service_tags_column() -> None:
    try:
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("service")}
        if "tags" in columns:
            return
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE service ADD COLUMN tags VARCHAR(512)"))
    except SQLAlchemyError:
        # Startup should not fail if migration is not applicable; service can still run.
        pass

