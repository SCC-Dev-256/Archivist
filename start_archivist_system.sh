#!/bin/bash

# Archivist System Startup Script
# This script starts the complete Archivist VOD processing system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a service is running
service_running() {
    pgrep -f "$1" >/dev/null 2>&1
}

# Function to check Redis health
check_redis() {
    if command_exists redis-cli; then
        if redis-cli ping >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check PostgreSQL health
check_postgresql() {
    if command_exists pg_isready; then
        if pg_isready >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start Redis
start_redis() {
    print_status "$BLUE" "🔍 Checking Redis..."
    
    if check_redis; then
        print_status "$GREEN" "✅ Redis is already running"
        return 0
    fi
    
    print_status "$YELLOW" "🚀 Starting Redis..."
    
    # Try systemctl first
    if command_exists systemctl; then
        if sudo systemctl start redis 2>/dev/null; then
            sleep 2
            if check_redis; then
                print_status "$GREEN" "✅ Redis started via systemctl"
                return 0
            fi
        fi
    fi
    
    # Try direct redis-server
    if command_exists redis-server; then
        redis-server --daemonize yes
        sleep 2
        if check_redis; then
            print_status "$GREEN" "✅ Redis started directly"
            return 0
        fi
    fi
    
    print_status "$RED" "❌ Failed to start Redis"
    return 1
}

# Function to start PostgreSQL
start_postgresql() {
    print_status "$BLUE" "🔍 Checking PostgreSQL..."
    
    if check_postgresql; then
        print_status "$GREEN" "✅ PostgreSQL is already running"
        return 0
    fi
    
    print_status "$YELLOW" "🚀 Starting PostgreSQL..."
    
    # Try systemctl first
    if command_exists systemctl; then
        if sudo systemctl start postgresql 2>/dev/null; then
            sleep 3
            if check_postgresql; then
                print_status "$GREEN" "✅ PostgreSQL started via systemctl"
                return 0
            fi
        fi
    fi
    
    # Try pg_ctl
    if command_exists pg_ctl; then
        if pg_ctl -D /var/lib/postgresql/data start 2>/dev/null; then
            sleep 3
            if check_postgresql; then
                print_status "$GREEN" "✅ PostgreSQL started via pg_ctl"
                return 0
            fi
        fi
    fi
    
    print_status "$RED" "❌ Failed to start PostgreSQL"
    return 1
}

# Function to check Python environment
check_python_env() {
    print_status "$BLUE" "🔍 Checking Python environment..."
    
    if ! command_exists python3; then
        print_status "$RED" "❌ Python3 not found"
        return 1
    fi
    
    # Check if we're in a virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_status "$GREEN" "✅ Virtual environment active: $VIRTUAL_ENV"
    else
        print_status "$YELLOW" "⚠️  No virtual environment detected"
    fi
    
    # Check key dependencies
    local missing_deps=()
    
    python3 -c "import flask" 2>/dev/null || missing_deps+=("flask")
    python3 -c "import redis" 2>/dev/null || missing_deps+=("redis")
    python3 -c "import psycopg2" 2>/dev/null || missing_deps+=("psycopg2")
    python3 -c "import celery" 2>/dev/null || missing_deps+=("celery")
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        print_status "$GREEN" "✅ All key dependencies available"
        return 0
    else
        print_status "$RED" "❌ Missing dependencies: ${missing_deps[*]}"
        print_status "$YELLOW" "💡 Run: pip install -r requirements.txt"
        return 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "$BLUE" "📁 Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p output
    mkdir -p core/templates
    mkdir -p core/static
    mkdir -p pids
    
    print_status "$GREEN" "✅ Directories created"
}

# Function to set environment variables
setup_environment() {
    print_status "$BLUE" "⚙️  Setting up environment..."
    
    # Load .env file if it exists
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
        print_status "$GREEN" "✅ Environment variables loaded from .env"
    else
        print_status "$YELLOW" "⚠️  No .env file found, using defaults"
    fi
    
    # Set defaults
    export FLASK_APP=${FLASK_APP:-"core.app"}
    export FLASK_ENV=${FLASK_ENV:-"production"}
    export FLASK_DEBUG=${FLASK_DEBUG:-"0"}
    export PYTHONPATH="${PWD}:${PYTHONPATH}"
    
    print_status "$GREEN" "✅ Environment configured"
}

# Function to start the complete system
start_complete_system() {
    print_status "$BLUE" "🚀 Starting Complete Archivist System..."
    
    if [ -f "scripts/deployment/start_complete_system.py" ]; then
        python3 scripts/deployment/start_complete_system.py
    else
        print_status "$RED" "❌ Complete system script not found"
        return 1
    fi
}

# Function to start integrated system
start_integrated_system() {
    print_status "$BLUE" "🚀 Starting Integrated System..."
    
    if [ -f "scripts/deployment/start_integrated_system.py" ]; then
        python3 scripts/deployment/start_integrated_system.py
    else
        print_status "$RED" "❌ Integrated system script not found"
        return 1
    fi
}

# Function to start dashboard
start_dashboard() {
    print_status "$BLUE" "🚀 Starting Dashboard..."
    
    if [ -f "start_dashboard.sh" ]; then
        chmod +x start_dashboard.sh
        ./start_dashboard.sh
    else
        print_status "$RED" "❌ Dashboard script not found"
        return 1
    fi
}

# Main startup function
main() {
    echo "🚀 Archivist System Startup"
    echo "=========================="
    echo "Time: $(date)"
    echo ""
    
    # Create directories
    create_directories
    
    # Setup environment
    setup_environment
    
    # Check Python environment
    if ! check_python_env; then
        print_status "$RED" "❌ Python environment check failed"
        exit 1
    fi
    
    # Start Redis
    if ! start_redis; then
        print_status "$RED" "❌ Redis startup failed"
        exit 1
    fi
    
    # Start PostgreSQL
    if ! start_postgresql; then
        print_status "$RED" "❌ PostgreSQL startup failed"
        exit 1
    fi
    
    # Wait a moment for services to stabilize
    sleep 2
    
    # Final health check
    print_status "$BLUE" "🔍 Final health check..."
    
    if check_redis && check_postgresql; then
        print_status "$GREEN" "✅ All dependencies ready"
    else
        print_status "$RED" "❌ Health check failed"
        exit 1
    fi
    
    echo ""
    print_status "$GREEN" "🎉 Dependencies started successfully!"
    echo ""
    
    # Start the main system
    print_status "$BLUE" "🚀 Starting Archivist System..."
    echo ""
    
    # Try different startup methods
    if start_complete_system; then
        print_status "$GREEN" "✅ Complete system started"
    elif start_integrated_system; then
        print_status "$GREEN" "✅ Integrated system started"
    elif start_dashboard; then
        print_status "$GREEN" "✅ Dashboard started"
    else
        print_status "$RED" "❌ Failed to start any system"
        print_status "$YELLOW" "💡 Try running manually:"
        echo "   python3 scripts/deployment/start_complete_system.py"
        echo "   or"
        echo "   ./start_dashboard.sh"
        exit 1
    fi
}

# Run main function
main "$@" 