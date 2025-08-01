#!/bin/bash

# Exit on error
set -e

# Activate virtual environment
if [ -d "venv_py311" ]; then
    source venv_py311/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load environment variables
source /opt/Archivist/.env

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Redis configuration
export REDIS_HOST=${REDIS_HOST:-"localhost"}
export REDIS_PORT=${REDIS_PORT:-"6379"}
export REDIS_DB=${REDIS_DB:-"0"}
export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"

# Run Celery worker for transcription tasks
echo "Starting Celery worker for transcription tasks..."
exec celery -A core.tasks worker \
    --loglevel=INFO \
    --concurrency=2 \
    --queues=transcription \
    --hostname=transcription-worker@%h \
    --logfile=logs/celery-worker.log \
    --pidfile=logs/celery-worker.pid 