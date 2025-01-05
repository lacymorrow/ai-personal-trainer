# AI Personal Trainer

An intelligent personal training application that creates customized workout plans and provides motivation through AI-generated voice guidance.

## Features
- Personalized workout plan generation using AI
- AI-generated voice guidance
- Progress tracking
- Customizable workout preferences
- Mobile-responsive web interface

## Technologies Used
- FastAPI (Backend)
- OpenAI GPT-4 (Workout Plan Generation)
- ElevenLabs (Voice Generation)
- SQLAlchemy (Database)
- TailwindCSS (Frontend Styling)

## Local Development Setup
1. Clone the repository:
```bash
git clone <your-repo-url>
cd ai_personal_trainer
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
DATABASE_URL=sqlite:///./ai_trainer.db
```

4. Run the application:
```bash
uvicorn main:app --reload
```

## Deployment
The application is configured for deployment on Railway.app:

1. Create a new project on Railway.app
2. Connect your GitHub repository
3. Add the following environment variables in Railway:
   - OPENAI_API_KEY
   - ELEVENLABS_API_KEY
   - DATABASE_URL (Railway will provide this automatically if you add a PostgreSQL database)
4. Deploy the application

## API Documentation
Once the application is running, visit `/docs` for the complete API documentation.

## Contributing
1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License
MIT License
