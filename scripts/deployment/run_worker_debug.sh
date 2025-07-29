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

# Set debug environment variables
export CELERY_WORKER_DEBUG=true  # Enable Celery worker debug mode
export CELERY_WORKER_VERBOSE=true  # Enable verbose Celery worker output

# Set Redis configuration
export REDIS_HOST=${REDIS_HOST:-"localhost"}
export REDIS_PORT=${REDIS_PORT:-"6379"}
export REDIS_DB=${REDIS_DB:-"0"}
export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"

# Set Celery configuration for debugging
export CELERY_WORKER_LOGLEVEL=DEBUG
export CELERY_WORKER_CONCURRENCY=1
export CELERY_WORKER_PREFETCH_MULTIPLIER=1

# Run Celery worker in debug mode
echo "Starting Celery worker in debug mode..."
exec celery -A core.tasks worker \
    --loglevel=DEBUG \
    --concurrency=1 \
    --queues=transcription \
    --hostname=transcription-worker-debug@%h \
    --logfile=logs/celery-worker-debug.log \
    --pidfile=logs/celery-worker-debug.pid \
    --autoscale=1,1 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat 