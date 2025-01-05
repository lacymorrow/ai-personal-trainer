from datetime import datetime, timedelta
import random
from typing import List, Dict
from models import User, Achievement, Streak, Challenge, ChallengeParticipant

# Achievement definitions with Gen Z flair
ACHIEVEMENTS = {
    "streak": [
        {
            "name": "No Cap Streak",
            "description": "7-day workout streak! Fr fr you're killing it! 🔥",
            "badge_url": "https://img.shields.io/badge/Streak-7%20Days-bronze?style=for-the-badge&logo=firebase&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o6ZtrbzjGAAXyx2WQ/giphy.gif",
            "points": 100,
            "days": 7
        },
        {
            "name": "Main Character Energy",
            "description": "30-day streak! You're literally that girl/guy! 💅",
            "badge_url": "https://img.shields.io/badge/Streak-30%20Days-gold?style=for-the-badge&logo=firebase&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",
            "points": 500,
            "days": 30
        }
    ],
    "pr": [
        {
            "name": "Gains = Obtained",
            "description": "First PR! Let's get this bread! 🍞",
            "badge_url": "https://img.shields.io/badge/Achievement-PR%20Breaker-red?style=for-the-badge&logo=powershell&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o7TKDkDbIDJieKbVm/giphy.gif",
            "points": 50
        },
        {
            "name": "Absolute Unit",
            "description": "5 PRs in one month! Sheeeesh! 💪",
            "badge_url": "https://img.shields.io/badge/Achievement-PR%20Breaker-red?style=for-the-badge&logo=powershell&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o7TKDkDbIDJieKbVm/giphy.gif",
            "points": 200
        }
    ],
    "milestone": [
        {
            "name": "Gym Tok Famous",
            "description": "Completed 10 workouts! The algorithm loves you! 📱",
            "badge_url": "https://img.shields.io/badge/Achievement-First%20Workout-blue?style=for-the-badge&logo=adidas&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o7TKtsBMu4lwFXvJS/giphy.gif",
            "points": 150
        },
        {
            "name": "Built Different",
            "description": "50 workouts completed! No skips, just W's! 👑",
            "badge_url": "https://img.shields.io/badge/Achievement-First%20Workout-blue?style=for-the-badge&logo=adidas&logoColor=white",
            "meme_url": "https://media.giphy.com/media/3o7TKtsBMu4lwFXvJS/giphy.gif",
            "points": 750
        }
    ]
}

# Titles based on levels
TITLES = {
    1: "Rookie Lifter",
    5: "Gym Rat Apprentice",
    10: "Certified Gains Enjoyer",
    15: "Fitness Girlboss/Maleboss",
    20: "Gym Influencer",
    25: "Swoledier",
    30: "Gains Legend",
    40: "Fitness CEO",
    50: "Gigachad/Gigastacy"
}

# Challenge templates
DAILY_CHALLENGES = [
    {
        "name": "Push Day Energy",
        "description": "Complete 100 push-ups today (any variation). Real ones only! 💪",
        "target_value": 100,
        "reward_points": 50
    },
    {
        "name": "Cardio? More like Car-YES-o",
        "description": "20 minutes of any cardio. It's giving main character morning routine! 🏃‍♂️",
        "target_value": 20,
        "reward_points": 40
    }
]

WEEKLY_CHALLENGES = [
    {
        "name": "Gains Week Challenge",
        "description": "Hit 3 PRs this week. We go Jim! 🏋️‍♂️",
        "target_value": 3,
        "reward_points": 200
    },
    {
        "name": "Consistency Check",
        "description": "Complete 5 workouts this week. No skips, just gains! 📈",
        "target_value": 5,
        "reward_points": 150
    }
]

