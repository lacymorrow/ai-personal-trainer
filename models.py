from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone = Column(String)
    fitness_level = Column(String)
    preferred_time = Column(String)
    goals = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workouts = relationship("Workout", back_populates="user")
    personal_records = relationship("PersonalRecord", back_populates="user")

class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exercises = Column(JSON)
    completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    difficulty_rating = Column(Integer, nullable=True)  # 1-5 rating
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workouts")
    exercise_logs = relationship("ExerciseLog", back_populates="workout")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"))
    exercise_name = Column(String)
    sets_completed = Column(Integer)
    reps_completed = Column(Integer, nullable=True)
    weight_used = Column(Float, nullable=True)  # in kg
    duration = Column(Integer, nullable=True)  # in seconds
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    workout = relationship("Workout", back_populates="exercise_logs")

class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exercise_name = Column(String)
    record_type = Column(String)  # "weight", "reps", "duration"
    value = Column(Float)
    achieved_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, nullable=True)

    user = relationship("User", back_populates="personal_records")
