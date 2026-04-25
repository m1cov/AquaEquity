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
    # Import models so they register with Base.metadata
    from app import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
