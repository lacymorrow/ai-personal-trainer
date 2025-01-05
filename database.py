import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle Railway's Postgres URL format
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("✅ Converted postgres:// to postgresql://")

if not DATABASE_URL:
    logger.warning("⚠️ No DATABASE_URL found, using SQLite")
    DATABASE_URL = "sqlite:///ai_trainer.db"

# Create engine with connection pooling and timeout settings
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        pool_recycle=300
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            'connect_timeout': 60
        }
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}")
        return False
