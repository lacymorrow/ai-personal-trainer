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
    achievements = relationship("Achievement", back_populates="user")
    streaks = relationship("Streak", back_populates="user")
    challenge_participations = relationship("ChallengeParticipant", back_populates="user")
    
    total_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    experience_points = Column(Integer, default=0)
    title = Column(String, default="Rookie Lifter")  # Dynamic titles based on achievements

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

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    description = Column(String)
    badge_url = Column(String)
    meme_url = Column(String)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    achievement_type = Column(String)  # 'streak', 'milestone', 'pr', 'special'
    level = Column(Integer, default=1)  # for tiered achievements

    user = relationship("User", back_populates="achievements")

class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_workout_date = Column(DateTime)
    streak_multiplier = Column(Float, default=1.0)  # for bonus points
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="streaks")

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    challenge_type = Column(String)  # 'daily', 'weekly', 'special'
    target_value = Column(Integer)
    reward_points = Column(Integer)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    meme_reward = Column(String)  # URL to celebration meme
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("ChallengeParticipant", back_populates="challenge")

class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    current_value = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge", back_populates="participants")
    user = relationship("User", back_populates="challenge_participations")
