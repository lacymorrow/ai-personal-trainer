from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, User, Workout, ExerciseLog, PersonalRecord
import os
from dotenv import load_dotenv

def init_database():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment or use SQLite as default
    database_url = os.getenv("DATABASE_URL", "sqlite:///./ai_trainer.db")
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        # Drop all existing tables
        Base.metadata.drop_all(engine)
        print("✅ Existing tables dropped successfully!")
        
        # Create all tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created successfully!")
        
        # Create session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Verify connection
        db.execute(text("SELECT 1"))
        print("✅ Database connection verified!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        raise
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    init_database()
