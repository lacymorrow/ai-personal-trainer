#!/bin/bash
set -e

echo "🚀 Starting AI Personal Trainer..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 5

# Initialize database
echo "🔄 Initializing database..."
python deploy.py

# Start the application
echo "✨ Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
