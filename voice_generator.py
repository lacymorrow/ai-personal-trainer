from elevenlabs import generate, save
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

class VoiceGenerator:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.audio_dir = "static/audio"
        
        # Create audio directory if it doesn't exist
        os.makedirs(self.audio_dir, exist_ok=True)

    def generate_voice_message(self, user_id: int, text: str, voice="Arnold") -> str:
        """Generate voice message using ElevenLabs API and save to file"""
        try:
            # Generate audio content
            audio = generate(
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

    def generate_workout_audio(self, user_id: int, workout_plan: dict) -> str:
        """Generate audio for a complete workout plan"""
        # Create the workout script
        script = self._create_workout_script(workout_plan)
        
        # Generate and save the audio
        audio_path = self.generate_voice_message(user_id, script)
        return audio_path

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
