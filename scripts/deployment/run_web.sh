#!/bin/bash

# Exit on error
set -e

# Parse command line arguments
MODE=${1:-"development"}
PORT=${2:-"5050"}
HOST=${3:-"0.0.0.0"}

# Activate virtual environment
if [ -d "venv_py311" ]; then
    source venv_py311/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    source .env
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Flask environment variables
export FLASK_APP=core.app
export PYTHONPATH=/opt/Archivist

# Check if Redis is running
if ! command -v redis-cli &> /dev/null; then
    echo "Redis CLI not found. Please install Redis."
    exit 1
fi

# Try to connect to Redis
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

# Start web server based on mode
if [ "$MODE" = "development" ]; then
    echo "Starting Flask development server..."
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export TESTING=false
    
    python3 -c "
import os
import sys
sys.path.insert(0, '/opt/Archivist')
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['TESTING'] = 'false'
from core.app import app
print('Starting Archivist Web UI for captioning system testing...')
app.socketio.run(app, host='$HOST', port=$PORT, debug=True, use_reloader=False)
"
elif [ "$MODE" = "production" ]; then
    echo "Starting Gunicorn production server..."
    export FLASK_ENV=production
    export FLASK_DEBUG=0
    
    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        echo "Gunicorn not found. Installing..."
        pip install gunicorn
    fi
    
    exec gunicorn \
        --bind $HOST:$PORT \
        --workers 4 \
        --timeout 120 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --log-level info \
        --reload \
        core.app:app
else
    echo "Invalid mode. Use 'development' or 'production'"
    echo "Usage: $0 [development|production] [port] [host]"
    echo "Example: $0 development 5050 0.0.0.0"
    exit 1
fi 