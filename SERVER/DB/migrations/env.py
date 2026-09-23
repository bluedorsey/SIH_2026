import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context

# Add repo root to Python path (SERVER's parent)
_repo_root = str(Path(__file__).resolve().parents[3])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Load POSTGRES_DSN from .env if not already in environment
if not os.environ.get("POSTGRES_DSN"):
    env_file = Path(_repo_root) / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("POSTGRES_DSN="):
                os.environ["POSTGRES_DSN"] = line.split("=", 1)[1].strip().strip('"').strip("'")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from SERVER.DB.models import raw_meta, derived_meta, review_meta, reference_meta
target_metadata = [raw_meta, derived_meta, review_meta, reference_meta]

# Override url
dsn = os.environ.get("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/oilens")
config.set_main_option("sqlalchemy.url", dsn)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Create schemas before running migrations
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS derived"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS review"))
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS reference"))
        connection.commit()

        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_schemas=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