class GamificationManager:
    def __init__(self, db_session):
        self.db = db_session

    async def check_and_award_achievements(self, user: User) -> List[Achievement]:
        """Check and award new achievements for a user"""
        new_achievements = []
        
        # Check streak achievements
        streak = self.db.query(Streak).filter(Streak.user_id == user.id).first()
        if streak:
            for achievement in ACHIEVEMENTS["streak"]:
                if streak.current_streak >= achievement["days"]:
                    existing = self.db.query(Achievement).filter(
                        Achievement.user_id == user.id,
                        Achievement.name == achievement["name"]
                    ).first()
                    
                    if not existing:
                        new_achievement = Achievement(
                            user_id=user.id,
                            name=achievement["name"],
                            description=achievement["description"],
                            badge_url=achievement["badge_url"],
                            meme_url=achievement["meme_url"],
                            achievement_type="streak"
                        )
                        self.db.add(new_achievement)
                        new_achievements.append(new_achievement)
                        user.total_points += achievement["points"]
        
        # Update user level and title
        self.update_user_level(user)
        
        if new_achievements:
            self.db.commit()
        
        return new_achievements

    def update_user_level(self, user: User):
        """Update user's level and title based on points"""
        new_level = 1 + (user.total_points // 1000)  # Level up every 1000 points
        if new_level != user.level:
            user.level = new_level
            # Find the highest title they qualify for
            qualified_titles = {k: v for k, v in TITLES.items() if k <= new_level}
            if qualified_titles:
                user.title = qualified_titles[max(qualified_titles.keys())]

    async def update_streak(self, user: User) -> Dict:
        """Update user's workout streak"""
        streak = self.db.query(Streak).filter(Streak.user_id == user.id).first()
        if not streak:
            streak = Streak(user_id=user.id)
            self.db.add(streak)
        
        today = datetime.utcnow().date()
        last_workout = streak.last_workout_date.date() if streak.last_workout_date else None
        
        if not last_workout or (today - last_workout) > timedelta(days=1):
            # Streak broken or first workout
            streak.current_streak = 1
        else:
            # Continue streak
            streak.current_streak += 1
        
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
        streak.last_workout_date = datetime.utcnow()
        
        # Increase multiplier for longer streaks
        streak.streak_multiplier = min(1 + (streak.current_streak * 0.1), 2.0)
        
        self.db.commit()
        
        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "multiplier": streak.streak_multiplier
        }

    async def create_daily_challenges(self) -> List[Challenge]:
        """Create new daily challenges"""
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        # Select 2 random daily challenges
        selected_challenges = random.sample(DAILY_CHALLENGES, 2)
        new_challenges = []
        
        for challenge_template in selected_challenges:
            challenge = Challenge(
                name=challenge_template["name"],
                description=challenge_template["description"],
                challenge_type="daily",
                target_value=challenge_template["target_value"],
                reward_points=challenge_template["reward_points"],
                start_date=datetime.combine(today, datetime.min.time()),
                end_date=datetime.combine(tomorrow, datetime.min.time()),
                meme_reward="/static/memes/challenge_complete.gif"
            )
            self.db.add(challenge)
            new_challenges.append(challenge)
        
        self.db.commit()
        return new_challenges

    async def join_challenge(self, user: User, challenge_id: int) -> ChallengeParticipant:
        """Join a challenge"""
        existing = self.db.query(ChallengeParticipant).filter(
            ChallengeParticipant.user_id == user.id,
            ChallengeParticipant.challenge_id == challenge_id
        ).first()
        
        if existing:
            return existing
        
        participant = ChallengeParticipant(
            user_id=user.id,
            challenge_id=challenge_id
        )
        self.db.add(participant)
        self.db.commit()
        
        return participant

    async def update_challenge_progress(self, user: User, challenge_id: int, value: int) -> Dict:
        """Update progress in a challenge"""
        participant = self.db.query(ChallengeParticipant).filter(
            ChallengeParticipant.user_id == user.id,
            ChallengeParticipant.challenge_id == challenge_id
        ).first()
        
        if not participant:
            return {"error": "Not participating in this challenge"}
        
        challenge = self.db.query(Challenge).get(challenge_id)
        participant.current_value = value
        
        completed = False
        if value >= challenge.target_value and not participant.completed:
            participant.completed = True
            completed = True
            user.total_points += challenge.reward_points
            self.update_user_level(user)
        
        self.db.commit()
        
        return {
            "completed": completed,
            "current_value": value,
            "target_value": challenge.target_value,
            "reward_points": challenge.reward_points if completed else 0
        }
