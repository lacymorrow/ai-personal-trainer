#!/bin/bash
set -e

echo "🚀 Starting AI Personal Trainer..."

# Start the application
echo "✨ Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug
