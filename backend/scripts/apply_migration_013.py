#!/usr/bin/env python3
"""
Apply Migration 013: Scenario Management System
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.db_manager import DatabaseManager
import yaml

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    print("\n🔧 Applying Migration 013: Scenario Management System")
    print("=" * 70)

    # Load config
    config = load_config()
    db_config = config['database']

    # Connect to database
    print(f"\n📡 Connecting to database: {db_config['host']}:{db_config['port']}")
    db = DatabaseManager(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    print("✅ Connected")

    # Read migration file
    migration_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'migrations', '013_scenarios_system.sql')
    print(f"\n📄 Reading migration file: {migration_path}")

    with open(migration_path, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    print(f"✅ Migration file loaded ({len(migration_sql)} characters)")

    # Apply migration
    print("\n🚀 Applying migration...")
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
        print("✅ Migration applied successfully!")

        # Verify tables created
        print("\n🔍 Verifying tables...")
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check tables
                cur.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'statedb'
                    AND table_name IN ('scenarios', 'scenario_statistics', 'user_scenario_progress', 'scenario_views')
                    ORDER BY table_name
                """)
                tables = cur.fetchall()

                print(f"  ✅ Tables created: {len(tables)}/4")
                for table in tables:
                    print(f"    - {table[0]}")

                # Check view
                cur.execute("""
                    SELECT table_name FROM information_schema.views
                    WHERE table_schema = 'statedb'
                    AND table_name = 'v_scenario_cards'
                """)
                view = cur.fetchone()

                if view:
                    print(f"  ✅ View created: v_scenario_cards")
                else:
                    print(f"  ❌ View not found")

        print("\n🎉 Migration 013 complete!")
        print("\nNext: Run seed_scenarios.py to populate data")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("=" * 70)

if __name__ == "__main__":
    main()
