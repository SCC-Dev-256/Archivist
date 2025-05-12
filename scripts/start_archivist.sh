#!/bin/bash

# Exit on any error
set -e

# Load environment variables
source /opt/Archivist/.env

# Create necessary directories
mkdir -p logs
mkdir -p output
mkdir -p core/templates
mkdir -p core/static

# Set Flask environment variables
export FLASK_APP=core.app
export FLASK_ENV=production
export FLASK_DEBUG=0

# Set Redis configuration
export REDIS_HOST=${REDIS_HOST:-"localhost"}
export REDIS_PORT=${REDIS_PORT:-"6379"}
export REDIS_DB=${REDIS_DB:-"0"}
export REDIS_URL="redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}"

# Set PostgreSQL configuration
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost:5432/archivist"}

# Set API configuration
export API_HOST=${API_HOST:-"0.0.0.0"}
export API_PORT=${API_PORT:-"5050"}
export API_WORKERS=${API_WORKERS:-"2"}

# Set server name for URL generation
export SERVER_NAME=${SERVER_NAME:-"${API_HOST}:${API_PORT}"}
export PREFERRED_URL_SCHEME=${PREFERRED_URL_SCHEME:-"http"}

# Set CORS configuration
export CORS_ORIGINS=${CORS_ORIGINS:-"*"}

# Function to start a process
start_process() {
    local pattern=$1
    local name=$2
    local command=$3
    
    if ! pgrep -f "$pattern" > /dev/null; then
        echo "Starting $name..."
        eval "$command" &
        sleep 2
        if pgrep -f "$pattern" > /dev/null; then
            echo "$name started successfully"
        else
            echo "Failed to start $name"
            exit 1
        fi
    else
        echo "$name is already running"
    fi
}

# Start Redis if not running
if ! pgrep redis-server > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 2
    if ! redis-cli ping > /dev/null; then
        echo "Failed to start Redis"
        exit 1
    fi
    echo "Redis started successfully"
else
    echo "Redis is already running"
fi

# Start PostgreSQL if not running
if ! pgrep postgres > /dev/null; then
    echo "Starting PostgreSQL..."
    pg_ctl -D /var/lib/postgresql/data start
    sleep 2
    if ! pg_isready; then
        echo "Failed to start PostgreSQL"
        exit 1
    fi
    echo "PostgreSQL started successfully"
else
    echo "PostgreSQL is already running"
fi

# Start the web app
start_process "gunicorn.*core:app" "Web App" "gunicorn --bind ${API_HOST}:${API_PORT} --workers ${API_WORKERS} --timeout 120 --access-logfile logs/gunicorn-access.log --error-logfile logs/gunicorn-error.log --capture-output --log-level info core:app"

echo "Archivist system started successfully"
echo "Web UI available at: http://${API_HOST}:${API_PORT}"
echo "API documentation available at: http://${API_HOST}:${API_PORT}/api/docs" 