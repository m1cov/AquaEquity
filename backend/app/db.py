"""
SQLAlchemy MySQL connection layer.

The database URL is read from the DATABASE_URL environment variable, e.g.:
    DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/aquafield

Falls back to a local SQLite file for development if DATABASE_URL is unset,
so the API can boot without MySQL configured (useful for early integration).
"""
from __future__ import annotations

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./aquafield_dev.db"  # dev fallback

# SQLite needs check_same_thread=False to be used with FastAPI's worker model
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Common declarative base for all SQLAlchemy models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call on startup; no-op for existing tables."""
    from app import db_models  # noqa: F401
    from sqlalchemy import inspect, text

    Base.metadata.create_all(bind=engine)

    # Add corner columns to existing farms table if missing (safe migration)
    try:
        inspector = inspect(engine)
        existing = {c["name"] for c in inspector.get_columns("farms")}
        corner_cols = [
            "top_left_x", "top_left_y", "top_right_x", "top_right_y",
            "bottom_left_x", "bottom_left_y", "bottom_right_x", "bottom_right_y",
        ]
        with engine.begin() as conn:
            for col in corner_cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE farms ADD COLUMN {col} FLOAT"))
    except Exception:
        pass
