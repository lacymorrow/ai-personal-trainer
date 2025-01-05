#!/usr/bin/env python3
import os
from database_utils import DatabaseManager
from models import Base
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def init_production_db():
    """Initialize the production database on Railway"""
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: DATABASE_URL not found in environment")
        return False
    
    # Handle Railway's Postgres URL format
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully!")
        
        # Verify connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Database connection verified!")
        
        # Initialize database manager
        db_manager = DatabaseManager(database_url=database_url)
        
        # Load sample data if this is a fresh deployment
        result = engine.execute(text("SELECT COUNT(*) FROM users"))
        if result.scalar() == 0:
            print("🔄 Loading sample data...")
            db_manager.load_sample_data()
        
        # Run health check
        health = db_manager.health_check()
        if health['status'] == 'healthy':
            print("✅ Database health check passed!")
            print("\n📊 Table Statistics:")
            for table, count in health['table_stats'].items():
                print(f"  {table}: {count} records")
        else:
            print(f"❌ Database health check failed: {health.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing production database: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Initializing production database...")
    success = init_production_db()
    if success:
        print("\n✨ Production database initialized successfully!")
    else:
        print("\n❌ Failed to initialize production database")
        exit(1)
