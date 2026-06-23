# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from logging.config import fileConfig

import sys
import os

# Add the project directory to the sys.path
sys.path.append(os.getcwd())

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your app's settings and Base
from app.config.settings import settings
from app.db.base import Base
# Ensure all models are imported so metadata is populated
from app.models import *  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _get_database_url() -> str:
    """Resolve the database URL from SUPABASE_DB_URL environment variable."""
    url = os.environ.get("SUPABASE_DB_URL")
    if url and url.strip():
        return url.strip()

    url_from_settings = getattr(settings, "SUPABASE_DB_URL", None)
    if url_from_settings and url_from_settings.strip():
        return url_from_settings.strip()

    raise RuntimeError(
        "SUPABASE_DB_URL environment variable is not set. "
        "Alembic requires a direct PostgreSQL connection URL (not the Supabase REST API URL). "
        "Example: postgresql://postgres.<project-ref>:<password>@db.<project-ref>.supabase.co:5432/postgres"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    url = _get_database_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
