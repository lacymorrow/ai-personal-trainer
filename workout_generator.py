import openai
import json
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

class WorkoutGenerator:
    def __init__(self):
        self.exercise_templates = {
            "beginner": {
                "strength": ["Bodyweight Squats", "Push-ups (on knees if needed)", "Wall Push-ups", "Lunges", "Plank"],
                "cardio": ["Walking", "Light Jogging", "Jumping Jacks", "March in Place"]
            },
            "intermediate": {
                "strength": ["Regular Push-ups", "Dumbbell Squats", "Dumbbell Rows", "Mountain Climbers", "Burpees"],
                "cardio": ["Running", "Jump Rope", "High Knees", "Burpees"]
            },
            "advanced": {
                "strength": ["Diamond Push-ups", "Pistol Squats", "Pull-ups", "Plyometric Push-ups", "Bulgarian Split Squats"],
                "cardio": ["Sprint Intervals", "Burpee Variations", "Box Jumps", "Mountain Climbers"]
            }
        }

    def generate_workout_plan(self, user_info: Dict) -> Dict:
        prompt = f"""Create a personalized workout plan for someone with the following profile:
        Name: {user_info['name']}
        Fitness Level: {user_info['fitness_level']}
        Goals: {user_info['goals']}
        
        Please create a structured workout plan that includes:
        1. A mix of exercises appropriate for their fitness level
        2. Sets and reps for each exercise
        3. Rest periods
        4. A motivational message
        
        Format the response as JSON with the following structure:
        {{
            "exercises": [
                {{"name": "exercise_name", "sets": number, "reps": number, "rest": "rest_duration"}}
            ],
            "motivation": "motivational_message"
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            workout_plan = json.loads(response.choices[0].message.content)
            return workout_plan
        except json.JSONDecodeError:
            # Fallback to template-based workout if AI generation fails
            return self._generate_template_workout(user_info['fitness_level'])

    def _generate_template_workout(self, fitness_level: str) -> Dict:
        exercises = []
        
        # Add strength exercises
        for exercise in self.exercise_templates[fitness_level]["strength"][:3]:
            exercises.append({
                "name": exercise,
                "sets": 3,
                "reps": 10,
                "rest": "60 seconds"
            })
        
        # Add cardio
        for exercise in self.exercise_templates[fitness_level]["cardio"][:2]:
            exercises.append({
                "name": exercise,
                "sets": 1,
                "reps": 1,
                "duration": "10 minutes",
                "rest": "60 seconds"
            })
        
        return {
            "exercises": exercises,
            "motivation": f"You're doing great! Keep pushing yourself and remember that every workout brings you closer to your goals!"
        }

    def generate_motivation_message(self, user_name: str, workout_history: List = None) -> str:
        prompt = f"""Generate a motivational message for {user_name} who is about to start their workout.
        Make it personal, encouraging, and energetic. Keep it under 100 words."""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content
