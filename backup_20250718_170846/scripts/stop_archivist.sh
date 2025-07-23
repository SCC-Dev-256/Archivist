#!/bin/bash

# Exit on any error
set -e

# Function to check if a process is running
check_process() {
    pgrep -f "$1" > /dev/null
}

# Function to stop a process if running
stop_process() {
    if check_process "$1"; then
        echo "Stopping $2..."
        pkill -f "$1"
        sleep 2
        if ! check_process "$1"; then
            echo "$2 stopped successfully"
        else
            echo "Failed to stop $2, forcing..."
            pkill -9 -f "$1"
            sleep 1
        fi
    else
        echo "$2 is not running"
    fi
}

echo "Stopping Archivist system..."

# Stop the web app first (to prevent new jobs from being queued)
stop_process "python -m core.web_app" "Web App"

# Stop the worker
stop_process "python -m core.task_queue" "Worker"

# Stop Redis (optional, uncomment if needed)
# echo "Stopping Redis..."
# sudo systemctl stop redis

echo "Archivist system stopped successfully" 