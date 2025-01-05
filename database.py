from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Handle Railway's Postgres URL format
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Use SQLite as fallback for local development
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./ai_trainer.db"
    # Create SQLite engine with check_same_thread=False
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Create PostgreSQL engine
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
