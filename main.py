from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, time, timedelta
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from dotenv import load_dotenv
from gamification import GamificationManager

from models import Base, User, Workout, ExerciseLog, PersonalRecord
from workout_generator import WorkoutGenerator
from voice_generator import VoiceGenerator
from database import engine, SessionLocal
from workout_enhancer import WorkoutEnhancer

# Load environment variables
load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

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

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize enhancer with optional credentials
workout_enhancer = WorkoutEnhancer(
    db_session=SessionLocal(),
    elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
    spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
)

# Initialize services
workout_generator = WorkoutGenerator()
voice_generator = VoiceGenerator()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "spotify_enabled": bool(os.getenv("SPOTIFY_CLIENT_ID")),
            "voice_enabled": bool(os.getenv("ELEVENLABS_API_KEY"))
        }
    )

@app.get("/users/{user_id}/workout")
async def get_workout(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest workout
    workout = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.created_at.desc()).first()
    
    if not workout:
        # Generate new workout if none exists
        workout_plan = workout_generator.generate_workout_plan({
            "name": user.name,
            "fitness_level": user.fitness_level,
            "goals": user.goals
        })
        
        # Generate audio for the new workout (optional)
        audio_path = voice_generator.generate_workout_audio(user_id, workout_plan)
        if audio_path:
            workout_plan["audio_url"] = audio_path
        
        return workout_plan
    
    # Generate new audio for existing workout (optional)
    workout_plan = {
        "exercises": json.loads(workout.exercises),
        "motivation": workout_generator.generate_motivation_message(user.name)
    }
    audio_path = voice_generator.generate_workout_audio(user_id, workout_plan)
    if audio_path:
        workout_plan["audio_url"] = audio_path
    
    return workout_plan

@app.post("/users/")
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
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

@app.post("/users/{user_id}/workout/complete")
async def complete_workout(user_id: int, feedback: str = None, db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.date.desc()).first()
    
    if not workout:
        raise HTTPException(status_code=404, detail="No workout found")
    
    workout.completed = "completed"
    workout.feedback = feedback
    db.commit()
    
    return {"message": "Workout marked as completed"}

@app.get("/users/{user_id}/gamification")
async def get_user_gamification(user_id: int, db: Session = Depends(get_db)):
    """Get user's gamification status including level, achievements, and challenges"""
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

@app.post("/challenges/{challenge_id}/join")
async def join_challenge(
    challenge_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Join a challenge"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    gamification = GamificationManager(db)
    participant = await gamification.join_challenge(user, challenge_id)
    
    return {"message": "Successfully joined challenge"}

@app.post("/challenges/{challenge_id}/progress")
async def update_challenge_progress(
    challenge_id: int,
    user_id: int,
    value: int,
    db: Session = Depends(get_db)
):
    """Update progress in a challenge"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    gamification = GamificationManager(db)
    result = await gamification.update_challenge_progress(user, challenge_id, value)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/workouts/{workout_id}/complete")
async def complete_workout(
    workout_id: int,
    workout_data: WorkoutComplete,
    db: Session = Depends(get_db)
):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Update workout completion
    workout.completed = True
    workout.completion_date = datetime.utcnow()
    workout.difficulty_rating = workout_data.difficulty_rating
    workout.notes = workout_data.notes
    
    # Initialize gamification manager
    gamification = GamificationManager(db)
    
    # Log exercises and check for PRs
    for log_data in workout_data.exercise_logs:
        exercise_log = ExerciseLog(
            workout_id=workout_id,
            exercise_name=log_data.exercise_name,
            sets_completed=log_data.sets_completed,
            reps_completed=log_data.reps_completed,
            weight_used=log_data.weight_used,
            duration=log_data.duration,
            completed=True
        )
        db.add(exercise_log)
        
        # Check for PRs and award achievements
        if log_data.weight_used:
            existing_pr = db.query(PersonalRecord).filter(
                PersonalRecord.user_id == workout.user_id,
                PersonalRecord.exercise_name == log_data.exercise_name,
                PersonalRecord.record_type == "weight"
            ).order_by(PersonalRecord.value.desc()).first()
            
            if not existing_pr or log_data.weight_used > existing_pr.value:
                new_pr = PersonalRecord(
                    user_id=workout.user_id,
                    exercise_name=log_data.exercise_name,
                    record_type="weight",
                    value=log_data.weight_used
                )
                db.add(new_pr)
                
                # Award points for new PR
                user = db.query(User).get(workout.user_id)
                user.total_points += 50  # Base points for PR
        
        if log_data.reps_completed:
            existing_pr = db.query(PersonalRecord).filter(
                PersonalRecord.user_id == workout.user_id,
                PersonalRecord.exercise_name == log_data.exercise_name,
                PersonalRecord.record_type == "reps"
            ).order_by(PersonalRecord.value.desc()).first()
            
            if not existing_pr or log_data.reps_completed > existing_pr.value:
                new_pr = PersonalRecord(
                    user_id=workout.user_id,
                    exercise_name=log_data.exercise_name,
                    record_type="reps",
                    value=log_data.reps_completed
                )
                db.add(new_pr)
                
                # Award points for new PR
                user = db.query(User).get(workout.user_id)
                user.total_points += 50  # Base points for PR
    
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
        "message": "Workout completed successfully",
        "points_earned": bonus_points,
        "streak_info": streak_info,
        "new_achievements": [
            {
                "name": a.name,
                "description": a.description,
                "badge_url": a.badge_url,
                "meme_url": a.meme_url
            }
            for a in new_achievements
        ]
    }

@app.get("/users/{user_id}/progress")
async def get_user_progress(user_id: int, db: Session = Depends(get_db)):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
