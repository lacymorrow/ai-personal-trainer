from elevenlabs import generate, save
import os
from dotenv import load_dotenv
from datetime import datetime
import json
from typing import Optional

load_dotenv()

class VoiceGenerator:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.audio_dir = "static/audio"
        self.elevenlabs_available = False
        try:
            if os.getenv("ELEVENLABS_API_KEY"):
                from elevenlabs import generate, save
                self.elevenlabs_available = True
                self.generate = generate
                self.save = save
        except ImportError:
            print("ElevenLabs not available. Voice generation will be disabled.")
        
        # Create audio directory if it doesn't exist
        os.makedirs(self.audio_dir, exist_ok=True)

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

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workout_{user_id}_{timestamp}.mp3"
            filepath = os.path.join(self.audio_dir, filename)

            # Save audio file
            with open(filepath, "wb") as f:
                f.write(audio)

            # Return the relative path to the audio file
            return f"/static/audio/{filename}"
        except Exception as e:
            print(f"Error generating voice message: {e}")
            return None

    def generate_workout_audio(self, user_id: int, workout_plan: dict) -> Optional[str]:
        """Generate audio for a complete workout plan"""
        if not self.elevenlabs_available:
            return None

        try:
            # Create the workout script
            script = self._create_workout_script(workout_plan)
            
            # Generate and save the audio
            audio_path = self.generate_voice_message(user_id, script)
            return audio_path
        except Exception as e:
            print(f"Error generating workout audio: {e}")
            return None

    def _create_workout_script(self, workout_plan: dict) -> str:
        """Create a natural-sounding script from the workout plan"""
        script = "Welcome to your personalized workout! Let's begin.\n\n"
        
        for exercise in workout_plan["exercises"]:
            if "duration" in exercise:
                script += f"Next up is {exercise['name']} for {exercise['duration']}. "
            else:
                script += f"Next up is {exercise['name']} for {exercise['sets']} sets of {exercise['reps']} repetitions. "
            script += f"Rest for {exercise['rest']}.\n"

        script += f"\n{workout_plan['motivation']}"
        return script

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
