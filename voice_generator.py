import os
from typing import Optional

class VoiceGenerator:
    def __init__(self):
        self.elevenlabs_available = False
        self.generate = None
        self.save = None
        
        # Only try to import if API key is set
        if os.getenv("ELEVENLABS_API_KEY"):
            try:
                from elevenlabs import generate, save
                self.elevenlabs_available = True
                self.generate = generate
                self.save = save
                print(" ElevenLabs initialized successfully")
            except ImportError:
                print(" ElevenLabs not available - voice generation disabled")

    def generate_voice_message(self, user_id: int, text: str, voice="Arnold") -> Optional[str]:
        """Generate voice message using ElevenLabs API and save to file"""
        if not self.elevenlabs_available:
            return None

        try:
            # Generate audio content
            audio = self.generate(
                text=text,
                voice=voice,
                model="eleven_monolingual_v1"
            )
            
            # Save to file
            filename = f"static/audio/message_{user_id}_{hash(text)}.mp3"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, "wb") as f:
                f.write(audio)
            
            return filename
        except Exception as e:
            print(f"Error generating voice message: {e}")
            return None

    def generate_workout_audio(self, user_id: int, workout_plan: dict) -> Optional[str]:
        """Generate audio for workout instructions"""
        if not self.elevenlabs_available:
            return None

        try:
            # Generate text for audio
            text = self._create_workout_text(workout_plan)
            return self.generate_voice_message(user_id, text)
        except Exception as e:
            print(f"Error generating workout audio: {e}")
            return None

    def _create_workout_text(self, workout_plan: dict) -> str:
        """Create text for workout audio"""
        text = "Let's get started with your workout!\n\n"
        
        if "motivation" in workout_plan:
            text += f"{workout_plan['motivation']}\n\n"
        
        if "exercises" in workout_plan:
            text += "Here's your workout plan:\n"
            for exercise in workout_plan["exercises"]:
                if isinstance(exercise, dict):
                    name = exercise.get("name", "")
                    sets = exercise.get("sets", "")
                    reps = exercise.get("reps", "")
                    duration = exercise.get("duration", "")
                    
                    if sets and reps:
                        text += f"{name}: {sets} sets of {reps} reps\n"
                    elif duration:
                        text += f"{name}: {duration} seconds\n"
                    else:
                        text += f"{name}\n"
                else:
                    text += f"{exercise}\n"
        
        text += "\nLet's crush this workout! Remember to stay hydrated and maintain proper form."
        return text
