#!/bin/bash

# Exit on error
set -e

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load environment variables
source /opt/Archivist/.env

# Create logs directory if it doesn't exist
mkdir -p logs

# Set Redis configuration
export REDIS_HOST=${REDIS_HOST:-"redis"}
export REDIS_PORT=${REDIS_PORT:-"6379"}
export REDIS_DB=${REDIS_DB:-"0"}
export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"

# Run the RQ worker with logging, redirect output to log file
exec rq worker transcription \
    --url "${REDIS_URL}" \
    --logging_level INFO \
    --log-format '%(asctime)s - %(name)s - %(levelname)s - %(message)s' \
    >> logs/rq-worker.log 2>&1 