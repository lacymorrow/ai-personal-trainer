# AI Personal Trainer

An intelligent personal training application that creates customized workout plans and provides motivation through AI-generated voice calls.

## Features
- Personalized workout plan generation using AI
- Scheduled voice calls with AI-generated motivation
- Progress tracking
- Customizable workout preferences
- Mobile-responsive web interface

## Setup
1. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn main:app --reload
```

## Technologies Used
- FastAPI (Backend)
- OpenAI GPT-4 (Workout Plan Generation)
- ElevenLabs (Voice Generation)
- Twilio (Phone Calls)
- SQLAlchemy (Database)
- HTML/CSS/JavaScript (Frontend)
