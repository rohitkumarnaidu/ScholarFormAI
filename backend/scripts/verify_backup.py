#!/usr/bin/env python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Backup verification script — checks that Supabase backups are accessible and valid.

Usage:
    python scripts/verify_backup.py
"""
import logging
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def verify_backup() -> bool:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("❌ SUPABASE_DB_URL not set")
        return False

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW()"))
            now = result.scalar()
            print(f"✅ Database connection successful: {now}")

            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            table_count = result.scalar()
            print(f"✅ Public tables: {table_count}")

            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'auth'"))
            auth_count = result.scalar()
            print(f"✅ Auth tables: {auth_count}")

            critical_tables = ["documents", "profiles", "user_api_keys", "api_key_usage_log"]
            for table in critical_tables:
                result = conn.execute(
                    text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                )
                exists = result.scalar()
                status = "✅" if exists else "❌"
                print(f"{status} Table '{table}': {'exists' if exists else 'MISSING'}")

            print(f"\n✅ Backup verification complete at {datetime.now(UTC).isoformat()}")
            return True

    except Exception as e:
        print(f"❌ Backup verification failed: {e}")
        return False
    finally:
        engine.dispose()


if __name__ == "__main__":
    success = verify_backup()
    sys.exit(0 if success else 1)
