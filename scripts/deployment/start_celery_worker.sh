#!/bin/bash

# Celery Worker Startup Script
# This script starts the Celery worker for the Archivist system

set -e

# Configuration
WORKER_NAME="vod_worker@%h"
CONCURRENCY=4
QUEUES="vod_processing,default"
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

# Function to check if Celery worker is already running
check_worker_running() {
    pgrep -f "celery.*worker" > /dev/null
}

# Function to stop existing workers
stop_workers() {
    if check_worker_running; then
        print_status $YELLOW "Stopping existing Celery workers..."
        pkill -f "celery.*worker"
        sleep 2
        if check_worker_running; then
            print_status $YELLOW "Force killing remaining workers..."
            pkill -9 -f "celery.*worker"
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

# Function to start the worker
start_worker() {
    print_status $BLUE "Starting Celery worker..."
    print_status $BLUE "Worker Name: $WORKER_NAME"
    print_status $BLUE "Concurrency: $CONCURRENCY"
    print_status $BLUE "Queues: $QUEUES"
    print_status $BLUE "Log Level: $LOG_LEVEL"
    
    # Activate virtual environment
    source venv_py311/bin/activate
    
    # Start the worker
    exec celery -A core.tasks worker \
        --loglevel=$LOG_LEVEL \
        --concurrency=$CONCURRENCY \
        --hostname=$WORKER_NAME \
        --queues=$QUEUES
}

# Main execution
main() {
    print_status $BLUE "🚀 Celery Worker Startup Script"
    print_status $BLUE "=================================="
    
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
                stop_workers
                print_status $GREEN "✅ Workers stopped"
                exit 0
                ;;
            --restart)
                stop_workers
                ;;
            --concurrency)
                CONCURRENCY="$2"
                shift 2
                ;;
            --queues)
                QUEUES="$2"
                shift 2
                ;;
            --name)
                WORKER_NAME="$2"
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
                echo "  --stop              Stop all Celery workers"
                echo "  --restart           Restart workers (stop then start)"
                echo "  --concurrency N     Set worker concurrency (default: 4)"
                echo "  --queues LIST       Set queues (default: vod_processing,default)"
                echo "  --name NAME         Set worker name (default: vod_worker@%h)"
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
    
    # Start the worker
    start_worker
}

# Run main function
main "$@" 