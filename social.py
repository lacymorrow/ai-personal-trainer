from datetime import datetime
from typing import Dict, List
import json
from sqlalchemy.orm import Session
from models import (
    User, WorkoutHighlight, Friendship, GymSpotted,
    TransformationProgress, Achievement
)

class SocialManager:
    def __init__(self, db_session: Session):
        self.db = db_session

    async def create_highlight(
        self,
        user_id: int,
        workout_id: int,
        title: str,
        description: str,
        media_url: str,
        highlight_type: str
    ) -> Dict:
        """Create a new workout highlight"""
        highlight = WorkoutHighlight(
            user_id=user_id,
            workout_id=workout_id,
            title=title,
            description=description,
            media_url=media_url,
            highlight_type=highlight_type
        )
        self.db.add(highlight)
        self.db.commit()

        return {
            "id": highlight.id,
            "title": title,
            "description": description,
            "media_url": media_url,
            "created_at": highlight.created_at
        }

    async def like_highlight(self, highlight_id: int, user_id: int) -> Dict:
        """Like a workout highlight"""
        highlight = self.db.query(WorkoutHighlight).get(highlight_id)
        if not highlight:
            return {"error": "Highlight not found"}

        highlight.likes += 1
        self.db.commit()

        # Award points to highlight creator
        creator = self.db.query(User).get(highlight.user_id)
        creator.total_points += 10  # 10 points per like
        self.db.commit()

        return {
            "likes": highlight.likes,
            "points_awarded": 10
        }

    async def add_friend(self, user_id: int, friend_id: int) -> Dict:
        """Send a friend request"""
        existing = self.db.query(Friendship).filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)) |
            ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).first()

        if existing:
            return {"error": "Friendship already exists"}

        friendship = Friendship(
            user_id=user_id,
            friend_id=friend_id,
            status="pending"
        )
        self.db.add(friendship)
        self.db.commit()

        return {
            "status": "pending",
            "created_at": friendship.created_at
        }

    async def accept_friend(self, friendship_id: int) -> Dict:
        """Accept a friend request"""
        friendship = self.db.query(Friendship).get(friendship_id)
        if not friendship:
            return {"error": "Friendship not found"}

        friendship.status = "accepted"
        self.db.commit()

        # Award achievement if this is their first friend
        friend_count = self.db.query(Friendship).filter(
            (Friendship.user_id == friendship.user_id) &
            (Friendship.status == "accepted")
        ).count()

        if friend_count == 1:
            achievement = Achievement(
                user_id=friendship.user_id,
                name="Gym Buddy Found!",
                description="Made your first gym friend! Time for spotting and PR cheering! 🤝",
                badge_url="/static/badges/first_friend.png",
                meme_url="/static/memes/first_friend.gif",
                achievement_type="social"
            )
            self.db.add(achievement)
            
            # Award points
            user = self.db.query(User).get(friendship.user_id)
            user.total_points += 100
            self.db.commit()

        return {
            "status": "accepted",
            "friend_count": friend_count
        }

    async def gym_spotted(
        self,
        spotter_id: int,
        spotted_id: int,
        gym_location: str,
        message: str
    ) -> Dict:
        """Record a gym spotting"""
        spotted = GymSpotted(
            spotter_id=spotter_id,
            spotted_id=spotted_id,
            gym_location=gym_location,
            message=message
        )
        self.db.add(spotted)
        
        # Award points to both users
        spotter = self.db.query(User).get(spotter_id)
        spotted_user = self.db.query(User).get(spotted_id)
        
        spotter.total_points += 20
        spotted_user.total_points += 20
        
        self.db.commit()

        return {
            "message": message,
            "points_awarded": 20,
            "created_at": spotted.created_at
        }

    async def add_transformation_progress(
        self,
        user_id: int,
        photo_url: str,
        metrics: Dict,
        mood: str
    ) -> Dict:
        """Add a transformation progress entry"""
        progress = TransformationProgress(
            user_id=user_id,
            photo_url=photo_url,
            metrics=json.dumps(metrics),
            mood=mood
        )
        self.db.add(progress)
        
        # Check for transformation streak
        progress_count = self.db.query(TransformationProgress).filter(
            TransformationProgress.user_id == user_id
        ).count()
        
        if progress_count % 7 == 0:  # Every 7 progress photos
            achievement = Achievement(
                user_id=user_id,
                name="Transformation Loading...",
                description=f"{progress_count} weeks of progress tracked! Keep grinding! 📸",
                badge_url=f"/static/badges/progress_{progress_count}.png",
                meme_url=f"/static/memes/progress_{progress_count}.gif",
                achievement_type="progress"
            )
            self.db.add(achievement)
            
            # Award bonus points
            user = self.db.query(User).get(user_id)
            user.total_points += 200
            
        self.db.commit()

        return {
            "photo_url": photo_url,
            "metrics": metrics,
            "mood": mood,
            "progress_count": progress_count
        }

    async def get_friend_feed(self, user_id: int, page: int = 1, limit: int = 10) -> List[Dict]:
        """Get a feed of friend activities"""
        # Get user's friends
        friend_ids = self.db.query(Friendship).filter(
            ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)) &
            (Friendship.status == "accepted")
        ).with_entities(
            Friendship.user_id,
            Friendship.friend_id
        ).all()
        
        friend_ids = [
            f_id for pair in friend_ids
            for f_id in pair
            if f_id != user_id
        ]

        # Get recent highlights from friends
        highlights = self.db.query(WorkoutHighlight).filter(
            WorkoutHighlight.user_id.in_(friend_ids)
        ).order_by(
            WorkoutHighlight.created_at.desc()
        ).offset((page - 1) * limit).limit(limit).all()

        return [{
            "id": h.id,
            "user_id": h.user_id,
            "title": h.title,
            "description": h.description,
            "media_url": h.media_url,
            "likes": h.likes,
            "created_at": h.created_at
        } for h in highlights]

    async def get_gym_feed(self, gym_location: str, page: int = 1, limit: int = 10) -> List[Dict]:
        """Get a feed of activity at a specific gym"""
        spotted = self.db.query(GymSpotted).filter(
            GymSpotted.gym_location == gym_location
        ).order_by(
            GymSpotted.created_at.desc()
        ).offset((page - 1) * limit).limit(limit).all()

        return [{
            "spotter_id": s.spotter_id,
            "spotted_id": s.spotted_id,
            "message": s.message,
            "created_at": s.created_at
        } for s in spotted]
