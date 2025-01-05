import json
import random
from typing import Dict, List
import openai
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from elevenlabs import generate, set_api_key
from models import User, AIMotivator, MotivationalMessage, SoundtrackPreference, Workout

class WorkoutEnhancer:
    def __init__(self, db_session, elevenlabs_api_key: str, spotify_client_id: str, spotify_client_secret: str):
        self.db = db_session
        set_api_key(elevenlabs_api_key)
        self.spotify_credentials = {
            "client_id": spotify_client_id,
            "client_secret": spotify_client_secret,
            "redirect_uri": "http://localhost:8000/callback"
        }

    async def generate_motivational_message(self, user_id: int, message_type: str) -> Dict:
        """Generate a personalized motivational message using AI"""
        user = self.db.query(User).get(user_id)
        motivator = self.db.query(AIMotivator).filter(AIMotivator.user_id == user_id).first()

        if not motivator:
            # Create default motivator if none exists
            motivator = AIMotivator(
                user_id=user_id,
                personality="hype_beast",
                voice_id="your_default_voice_id",
                catchphrase="Let's get these gains! 💪"
            )
            self.db.add(motivator)
            self.db.commit()

        # Get context for the message
        context = self._get_user_context(user)
        
        # Generate message using OpenAI
        client = openai.OpenAI()
        prompt = self._create_motivational_prompt(context, motivator.personality, message_type)
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a Gen Z fitness motivator. Use modern slang, emojis, and high energy!"},
                {"role": "user", "content": prompt}
            ]
        )
        message_content = response.choices[0].message.content

        # Generate audio using ElevenLabs
        audio = generate(
            text=message_content,
            voice=motivator.voice_id,
            model="eleven_monolingual_v1"
        )

        # Save audio file
        audio_filename = f"static/audio/motivation_{user_id}_{message_type}_{random.randint(1000, 9999)}.mp3"
        with open(audio_filename, "wb") as f:
            f.write(audio)

        # Save message to database
        message = MotivationalMessage(
            motivator_id=motivator.id,
            message_type=message_type,
            content=message_content,
            audio_url=audio_filename
        )
        self.db.add(message)
        self.db.commit()

        return {
            "message": message_content,
            "audio_url": audio_filename
        }

    def _get_user_context(self, user: User) -> Dict:
        """Get relevant user context for personalized motivation"""
        streak = self.db.query("Streak").filter_by(user_id=user.id).first()
        recent_prs = self.db.query("PersonalRecord").filter_by(user_id=user.id)\
            .order_by("created_at desc").limit(3).all()
        
        return {
            "name": user.name,
            "level": user.level,
            "title": user.title,
            "streak": streak.current_streak if streak else 0,
            "workout_style": user.workout_style,
            "recent_achievements": [pr.exercise_name for pr in recent_prs]
        }

    def _create_motivational_prompt(self, context: Dict, personality: str, message_type: str) -> str:
        """Create a prompt for OpenAI based on context and message type"""
        prompts = {
            "pre_workout": f"Create a hype pre-workout message for {context['name']}, who's on a {context['streak']}-day streak! They're a {context['workout_style']} enthusiast at level {context['level']}. Recent wins: {', '.join(context['recent_achievements'])}. Use the {personality} personality type.",
            "achievement": f"Celebrate {context['name']}'s achievement! They just hit a new PR. They're now {context['title']} at level {context['level']}. Make it extra hype and encouraging!",
            "streak": f"Hype up {context['name']} for maintaining a {context['streak']}-day streak! They're crushing it as a {context['workout_style']} enthusiast. Make them feel like the main character!"
        }
        return prompts.get(message_type, prompts["pre_workout"])

    async def create_workout_playlist(self, user_id: int, workout_intensity: str) -> str:
        """Create a personalized Spotify playlist for the workout"""
        user = self.db.query(User).get(user_id)
        if not user.spotify_connected:
            return None

        preferences = self.db.query(SoundtrackPreference).filter_by(user_id=user_id).first()
        if not preferences:
            return None

        # Initialize Spotify client
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(**self.spotify_credentials))

        # Get BPM range based on workout intensity
        bpm_ranges = {
            "beast_mode": (140, 180),
            "regular": (120, 140),
            "recovery": (90, 120)
        }
        min_bpm, max_bpm = bpm_ranges.get(workout_intensity, (120, 140))

        # Get preferred genres
        genres = json.loads(preferences.genres)

        # Search for tracks
        tracks = []
        for genre in genres:
            results = sp.recommendations(
                seed_genres=[genre],
                target_tempo=(min_bpm + max_bpm) / 2,
                min_tempo=min_bpm,
                max_tempo=max_bpm,
                target_energy=0.8 if workout_intensity == "beast_mode" else 0.6,
                limit=5
            )
            tracks.extend([track["uri"] for track in results["tracks"]])

        # Create new playlist
        playlist_name = f"🏋️‍♂️ {user.name}'s {workout_intensity.title()} Workout"
        playlist = sp.user_playlist_create(
            user=sp.current_user()["id"],
            name=playlist_name,
            description=f"Generated by AI Personal Trainer for your {workout_intensity} workout. Let's get these gains! 💪"
        )

        # Add tracks to playlist
        sp.playlist_add_items(playlist["id"], tracks)

        return playlist["id"]

    async def customize_ai_motivator(self, user_id: int, personality: str, voice_id: str, catchphrase: str) -> Dict:
        """Customize the user's AI motivator personality"""
        motivator = self.db.query(AIMotivator).filter(AIMotivator.user_id == user_id).first()
        
        if not motivator:
            motivator = AIMotivator(user_id=user_id)
            self.db.add(motivator)
        
        motivator.personality = personality
        motivator.voice_id = voice_id
        motivator.catchphrase = catchphrase
        
        self.db.commit()
        
        return {
            "personality": personality,
            "voice_id": voice_id,
            "catchphrase": catchphrase
        }

    async def update_soundtrack_preferences(
        self,
        user_id: int,
        vibe: str,
        genres: List[str],
        bpm_range: Dict[str, int]
    ) -> Dict:
        """Update user's workout soundtrack preferences"""
        prefs = self.db.query(SoundtrackPreference).filter_by(user_id=user_id).first()
        
        if not prefs:
            prefs = SoundtrackPreference(user_id=user_id)
            self.db.add(prefs)
        
        prefs.vibe = vibe
        prefs.genres = json.dumps(genres)
        prefs.bpm_range = json.dumps(bpm_range)
        
        self.db.commit()
        
        return {
            "vibe": vibe,
            "genres": genres,
            "bpm_range": bpm_range
        }
