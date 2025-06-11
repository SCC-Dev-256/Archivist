#!/bin/bash

# Exit on error
set -e

# Set debug environment variables
export TRANSCRIPTION_DEBUG=true
export PYTHONPATH=/opt/Archivist
export LOG_LEVEL=DEBUG
export PYTHONUNBUFFERED=1  # Ensure Python output is not buffered
export RQ_WORKER_DEBUG=true  # Enable RQ worker debug mode
export RQ_WORKER_VERBOSE=true  # Enable verbose RQ worker output

# Create logs directory if it doesn't exist
mkdir -p /opt/Archivist/logs/transcription
mkdir -p /opt/Archivist/logs/memory
mkdir -p /opt/Archivist/logs/system

# Function to clean old debug files (keep last 7 days)
cleanup_old_logs() {
    find /opt/Archivist/logs/transcription -name "transcription_*.log" -mtime +7 -delete
    find /opt/Archivist/logs/transcription -name "debug_*.json" -mtime +7 -delete
    find /opt/Archivist/logs/memory -name "memory_*.log" -mtime +7 -delete
    find /opt/Archivist/logs/system -name "system_*.log" -mtime +7 -delete
}

# Function to monitor system resources
monitor_system() {
    while true; do
        echo "=== System Status $(date) ===" >> /opt/Archivist/logs/system/system_$(date +%Y%m%d).log
        free -h >> /opt/Archivist/logs/system/system_$(date +%Y%m%d).log
        df -h >> /opt/Archivist/logs/system/system_$(date +%Y%m%d).log
        ps aux | grep python >> /opt/Archivist/logs/system/system_$(date +%Y%m%d).log
        echo "=========================" >> /opt/Archivist/logs/system/system_$(date +%Y%m%d).log
        sleep 300  # Log every 5 minutes
    done
}

# Function to monitor memory usage
monitor_memory() {
    while true; do
        echo "=== Memory Usage $(date) ===" >> /opt/Archivist/logs/memory/memory_$(date +%Y%m%d).log
        ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 10 >> /opt/Archivist/logs/memory/memory_$(date +%Y%m%d).log
        echo "=========================" >> /opt/Archivist/logs/memory/memory_$(date +%Y%m%d).log
        sleep 60  # Log every minute
    done
}

# Clean up old logs before starting
cleanup_old_logs

# Start system monitoring in background
monitor_system &
SYSTEM_PID=$!

# Start memory monitoring in background
monitor_memory &
MEMORY_PID=$!

# Function to handle cleanup on exit
cleanup() {
    echo "Cleaning up..."
    kill $SYSTEM_PID $MEMORY_PID 2>/dev/null || true
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Activate virtual environment and start worker with debug settings
cd /opt/Archivist && \
source .venv/bin/activate && \
rq worker transcription \
    --url redis://localhost:6379/0 \
    --logging_level DEBUG \
    --log-format '%(asctime)s - %(name)s - %(levelname)s - %(message)s' \
    --name "archivist-worker-debug-$(date +%s)" \
    --verbose \
    --max-jobs 1 \
    --burst \
    --with-scheduler

# Note: The worker will output debug logs to:
# - /opt/Archivist/logs/transcription/transcription_*.log
# - /opt/Archivist/logs/transcription/debug_*.json
# - /opt/Archivist/logs/memory/memory_*.log
# - /opt/Archivist/logs/system/system_*.log 