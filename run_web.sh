#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Flask environment variables
export FLASK_APP=core.app
export FLASK_ENV=production
export PYTHONPATH=/opt/Archivist
export DATABASE_URL="postgresql://archivist:archivist_password@localhost:5432/archivist"

# Check if Redis is running
if ! command -v redis-cli &> /dev/null; then
    echo "Redis CLI not found. Please install Redis."
    exit 1
fi

# Try to connect to Redis without authentication
if ! redis-cli ping &> /dev/null; then
    echo "Warning: Could not connect to Redis. The application will use in-memory storage instead."
    export CACHE_TYPE='simple'
    export RATELIMIT_STORAGE_URL='memory://'
fi

# Check if PostgreSQL is running (if using PostgreSQL)
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == postgresql://* ]]; then
    if ! command -v pg_isready &> /dev/null; then
        echo "PostgreSQL client not found. Please install PostgreSQL client."
        exit 1
    fi
    
    if ! pg_isready -h localhost &> /dev/null; then
        echo "PostgreSQL is not running. Please start PostgreSQL first."
        exit 1
    fi
fi

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:5050 \
    --workers 4 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output \
    --log-level info \
    --reload \
    core.app:app 