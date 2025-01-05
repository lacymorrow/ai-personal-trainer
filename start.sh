#!/bin/bash

# Run database initialization
echo "🔄 Initializing database..."
python deploy.py

# Start the application
echo "🚀 Starting application..."
uvicorn main:app --host 0.0.0.0 --port $PORT
