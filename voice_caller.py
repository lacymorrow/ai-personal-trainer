from elevenlabs import generate, save
from twilio.rest import Client
import os
from dotenv import load_dotenv
import tempfile

load_dotenv()

class VoiceCaller:
    def __init__(self):
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.twilio_client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.twilio_phone = "+1234567890"  # Replace with your Twilio phone number

    def generate_voice_message(self, text: str, voice="Arnold") -> bytes:
        """Generate voice message using ElevenLabs API"""
        try:
            audio = generate(
                text=text,
                voice=voice,
                model="eleven_monolingual_v1"
            )
            return audio
        except Exception as e:
            print(f"Error generating voice message: {e}")
            return None

    def make_call(self, phone_number: str, message: str) -> bool:
        """Make a phone call using Twilio with the generated voice message"""
        try:
            # Generate voice message
            audio_content = self.generate_voice_message(message)
            if not audio_content:
                return False

            # Save audio content to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_file_path = temp_file.name

            # Create TwiML to play the message
            twiml = f"""
            <Response>
                <Play>{temp_file_path}</Play>
                <Pause length="1"/>
                <Say>Time to work out! Let's get moving!</Say>
            </Response>
            """

            # Make the call
            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=phone_number,
                from_=self.twilio_phone
            )

            # Clean up temporary file
            os.unlink(temp_file_path)
            
            return True
        except Exception as e:
            print(f"Error making call: {e}")
            return False

    def schedule_call(self, phone_number: str, message: str, schedule_time: str) -> bool:
        """Schedule a call for a specific time"""
        # This method would integrate with the APScheduler in main.py
        try:
            return self.make_call(phone_number, message)
        except Exception as e:
            print(f"Error scheduling call: {e}")
            return False
