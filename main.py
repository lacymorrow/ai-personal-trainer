from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, time, timedelta
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import logging
import sys
from dotenv import load_dotenv
from gamification import GamificationManager

from models import Base, User, Workout, ExerciseLog, PersonalRecord, Streak, Achievement, Challenge, ChallengeParticipant
from workout_generator import WorkoutGenerator
from voice_generator import VoiceGenerator
from spotify_player import SpotifyPlayer
from database import engine, SessionLocal
from workout_enhancer import WorkoutEnhancer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Global components
workout_generator = None
voice_generator = None
spotify_player = None
workout_enhancer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application"""
    # Startup
    try:
        logger.info("🚀 Starting up application...")

        # Initialize components
        global workout_generator, voice_generator, spotify_player, workout_enhancer
        workout_generator = WorkoutGenerator()
        voice_generator = VoiceGenerator()
        spotify_player = SpotifyPlayer()
        workout_enhancer = WorkoutEnhancer(
            spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
        )
        logger.info("✅ Components initialized successfully")

        # Create static directories if they don't exist
        os.makedirs("static/audio", exist_ok=True)
        logger.info("✅ Static directories created")

        # Create database tables
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Error creating database tables: {str(e)}")
            raise

        yield
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
        raise
    finally:
        # Cleanup
        logger.info("👋 Shutting down application...")

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
    logger.info("✅ Static files and templates mounted successfully")
except Exception as e:
    logger.error(f"❌ Error mounting static files: {str(e)}")
    raise

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic model for user creation
class UserCreate(BaseModel):
    name: str
    phone: str
    fitness_level: str
    preferred_time: str
    goals: str

# Pydantic models for workout completion and progress tracking
class ExerciseLogCreate(BaseModel):
    exercise_name: str
    sets_completed: Optional[int] = None
    reps_completed: Optional[int] = None
    weight_used: Optional[float] = None
    duration: Optional[int] = None

class WorkoutComplete(BaseModel):
    difficulty_rating: Optional[int] = None
    notes: Optional[str] = None
    exercise_logs: List[ExerciseLogCreate]

class ChallengeResponse(BaseModel):
    id: int
    name: str
    description: str
    target_value: int
    current_value: Optional[int] = None
    reward_points: int
    completed: bool = False
    end_date: datetime

class UserProgressResponse(BaseModel):
    level: int
    title: str
    total_points: int
    experience_points: int
    current_streak: int
    longest_streak: int
    streak_multiplier: float
    achievements: list
    active_challenges: List[ChallengeResponse]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "database": "connected",
            "components": {
                "workout_generator": workout_generator is not None,
                "voice_generator": voice_generator is not None,
                "spotify_player": spotify_player is not None,
                "workout_enhancer": workout_enhancer is not None,
                "spotify": workout_enhancer.spotify_available if workout_enhancer else False,
                "voice": voice_generator.elevenlabs_available if voice_generator else False
            }
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    try:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "spotify_enabled": workout_enhancer.spotify_available if workout_enhancer else False,
                "voice_enabled": voice_generator.elevenlabs_available if voice_generator else False
            }
        )
    except Exception as e:
        logger.error(f"❌ Error rendering index page: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/workout")
async def get_workout(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            # Create a new user with default settings if none exists
            user = User(
                id=user_id,
                name="User",
                fitness_level="beginner",
                goals="Get fit and healthy"
            )
            db.add(user)
            db.commit()

        # Generate a new workout plan
        workout_plan = workout_generator.generate_workout_plan({
            "name": user.name,
            "fitness_level": user.fitness_level,
            "goals": user.goals
        })

        # Create a new workout record
        workout = Workout(
            user_id=user_id,
            exercises=workout_plan["exercises"],
            completed=False,
            workout_intensity="regular"
        )
        db.add(workout)
        db.commit()
        db.refresh(workout)

        # Add workout ID to the response
        workout_plan["id"] = workout.id
        
        # Enhance the workout with music and voice features
        if workout_enhancer:
            workout_enhancer.db = db  # Set the database session
            enhanced_plan = await workout_enhancer.enhance_workout(workout_plan, user_id)
            return enhanced_plan
        
        return workout_plan

    except Exception as e:
        logger.error(f"Error generating workout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workouts/{workout_id}/complete")
async def complete_workout(
    workout_id: int,
    workout_data: WorkoutComplete,
    db: Session = Depends(get_db)
):
    try:
        workout = db.query(Workout).filter(Workout.id == workout_id).first()
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")

        # Update workout completion
        workout.completed = True
        workout.completion_date = datetime.utcnow()
        workout.difficulty_rating = workout_data.difficulty_rating
        workout.notes = workout_data.notes

        # Get the original exercises
        exercises = workout.exercises

        # Initialize gamification manager
        gamification = GamificationManager(db)

        # Log exercises and check for PRs
        for exercise in exercises:
            exercise_log = ExerciseLog(
                workout_id=workout_id,
                exercise_name=exercise["name"],
                sets_completed=exercise["sets"],
                reps_completed=exercise["reps"] if isinstance(exercise["reps"], int) else None,
                completed=True
            )
            db.add(exercise_log)

        # Update streak and get new achievements
        user = db.query(User).get(workout.user_id)
        streak_info = await gamification.update_streak(user)
        new_achievements = await gamification.check_and_award_achievements(user)

        # Award base points for completing workout
        base_points = 100  # Base points for workout completion
        bonus_points = int(base_points * streak_info["multiplier"])  # Apply streak multiplier
        user.total_points += bonus_points

        db.commit()

        return {
            "message": "Workout completed successfully!",
            "points_earned": bonus_points,
            "new_achievements": new_achievements,
            "streak_info": streak_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error completing workout {workout_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/")
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    try:
        # Create user
        db_user = User(
            name=user.name,
            phone=user.phone,
            fitness_level=user.fitness_level,
            preferred_time=user.preferred_time,
            goals=user.goals
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Generate initial workout plan
        workout_plan = workout_generator.generate_workout_plan({
            "name": user.name,
            "fitness_level": user.fitness_level,
            "goals": user.goals
        })

        # Create workout entry
        db_workout = Workout(
            user_id=db_user.id,
            exercises=json.dumps(workout_plan["exercises"])
        )
        db.add(db_workout)
        db.commit()

        # Generate audio file for the workout
        audio_path = voice_generator.generate_workout_audio(db_user.id, workout_plan)

        return {
            "message": "User created successfully",
            "user_id": db_user.id,
            "workout_plan": workout_plan,
            "audio_url": audio_path
        }
    except Exception as e:
        logger.error(f"❌ Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{user_id}/workout/complete")
async def complete_workout(user_id: int, feedback: str = None, db: Session = Depends(get_db)):
    try:
        workout = db.query(Workout).filter(
            Workout.user_id == user_id
        ).order_by(Workout.date.desc()).first()

        if not workout:
            raise HTTPException(status_code=404, detail="No workout found")

        workout.completed = "completed"
        workout.feedback = feedback
        db.commit()

        return {"message": "Workout marked as completed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error completing workout for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/gamification")
async def get_user_gamification(user_id: int, db: Session = Depends(get_db)):
    """Get user's gamification status including level, achievements, and challenges"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get streak info
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        streak_info = {
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "streak_multiplier": streak.streak_multiplier if streak else 1.0
        }

        # Get achievements
        achievements = db.query(Achievement).filter(
            Achievement.user_id == user_id
        ).order_by(Achievement.unlocked_at.desc()).all()

        # Get active challenges
        now = datetime.utcnow()
        active_challenges = db.query(Challenge).filter(
            Challenge.end_date > now
        ).all()

        # Get user's progress in active challenges
        challenge_responses = []
        for challenge in active_challenges:
            participant = db.query(ChallengeParticipant).filter(
                ChallengeParticipant.challenge_id == challenge.id,
                ChallengeParticipant.user_id == user_id
            ).first()

            challenge_responses.append({
                "id": challenge.id,
                "name": challenge.name,
                "description": challenge.description,
                "target_value": challenge.target_value,
                "current_value": participant.current_value if participant else 0,
                "reward_points": challenge.reward_points,
                "completed": participant.completed if participant else False,
                "end_date": challenge.end_date
            })

        return {
            "level": user.level,
            "title": user.title,
            "total_points": user.total_points,
            "experience_points": user.experience_points,
            **streak_info,
            "achievements": [
                {
                    "name": a.name,
                    "description": a.description,
                    "badge_url": a.badge_url,
                    "meme_url": a.meme_url,
                    "unlocked_at": a.unlocked_at
                }
                for a in achievements
            ],
            "active_challenges": challenge_responses
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting gamification status for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/challenges/{challenge_id}/join")
async def join_challenge(
    challenge_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Join a challenge"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        gamification = GamificationManager(db)
        participant = await gamification.join_challenge(user, challenge_id)

        return {"message": "Successfully joined challenge"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error joining challenge {challenge_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/challenges/{challenge_id}/progress")
async def update_challenge_progress(
    challenge_id: int,
    user_id: int,
    value: int,
    db: Session = Depends(get_db)
):
    """Update progress in a challenge"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        gamification = GamificationManager(db)
        result = await gamification.update_challenge_progress(user, challenge_id, value)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating progress in challenge {challenge_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/progress")
async def get_user_progress(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get workout completion stats
        total_workouts = db.query(Workout).filter(Workout.user_id == user_id).count()
        completed_workouts = db.query(Workout).filter(
            Workout.user_id == user_id,
            Workout.completed == True
        ).count()

        # Get personal records
        personal_records = db.query(PersonalRecord).filter(
            PersonalRecord.user_id == user_id
        ).order_by(PersonalRecord.achieved_at.desc()).all()

        # Get recent workouts
        recent_workouts = db.query(Workout).filter(
            Workout.user_id == user_id
        ).order_by(Workout.created_at.desc()).limit(5).all()

        return {
            "stats": {
                "total_workouts": total_workouts,
                "completed_workouts": completed_workouts,
                "completion_rate": (completed_workouts / total_workouts * 100) if total_workouts > 0 else 0
            },
            "personal_records": [
                {
                    "exercise": pr.exercise_name,
                    "type": pr.record_type,
                    "value": pr.value,
                    "achieved_at": pr.achieved_at
                }
                for pr in personal_records
            ],
            "recent_workouts": [
                {
                    "id": w.id,
                    "date": w.created_at,
                    "completed": w.completed,
                    "difficulty_rating": w.difficulty_rating
                }
                for w in recent_workouts
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting progress for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error(f"❌ Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
