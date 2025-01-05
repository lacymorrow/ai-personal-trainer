from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, time
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv

from models import Base, User, Workout
from workout_generator import WorkoutGenerator
from voice_generator import VoiceGenerator
from database import engine, SessionLocal

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
async def read_root(request: Request):
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

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

@app.get("/users/{user_id}/workout")
async def get_workout(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest workout
    workout = db.query(Workout).filter(
        Workout.user_id == user_id
    ).order_by(Workout.date.desc()).first()
    
    if not workout:
        # Generate new workout if none exists
        workout_plan = workout_generator.generate_workout_plan({
            "name": user.name,
            "fitness_level": user.fitness_level,
            "goals": user.goals
        })
        
        # Generate audio for the new workout
        audio_path = voice_generator.generate_workout_audio(user_id, workout_plan)
        workout_plan["audio_url"] = audio_path
        
        return workout_plan
    
    # Generate new audio for existing workout
    workout_plan = {
        "exercises": json.loads(workout.exercises),
        "motivation": workout_generator.generate_motivation_message(user.name)
    }
    audio_path = voice_generator.generate_workout_audio(user_id, workout_plan)
    
    return {
        "exercises": workout_plan["exercises"],
        "motivation": workout_plan["motivation"],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
