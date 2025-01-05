import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from models import (
    Base, User, Workout, ExerciseLog, PersonalRecord,
    Achievement, Streak, Challenge, ChallengeParticipant,
    SoundtrackPreference, WorkoutHighlight, AIMotivator,
    MotivationalMessage, TransformationProgress, Friendship,
    GymSpotted
)

class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./ai_trainer.db")
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self) -> str:
        """Create a backup of the current database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.db"
        
        if "sqlite" in self.database_url:
            # SQLite backup
            db_path = self.database_url.replace("sqlite:///", "")
            shutil.copy2(db_path, backup_file)
        else:
            # PostgreSQL backup using pg_dump
            os.system(f"pg_dump {self.database_url} > {backup_file}")
        
        return str(backup_file)

    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from a backup file"""
        try:
            if "sqlite" in self.database_url:
                db_path = self.database_url.replace("sqlite:///", "")
                shutil.copy2(backup_file, db_path)
            else:
                os.system(f"psql {self.database_url} < {backup_file}")
            return True
        except Exception as e:
            print(f"Error restoring backup: {str(e)}")
            return False

    def health_check(self) -> Dict:
        """Check database health and return status"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            expected_tables = {
                'users', 'workouts', 'exercise_logs', 'personal_records',
                'achievements', 'streaks', 'challenges', 'challenge_participants',
                'soundtrack_preferences', 'workout_highlights', 'ai_motivators',
                'motivational_messages', 'transformation_progress', 'friendships',
                'gym_spotted'
            }
            
            db = self.SessionLocal()
            try:
                # Check connection
                db.execute(text("SELECT 1"))
                
                # Get table statistics
                stats = {}
                for table in tables:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    stats[table] = count
                
                return {
                    "status": "healthy",
                    "connection": "ok",
                    "missing_tables": list(expected_tables - set(tables)),
                    "table_stats": stats,
                    "database_type": "sqlite" if "sqlite" in self.database_url else "postgresql"
                }
            finally:
                db.close()
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    def load_sample_data(self) -> None:
        """Load sample data for testing"""
        db = self.SessionLocal()
        try:
            # Create sample users
            users = [
                User(
                    name="Gym Bro",
                    phone="123-456-7890",
                    fitness_level="intermediate",
                    preferred_time="morning",
                    goals="Get shredded",
                    total_points=500,
                    level=5,
                    title="Certified Gains Enjoyer",
                    social_handle="@gymbro",
                    workout_style="powerlifting"
                ),
                User(
                    name="Fitness Queen",
                    phone="098-765-4321",
                    fitness_level="advanced",
                    preferred_time="evening",
                    goals="Build strength",
                    total_points=1000,
                    level=10,
                    title="Fitness Girlboss",
                    social_handle="@fitnessqueen",
                    workout_style="crossfit"
                )
            ]
            db.add_all(users)
            db.commit()

            # Create sample workouts
            workouts = [
                Workout(
                    user_id=1,
                    exercises=json.dumps([
                        {"name": "Bench Press", "sets": 4, "reps": 10},
                        {"name": "Shoulder Press", "sets": 3, "reps": 12}
                    ]),
                    completed=True,
                    workout_intensity="beast_mode",
                    difficulty_rating=8,
                    notes="Feeling strong today! 💪",
                    created_at=datetime.now()
                ),
                Workout(
                    user_id=2,
                    exercises=json.dumps([
                        {"name": "Burpees", "sets": 3, "reps": 20},
                        {"name": "Mountain Climbers", "duration": 60}
                    ]),
                    completed=True,
                    workout_intensity="regular",
                    difficulty_rating=6,
                    notes="Great HIIT session! 🔥",
                    created_at=datetime.now()
                )
            ]
            db.add_all(workouts)
            db.commit()

            # Create sample achievements
            achievements = [
                Achievement(
                    user_id=1,
                    name="No Cap Streak",
                    description="7-day workout streak! Fr fr you're killing it! 🔥",
                    badge_url="/static/badges/streak_7.png",
                    meme_url="/static/memes/streak_7.gif",
                    achievement_type="streak"
                ),
                Achievement(
                    user_id=2,
                    name="Gains = Obtained",
                    description="First PR! Let's get this bread! 🍞",
                    badge_url="/static/badges/first_pr.png",
                    meme_url="/static/memes/first_pr.gif",
                    achievement_type="pr"
                )
            ]
            db.add_all(achievements)
            db.commit()

            # Create sample streaks
            streaks = [
                Streak(user_id=1, current_streak=7, longest_streak=7, streak_multiplier=1.7),
                Streak(user_id=2, current_streak=3, longest_streak=10, streak_multiplier=1.3)
            ]
            db.add_all(streaks)
            db.commit()

            # Create sample challenges
            challenge = Challenge(
                name="Push Day Energy",
                description="Complete 100 push-ups today. Real ones only! 💪",
                challenge_type="daily",
                target_value=100,
                reward_points=50,
                start_date=datetime.now(),
                end_date=datetime.now(),
                meme_reward="/static/memes/challenge_complete.gif"
            )
            db.add(challenge)
            db.commit()

            # Create sample challenge participants
            participants = [
                ChallengeParticipant(
                    challenge_id=1,
                    user_id=1,
                    current_value=75,
                    completed=False
                ),
                ChallengeParticipant(
                    challenge_id=1,
                    user_id=2,
                    current_value=100,
                    completed=True
                )
            ]
            db.add_all(participants)
            db.commit()

            print("✅ Sample data loaded successfully!")

        except Exception as e:
            print(f"❌ Error loading sample data: {str(e)}")
            db.rollback()
        finally:
            db.close()

    def run_migrations(self) -> bool:
        """Run any pending database migrations"""
        try:
            # Create alembic.ini if it doesn't exist
            if not os.path.exists("alembic.ini"):
                os.system("alembic init alembic")
            
            # Run migrations
            os.system("alembic upgrade head")
            return True
        except Exception as e:
            print(f"Error running migrations: {str(e)}")
            return False

    def get_table_schema(self) -> Dict[str, List[str]]:
        """Get schema information for all tables"""
        inspector = inspect(self.engine)
        schema = {}
        
        for table_name in inspector.get_table_names():
            columns = []
            for column in inspector.get_columns(table_name):
                columns.append(f"{column['name']} ({column['type']})")
            schema[table_name] = columns
        
        return schema
