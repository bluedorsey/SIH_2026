"""
Environment-driven settings for the OILENS backend API.

Reads from .env at the repo root (or env vars).
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


def _find_env_file() -> str:
    """Walk up from this file to find .env."""
    p = Path(__file__).resolve()
    for parent in [p.parent, p.parent.parent, p.parent.parent.parent]:
        candidate = parent / ".env"
        if candidate.exists():
            return str(candidate)
    return ".env"


class Settings(BaseSettings):
    """All backend configuration — single source of truth."""

    # ── Database ─────────────────────────────────────────────────────────────
    postgres_dsn: str = Field(
        default="postgresql+psycopg://postgres:devpass@localhost:5432/oilens",
        alias="POSTGRES_DSN",
    )
    duckdb_path: str = Field(
        default="SERVER/ANALYTICS/oilens_analytics.duckdb",
        alias="DUCKDB_PATH",
    )

    # ── Models & Pipeline ────────────────────────────────────────────────────
    model_dir: str = Field(
        default="SERVER/Classfication/Models",
        alias="MODEL_DIR",
    )
    pipeline_version: str = Field(default="0.7.0", alias="PIPELINE_VERSION")

    # ── API ───────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    default_page_size: int = 50
    max_page_size: int = 200

    model_config = {
        "env_file": _find_env_file(),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
