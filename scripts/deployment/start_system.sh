#!/bin/bash

# Exit on any error
set -e

# Parse command line arguments
MODE=${1:-"full"}
COMPONENT=${2:-""}

# Load environment variables
if [ -f ".env" ]; then
    source .env
fi

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
export DATABASE_URL=${DATABASE_URL:-"postgresql://archivist:archivist_password@localhost:5432/archivist"}

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

# Function to check service status
check_service() {
    local service_name=$1
    local check_command=$2
    
    if eval "$check_command" > /dev/null 2>&1; then
        echo "✅ $service_name is running"
        return 0
    else
        echo "❌ $service_name is not running"
        return 1
    fi
}

# Start Redis if not running
if ! check_service "Redis" "redis-cli ping"; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 2
    if check_service "Redis" "redis-cli ping"; then
        echo "Redis started successfully"
    else
        echo "Failed to start Redis"
        exit 1
    fi
fi

# Start PostgreSQL if not running
if ! check_service "PostgreSQL" "pg_isready"; then
    echo "Starting PostgreSQL..."
    pg_ctl -D /var/lib/postgresql/data start
    sleep 2
    if check_service "PostgreSQL" "pg_isready"; then
        echo "PostgreSQL started successfully"
    else
        echo "Failed to start PostgreSQL"
        exit 1
    fi
fi

# Start components based on mode
case $MODE in
    "web")
        echo "Starting web server only..."
        start_process "gunicorn.*core.app:app" "Web Server" "bash scripts/deployment/run_web.sh production"
        ;;
    "worker")
        echo "Starting worker only..."
        start_process "celery.*worker" "Celery Worker" "bash scripts/deployment/run_worker.sh"
        ;;
    "full")
        echo "Starting complete Archivist system..."
        start_process "gunicorn.*core.app:app" "Web Server" "bash scripts/deployment/run_web.sh production"
        start_process "celery.*worker" "Celery Worker" "bash scripts/deployment/run_worker.sh"
        ;;
    "development")
        echo "Starting development system..."
        start_process "python.*test_web_ui.py" "Development Server" "python3 test_web_ui.py"
        ;;
    *)
        echo "Invalid mode. Use: web, worker, full, or development"
        echo "Usage: $0 [web|worker|full|development]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Archivist system started successfully!"
echo "📊 System Status:"
check_service "Redis" "redis-cli ping"
check_service "PostgreSQL" "pg_isready"
echo "🌐 Web UI available at: http://${API_HOST}:${API_PORT}"
echo "📚 API documentation available at: http://${API_HOST}:${API_PORT}/api/docs"
echo ""
echo "📋 Useful commands:"
echo "  Monitor system: python3 scripts/monitoring/monitor.py"
echo "  View logs: tail -f logs/archivist.log"
echo "  Stop system: bash scripts/deployment/stop_archivist.sh"