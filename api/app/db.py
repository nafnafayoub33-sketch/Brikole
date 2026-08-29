"""Engine and session.

Synchronous SQLAlchemy on PyMySQL: FastAPI runs `def` endpoints in a thread
pool, so this costs nothing here and removes a whole class of async-driver
surprises against MySQL.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    echo=_settings.sql_echo,
    pool_pre_ping=True,  # MySQL drops idle connections; without this the first
    pool_recycle=3600,   # request after a quiet period fails
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """For scripts and seeds: commit on success, roll back on anything else."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
