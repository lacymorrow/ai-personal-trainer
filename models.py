from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone = Column(String, unique=True, index=True)
    fitness_level = Column(String)  # beginner, intermediate, advanced
    preferred_time = Column(String)  # Store as HH:MM in 24-hour format
    goals = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    workouts = relationship("Workout", back_populates="user")

class Workout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.utcnow)
    exercises = Column(String)  # Store as JSON string
    completed = Column(String, default="pending")  # pending, completed, missed
    feedback = Column(String, nullable=True)
    
    user = relationship("User", back_populates="workouts")
