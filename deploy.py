#!/usr/bin/env python3
import os
import sys
import logging
from database_utils import DatabaseManager
from models import Base
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def init_production_db():
    """Initialize the production database on Railway"""
    try:
        load_dotenv()
        
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL not found in environment")
            return False
        
        logger.info(f"🔌 Using database: {database_url[:20]}...")
        
        # Handle Railway's Postgres URL format
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
            logger.info("✅ Converted postgres:// to postgresql://")
        
        try:
            # Create engine with extended timeout
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    'connect_timeout': 60
                }
            )
            logger.info("✅ Database engine created")
            
            # Test connection before creating tables
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("✅ Initial database connection verified")
            
            # Create all tables
            Base.metadata.create_all(engine)
            logger.info("✅ Database tables created successfully")
            
            # Initialize database manager
            db_manager = DatabaseManager(database_url=database_url)
            logger.info("✅ Database manager initialized")
            
            # Check if this is a fresh deployment
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                logger.info(f"📊 Current user count: {user_count}")
                
                if user_count == 0:
                    logger.info("🔄 Loading sample data for fresh deployment...")
                    db_manager.load_sample_data()
                    logger.info("✅ Sample data loaded successfully")
            
            # Run health check
            health = db_manager.health_check()
            if health['status'] == 'healthy':
                logger.info("✅ Database health check passed!")
                logger.info("\n📊 Table Statistics:")
                for table, count in health['table_stats'].items():
                    logger.info(f"  {table}: {count} records")
                return True
            else:
                logger.error(f"❌ Database health check failed: {health.get('error', 'Unknown error')}")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Database error: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Deployment error: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting production database initialization...")
    success = init_production_db()
    
    if success:
        logger.info("✅ Production database initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Production database initialization failed!")
        sys.exit(1)
