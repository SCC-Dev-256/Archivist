#!/bin/bash

# Celery Beat Startup Script
# This script starts the Celery beat scheduler for the Archivist system

set -e

# Configuration
SCHEDULER="celery.beat.PersistentScheduler"
LOG_LEVEL="info"

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

# Function to check if Celery beat is already running
check_beat_running() {
    pgrep -f "celery.*beat" > /dev/null
}

# Function to stop existing beat processes
stop_beat() {
    if check_beat_running; then
        print_status $YELLOW "Stopping existing Celery beat processes..."
        pkill -f "celery.*beat"
        sleep 2
        if check_beat_running; then
            print_status $YELLOW "Force killing remaining beat processes..."
            pkill -9 -f "celery.*beat"
            sleep 1
        fi
    fi
}

# Function to check Redis connection
check_redis() {
    if ! command -v redis-cli &> /dev/null; then
        print_status $RED "Redis CLI not found. Please install Redis."
        exit 1
    fi
    
    if ! redis-cli ping &> /dev/null; then
        print_status $RED "Cannot connect to Redis. Please start Redis first."
        exit 1
    fi
    
    print_status $GREEN "✅ Redis connection successful"
}

# Function to check Python environment
check_python_env() {
    if [ ! -d "venv_py311" ]; then
        print_status $RED "Virtual environment not found. Please run setup first."
        exit 1
    fi
    
    print_status $GREEN "✅ Python environment found"
}

# Function to start the beat scheduler
start_beat() {
    print_status $BLUE "Starting Celery beat scheduler..."
    print_status $BLUE "Scheduler: $SCHEDULER"
    print_status $BLUE "Log Level: $LOG_LEVEL"
    
    # Activate virtual environment
    source venv_py311/bin/activate
    
    # Start the beat scheduler
    exec celery -A core.tasks beat \
        --loglevel=$LOG_LEVEL \
        --scheduler=$SCHEDULER
}

# Main execution
main() {
    print_status $BLUE "⏰ Celery Beat Scheduler Startup Script"
    print_status $BLUE "========================================"
    
    # Check if we're in the right directory
    if [ ! -f "core/tasks/__init__.py" ]; then
        print_status $RED "❌ Not in Archivist project directory"
        print_status $RED "Please run this script from the project root"
        exit 1
    fi
    
    # Check dependencies
    check_python_env
    check_redis
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --stop)
                stop_beat
                print_status $GREEN "✅ Beat scheduler stopped"
                exit 0
                ;;
            --restart)
                stop_beat
                ;;
            --scheduler)
                SCHEDULER="$2"
                shift 2
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --stop              Stop Celery beat scheduler"
                echo "  --restart           Restart beat scheduler (stop then start)"
                echo "  --scheduler NAME    Set scheduler (default: celery.beat.PersistentScheduler)"
                echo "  --log-level LEVEL   Set log level (default: info)"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                print_status $RED "Unknown option: $1"
                print_status $RED "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Start the beat scheduler
    start_beat
}

# Run main function
main "$@" 