#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from database_utils import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description='AI Personal Trainer Database Management CLI')
    parser.add_argument('action', choices=['backup', 'restore', 'healthcheck', 'load_sample_data', 'migrate', 'schema'])
    parser.add_argument('--backup-file', help='Backup file to restore from')
    args = parser.parse_args()

    db_manager = DatabaseManager()

    if args.action == 'backup':
        backup_file = db_manager.create_backup()
        print(f"✅ Database backup created: {backup_file}")

    elif args.action == 'restore':
        if not args.backup_file:
            print("❌ Error: --backup-file is required for restore")
            return
        success = db_manager.restore_backup(args.backup_file)
        if success:
            print("✅ Database restored successfully!")
        else:
            print("❌ Error restoring database")

    elif args.action == 'healthcheck':
        health = db_manager.health_check()
        print("\n🏥 Database Health Report")
        print("=" * 50)
        print(f"Status: {health['status']}")
        if health['status'] == 'healthy':
            print(f"Database Type: {health['database_type']}")
            print("\n📊 Table Statistics:")
            for table, count in health['table_stats'].items():
                print(f"  {table}: {count} records")
            if health['missing_tables']:
                print("\n⚠️  Missing Tables:")
                for table in health['missing_tables']:
                    print(f"  - {table}")
        else:
            print(f"Error: {health['error']}")

    elif args.action == 'load_sample_data':
        db_manager.load_sample_data()

    elif args.action == 'migrate':
        success = db_manager.run_migrations()
        if success:
            print("✅ Database migrations completed successfully!")
        else:
            print("❌ Error running migrations")

    elif args.action == 'schema':
        schema = db_manager.get_table_schema()
        print("\n📝 Database Schema")
        print("=" * 50)
        for table, columns in schema.items():
            print(f"\n🔹 {table}")
            for column in columns:
                print(f"  - {column}")

if __name__ == "__main__":
    main()
