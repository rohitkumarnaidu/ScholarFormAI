#!/usr/bin/env python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Migration verification script — checks Alembic schema sync with SQLAlchemy models.

Usage:
    python scripts/verify_migration.py          # Check if migration is needed
    python scripts/verify_migration.py --diff    # Show column differences
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, create_engine
from app.config.settings import settings
from app.models import *  # noqa: F401 — ensure all models loaded
from app.db.base import Base


def get_db_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL") or getattr(settings, "SUPABASE_DB_URL", None)
    if not url:
        print("ERROR: SUPABASE_DB_URL not set")
        sys.exit(1)
    return url


def verify_migration(show_diff: bool = False) -> bool:
    db_url = get_db_url()
    engine = create_engine(db_url)

    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables.keys())

        missing_tables = model_tables - existing_tables
        extra_tables = existing_tables - model_tables - {"alembic_version"}

        if missing_tables:
            print(f"❌ Tables in models but missing in DB: {missing_tables}")
        if extra_tables:
            print(f"⚠️  Tables in DB but not in models: {extra_tables}")

        column_diffs = {}
        for table_name in model_tables & existing_tables:
            model_cols = {c.name for c in Base.metadata.tables[table_name].columns}
            db_cols = {c["name"] for c in inspector.get_columns(table_name)}

            missing_cols = model_cols - db_cols
            extra_cols = db_cols - model_cols

            if missing_cols or extra_cols:
                column_diffs[table_name] = {
                    "missing": missing_cols,
                    "extra": extra_cols,
                }

        if column_diffs:
            print("❌ Column differences found:")
            for table, diffs in column_diffs.items():
                if diffs["missing"]:
                    print(f"   {table}: missing columns {diffs['missing']}")
                if diffs["extra"]:
                    print(f"   {table}: extra columns {diffs['extra']}")
            if show_diff:
                return False
        else:
            print("✅ Schema is in sync — no migration needed")
            return True

        if not missing_tables and not column_diffs:
            print("✅ Schema is in sync (ignoring extra tables)")
            return True

        return False

    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Alembic schema sync")
    parser.add_argument("--diff", action="store_true", help="Show detailed column differences")
    args = parser.parse_args()

    success = verify_migration(show_diff=args.diff)
    sys.exit(0 if success else 1)
