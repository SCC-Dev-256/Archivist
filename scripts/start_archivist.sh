#!/bin/bash

# Exit on any error
set -e

# Load environment variables
source /opt/Archivist/.env

# Function to check if a process is running
check_process() {
    pgrep -f "$1" > /dev/null
}

# Function to start a process if not running
start_process() {
    if ! check_process "$1"; then
        echo "Starting $2..."
        cd /opt/Archivist
        source venv/bin/activate
        
        # Set Flask environment variables
        export FLASK_APP=core
        export FLASK_ENV=production
        export PYTHONPATH="${PYTHONPATH}:/opt/Archivist"
        
        # Set Redis configuration
        export REDIS_HOST=${REDIS_HOST:-"localhost"}
        export REDIS_PORT=${REDIS_PORT:-"6379"}
        export REDIS_DB=${REDIS_DB:-"0"}
        export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"
        
        # Set database configuration if not already set
        if [ -z "$DATABASE_URL" ]; then
            export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/archivist"
        fi
        
        # Set NAS and output paths if not already set
        if [ -z "$NAS_PATH" ]; then
            export NAS_PATH="/mnt"
        fi
        if [ -z "$OUTPUT_DIR" ]; then
            export OUTPUT_DIR="/mnt/transcriptions"
        fi
        
        # Create necessary directories
        mkdir -p "$OUTPUT_DIR"
        mkdir -p core/templates
        mkdir -p core/static
        mkdir -p logs
        
        # Start the process
        $3 &
        sleep 2
        if check_process "$1"; then
            echo "$2 started successfully"
        else
            echo "Failed to start $2"
            exit 1
        fi
    else
        echo "$2 is already running"
    fi
}

echo "Starting Archivist system..."

# Check Redis
if ! systemctl is-active --quiet redis; then
    echo "Starting Redis..."
    sudo systemctl start redis
    sleep 2
fi

# Verify Redis connection
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Error: Cannot connect to Redis. Please check Redis configuration."
    exit 1
fi

# Check PostgreSQL
if ! systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL..."
    sudo systemctl start postgresql
    sleep 2
fi

# Start the worker
start_process "python -m core.task_queue" "Worker" "python -m core.task_queue"

# Start the web app with gunicorn
start_process "gunicorn.*core:app" "Web App" "gunicorn --bind 0.0.0.0:5050 --workers 2 --timeout 120 --access-logfile logs/gunicorn-access.log --error-logfile logs/gunicorn-error.log --capture-output --log-level info core:app"

echo "Archivist system started successfully" 