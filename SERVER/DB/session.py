"""
Database session factory — sync engine for the OILENS backend.

Uses SQLAlchemy 2.0 with psycopg (binary) driver.
Connection string read from environment via API/config.py.
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


_engine = None
_SessionLocal = None


def _get_dsn() -> str:
    """Resolve POSTGRES_DSN from environment (lazy, avoids circular import)."""
    import os
    dsn = os.environ.get("POSTGRES_DSN", "")
    if not dsn:
        # Try loading from .env at repo root
        from pathlib import Path
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("POSTGRES_DSN="):
                    dsn = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not dsn:
        raise RuntimeError(
            "POSTGRES_DSN not set.  Set it in .env or as an environment variable.\n"
            "Example: POSTGRES_DSN=postgresql+psycopg://postgres:devpass@localhost:5432/oilens"
        )
    return dsn


def get_engine():
    """Return (and cache) the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            _get_dsn(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return (and cache) the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def get_db():
    """Yield a transactional session, auto-committing on success, rolling back on error."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_dependency():
    """FastAPI dependency — yields a session per request."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_schemas(engine=None):
    """Create the four Postgres schemas if they don't exist."""
    eng = engine or get_engine()
    with eng.connect() as conn:
        for schema in ("raw", "derived", "review", "reference"):
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
