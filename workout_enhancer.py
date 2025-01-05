import json
import random
from typing import Dict, List, Optional, Any
import openai
import os
from models import User, AIMotivator, MotivationalMessage, SoundtrackPreference, Workout

class WorkoutEnhancer:
    def __init__(self, db_session, elevenlabs_api_key: Optional[str] = None, spotify_client_id: Optional[str] = None, spotify_client_secret: Optional[str] = None):
        self.db = db_session
        self.elevenlabs_api_key = elevenlabs_api_key
        if self.elevenlabs_api_key:
            try:
                from elevenlabs import generate, set_api_key
                set_api_key(self.elevenlabs_api_key)
            except Exception as e:
                print(f"⚠️ ElevenLabs initialization failed: {str(e)}")
        
        self.spotify_credentials = None
        if spotify_client_id and spotify_client_secret:
            self.spotify_credentials = {
                "client_id": spotify_client_id,
                "client_secret": spotify_client_secret,
                "redirect_uri": "http://localhost:8000/callback"
            }

        self.spotify_available = False
        self.elevenlabs_available = False
        self.spotify = None
        self.generate_voice = None
        
        # Initialize Spotify if credentials are provided
        if spotify_client_id and spotify_client_secret:
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                
                auth_manager = SpotifyClientCredentials(
                    client_id=spotify_client_id,
                    client_secret=spotify_client_secret
                )
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                self.spotify_available = True
                print("✅ Spotify initialized successfully")
            except Exception as e:
                print(f"⚠️ Spotify initialization failed: {str(e)}")
        
        # Initialize ElevenLabs if API key is provided
        if elevenlabs_api_key:
            try:
                self.generate_voice = generate
                self.elevenlabs_available = True
                print("✅ ElevenLabs initialized successfully")
            except Exception as e:
                print(f"⚠️ ElevenLabs initialization failed: {str(e)}")

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

        # Generate audio using ElevenLabs if available
        audio_filename = None
        if self.elevenlabs_available:
            audio = self.generate_voice(
                text=message_content,
                voice=motivator.voice_id,
                model="eleven_monolingual_v1"
            )
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

    async def create_workout_playlist(self, user_id: int, workout_intensity: str) -> Optional[str]:
        """Create a personalized Spotify playlist for the workout"""
        if not self.spotify_credentials:
            return None

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

    async def enhance_workout(self, workout_plan: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Enhance workout with music and voice features if available"""
        enhanced_plan = workout_plan.copy()
        
        # Add Spotify playlist if available
        if self.spotify_available:
            try:
                playlist = self._get_workout_playlist()
                if playlist:
                    enhanced_plan["spotify_playlist"] = playlist
            except Exception as e:
                print(f"Error getting workout playlist: {e}")
        
        # Add voice guidance if available
        if self.elevenlabs_available:
            try:
                audio_path = self._generate_workout_audio(workout_plan, user_id)
                if audio_path:
                    enhanced_plan["audio_url"] = audio_path
            except Exception as e:
                print(f"Error generating workout audio: {e}")
        
        return enhanced_plan

    def _get_workout_playlist(self, workout_type: str = "workout") -> Optional[Dict[str, Any]]:
        """Get a workout playlist if Spotify is available"""
        if not self.spotify_available:
            return None

        try:
            # Search for a workout playlist
            results = self.spotify.search(
                q=f"{workout_type} motivation",
                type="playlist",
                limit=1
            )
            
            if results and results["playlists"]["items"]:
                playlist = results["playlists"]["items"][0]
                return {
                    "name": playlist["name"],
                    "url": playlist["external_urls"]["spotify"],
                    "uri": playlist["uri"]
                }
            return None
        except Exception as e:
            print(f"Error getting workout playlist: {e}")
            return None

    def _generate_workout_audio(self, workout_plan: Dict[str, Any], user_id: int) -> Optional[str]:
        """Generate voice guidance if ElevenLabs is available"""
        if not self.elevenlabs_available:
            return None

        try:
            # Create the workout script
            script = self._create_workout_script(workout_plan)
            
            # Generate audio
            audio = self.generate_voice(
                text=script,
                voice="Arnold",
                model="eleven_monolingual_v1"
            )
            
            # Save to file
            filename = f"static/audio/workout_{user_id}_{hash(script)}.mp3"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "wb") as f:
                f.write(audio)
            
            return filename
        except Exception as e:
            print(f"Error generating workout audio: {e}")
            return None

    def _create_workout_script(self, workout_plan: Dict[str, Any]) -> str:
        """Create a script for the workout audio"""
        script = "Welcome to your personalized workout! Let's begin.\n\n"
        
        if "exercises" in workout_plan:
            for exercise in workout_plan["exercises"]:
                if isinstance(exercise, dict):
                    name = exercise.get("name", "")
                    sets = exercise.get("sets", "")
                    reps = exercise.get("reps", "")
                    duration = exercise.get("duration", "")
                    
                    if sets and reps:
                        script += f"Next up is {name} for {sets} sets of {reps} reps.\n"
                    elif duration:
                        script += f"Next up is {name} for {duration}.\n"
                    else:
                        script += f"Next up is {name}.\n"
        
        if "motivation" in workout_plan:
            script += f"\n{workout_plan['motivation']}"
        
        return script
