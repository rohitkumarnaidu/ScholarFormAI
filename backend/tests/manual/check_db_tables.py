# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import os
import sys

# Add backend directory to path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import inspect, text

from app.db.session import engine


def check_tables():
    print("\n--- 🔍 Checking Database Tables ---")
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("❌ No tables found in the 'public' schema.")
        else:
            print(f"✅ Found {len(tables)} tables in 'public' schema:")
            for table in tables:
                print(f"   - {table}")
                
            # Check for specific expected tables
            expected = ["profiles", "documents", "processing_results"]
            missing = [t for t in expected if t not in tables]
            
            if missing:
                print(f"\n ️  Warning: Some expected tables seem missing from public schema: {missing}")
            else:
                print("\n✅ All core application tables appear to be present.")

        # Check for auth schema (Supabase specific)
        print("\n--- 🔐 Checking Auth Schema (Supabase) ---")
        with engine.connect() as connection:
            try:
                result = connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'auth'"))
                auth_tables = [row[0] for row in result]
                if auth_tables:
                     print(f"✅ Found {len(auth_tables)} tables in 'auth' schema (e.g., {', '.join(auth_tables[:3])}...)")
                else:
                     print("❌ No tables found in 'auth' schema. (This is unexpected for Supabase)")
            except Exception as e:
                print(f" ️  Could not query auth schema: {e}")

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    check_tables()
