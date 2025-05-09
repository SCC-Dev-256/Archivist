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

# Start the worker
start_process "python -m core.task_queue" "Worker" "python -m core.task_queue"

# Start the web app
start_process "python -m core.web_app" "Web App" "python -m core.web_app"

echo "Archivist system started successfully" 