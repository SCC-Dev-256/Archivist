#!/bin/bash

# Centralized Archivist System Startup Script (Shell Version)
# This script starts ALL services in the correct order with proper integration

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_PATH="$PROJECT_ROOT/venv_py311"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# Service ports
REDIS_PORT=6379
POSTGRESQL_PORT=5432
ADMIN_UI_PORT=8080
DASHBOARD_PORT=5051

# Service startup order
SERVICES=("redis" "postgresql" "celery_worker" "celery_beat" "vod_sync_monitor" "admin_ui" "monitoring_dashboard")

# Restart configuration
MAX_RESTART_ATTEMPTS=3
RESTART_DELAY=10

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

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_DIR/centralized_system.log"
}

# Function to create necessary directories
setup_directories() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    mkdir -p "$PROJECT_ROOT/output"
    mkdir -p "$PROJECT_ROOT/core/templates"
    mkdir -p "$PROJECT_ROOT/core/static"
}

# Function to check if a service is running
is_service_running() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# Function to save service PID
save_pid() {
    local service_name=$1
    local pid=$2
    echo "$pid" > "$PID_DIR/${service_name}.pid"
}

# Function to check Redis health
check_redis_health() {
    if command -v redis-cli > /dev/null 2>&1; then
        if redis-cli ping > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check PostgreSQL health
check_postgresql_health() {
    if command -v pg_isready > /dev/null 2>&1; then
        if pg_isready > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check Admin UI health
check_admin_ui_health() {
    if command -v curl > /dev/null 2>&1; then
        if curl -s "http://localhost:$ADMIN_UI_PORT/api/admin/status" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check Dashboard health
check_dashboard_health() {
    if command -v curl > /dev/null 2>&1; then
        if curl -s "http://localhost:$DASHBOARD_PORT/api/health" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start Redis
start_redis() {
    if check_redis_health; then
        print_status "$GREEN" "✅ Redis is already running"
        return 0
    fi
    
    print_status "$BLUE" "Starting Redis..."
    if command -v redis-server > /dev/null 2>&1; then
        redis-server --daemonize yes
        sleep 2
        
        if check_redis_health; then
            print_status "$GREEN" "✅ Redis started successfully"
            save_pid "redis" $(pgrep redis-server)
            return 0
        else
            print_status "$RED" "❌ Failed to start Redis"
            return 1
        fi
    else
        print_status "$RED" "❌ Redis server not found"
        return 1
    fi
}

# Function to start PostgreSQL
start_postgresql() {
    if check_postgresql_health; then
        print_status "$GREEN" "✅ PostgreSQL is already running"
        return 0
    fi
    
    print_status "$BLUE" "Starting PostgreSQL..."
    if command -v pg_ctl > /dev/null 2>&1; then
        pg_ctl -D /var/lib/postgresql/data start > /dev/null 2>&1
        sleep 3
        
        if check_postgresql_health; then
            print_status "$GREEN" "✅ PostgreSQL started successfully"
            save_pid "postgresql" $(pgrep postgres)
            return 0
        else
            print_status "$RED" "❌ Failed to start PostgreSQL"
            return 1
        fi
    else
        print_status "$RED" "❌ PostgreSQL not found"
        return 1
    fi
}

# Function to start Celery worker
start_celery_worker() {
    print_status "$BLUE" "Starting Celery worker..."
    
    cd "$PROJECT_ROOT"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    # Start Celery worker in background
    celery -A core.tasks worker --loglevel=info --concurrency=2 \
        --pidfile="$PID_DIR/celery_worker.pid" \
        --logfile="$LOG_DIR/celery_worker.log" > /dev/null 2>&1 &
    
    local pid=$!
    save_pid "celery_worker" $pid
    
    sleep 5
    
    if [ -f "$PID_DIR/celery_worker.pid" ] && ps -p $pid > /dev/null 2>&1; then
        print_status "$GREEN" "✅ Celery worker started successfully"
        return 0
    else
        print_status "$RED" "❌ Failed to start Celery worker"
        return 1
    fi
}

# Function to start Celery beat
start_celery_beat() {
    print_status "$BLUE" "Starting Celery beat scheduler..."
    
    cd "$PROJECT_ROOT"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    # Start Celery beat in background
    celery -A core.tasks beat --loglevel=info \
        --pidfile="$PID_DIR/celery_beat.pid" \
        --logfile="$LOG_DIR/celery_beat.log" > /dev/null 2>&1 &
    
    local pid=$!
    save_pid "celery_beat" $pid
    
    sleep 5
    
    if [ -f "$PID_DIR/celery_beat.pid" ] && ps -p $pid > /dev/null 2>&1; then
        print_status "$GREEN" "✅ Celery beat scheduler started successfully"
        return 0
    else
        print_status "$RED" "❌ Failed to start Celery beat scheduler"
        return 1
    fi
}

# Function to start VOD sync monitor
start_vod_sync_monitor() {
    print_status "$BLUE" "Starting VOD sync monitor..."
    
    cd "$PROJECT_ROOT"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    # Set PYTHONPATH to project root so 'core' is found
    PYTHONPATH="$PROJECT_ROOT" python3 scripts/monitoring/vod_sync_monitor.py --single-run > "$LOG_DIR/vod_sync_monitor.log" 2>&1 &
    local pid=$!
    save_pid "vod_sync_monitor" $pid
    
    sleep 2
    
    if ps -p $pid > /dev/null 2>&1; then
        print_status "$GREEN" "✅ VOD sync monitor started successfully"
        return 0
    else
        print_status "$RED" "❌ Failed to start VOD sync monitor"
        return 1
    fi
}

# Function to start Admin UI
start_admin_ui() {
    print_status "$BLUE" "Starting Admin UI..."
    
    cd "$PROJECT_ROOT"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    python3 -m core.admin_ui > "$LOG_DIR/admin_ui.log" 2>&1 &
    local pid=$!
    save_pid "admin_ui" $pid
    
    # Wait for Admin UI to start
    for i in {1..30}; do
        if check_admin_ui_health; then
            print_status "$GREEN" "✅ Admin UI started successfully"
            return 0
        fi
        sleep 1
    done
    
    print_status "$RED" "❌ Failed to start Admin UI"
    return 1
}

# Function to start monitoring dashboard
start_monitoring_dashboard() {
    print_status "$BLUE" "Starting monitoring dashboard..."
    
    cd "$PROJECT_ROOT"
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    
    python3 -m core.monitoring.integrated_dashboard > "$LOG_DIR/monitoring_dashboard.log" 2>&1 &
    local pid=$!
    save_pid "monitoring_dashboard" $pid
    
    # Wait for dashboard to start
    for i in {1..30}; do
        if check_dashboard_health; then
            print_status "$GREEN" "✅ Monitoring dashboard started successfully"
            return 0
        fi
        sleep 1
    done
    
    print_status "$RED" "❌ Failed to start monitoring dashboard"
    return 1
}





# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        print_status "$BLUE" "Stopping $service_name (PID: $pid)..."
        
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
            sleep 2
            
            if ps -p "$pid" > /dev/null 2>&1; then
                print_status "$YELLOW" "Force killing $service_name..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        
        rm -f "$pid_file"
        print_status "$GREEN" "✅ $service_name stopped"
    fi
}

# Function to stop all services
stop_all_services() {
    print_status "$BLUE" "Stopping all services..."
    
    # Stop in reverse order
    for ((i=${#SERVICES[@]}-1; i>=0; i--)); do
        stop_service "${SERVICES[$i]}"
    done
    
    # Stop Redis and PostgreSQL
    if command -v redis-cli > /dev/null 2>&1; then
        redis-cli shutdown > /dev/null 2>&1 || true
    fi
    
    if command -v pg_ctl > /dev/null 2>&1; then
        pg_ctl -D /var/lib/postgresql/data stop > /dev/null 2>&1 || true
    fi
    
    print_status "$GREEN" "✅ All services stopped"
}

# Function to check dependencies
check_dependencies() {
    print_status "$BLUE" "Checking system dependencies..."
    
    # Check Python
    if ! command -v python3 > /dev/null 2>&1; then
        print_status "$RED" "❌ Python3 not found"
        return 1
    fi
    
    # Check virtual environment
    if [ ! -d "$VENV_PATH" ]; then
        print_status "$YELLOW" "⚠️ Virtual environment not found at $VENV_PATH"
    fi
    
    # Check flex mounts
    local flex_mounts=("/mnt/flex-1" "/mnt/flex-2" "/mnt/flex-3" "/mnt/flex-4" "/mnt/flex-5")
    for mount in "${flex_mounts[@]}"; do
        if mountpoint -q "$mount"; then
            print_status "$GREEN" "✅ Flex mount $mount available"
        else
            print_status "$YELLOW" "⚠️ Flex mount $mount not mounted"
        fi
    done
    
    print_status "$GREEN" "✅ Dependencies check completed"
    return 0
}

# Function to start all services
start_all_services() {
    print_status "$BLUE" "Starting all services in order..."
    
    for service in "${SERVICES[@]}"; do
        case $service in
            "redis")
                if ! start_redis; then
                    print_status "$RED" "❌ Failed to start Redis, stopping startup"
                    return 1
                fi
                ;;
            "postgresql")
                if ! start_postgresql; then
                    print_status "$RED" "❌ Failed to start PostgreSQL, stopping startup"
                    return 1
                fi
                ;;

            "celery_worker")
                if ! start_celery_worker; then
                    print_status "$RED" "❌ Failed to start Celery worker, stopping startup"
                    return 1
                fi
                ;;
            "celery_beat")
                if ! start_celery_beat; then
                    print_status "$RED" "❌ Failed to start Celery beat, stopping startup"
                    return 1
                fi
                ;;
            "vod_sync_monitor")
                if ! start_vod_sync_monitor; then
                    print_status "$YELLOW" "⚠️ Failed to start VOD sync monitor, continuing..."
                fi
                ;;
            "admin_ui")
                if ! start_admin_ui; then
                    print_status "$RED" "❌ Failed to start Admin UI, stopping startup"
                    return 1
                fi
                ;;
            "monitoring_dashboard")
                if ! start_monitoring_dashboard; then
                    print_status "$RED" "❌ Failed to start monitoring dashboard, stopping startup"
                    return 1
                fi
                ;;
        esac
        
        sleep 2
    done
    
    print_status "$GREEN" "✅ All services started successfully"
    return 0
}

# Function to show status
show_status() {
    print_status "$BLUE" "Service Status:"
    echo "=================="
    
    for service in "${SERVICES[@]}"; do
        if [ "$service" = "redis" ]; then
            if check_redis_health; then
                print_status "$GREEN" "✅ redis: Running (via health check)"
            else
                print_status "$RED" "❌ redis: Not running"
            fi
        elif [ "$service" = "postgresql" ]; then
            if check_postgresql_health; then
                print_status "$GREEN" "✅ postgresql: Running (via health check)"
            else
                print_status "$RED" "❌ postgresql: Not running"
            fi

        elif [ "$service" = "vod_sync_monitor" ]; then
            # Check if VOD sync monitor has run recently (within last 10 minutes)
            local log_file="$LOG_DIR/vod_sync_monitor.log"
            if [ -f "$log_file" ]; then
                local last_modified=$(stat -c %Y "$log_file" 2>/dev/null || echo "0")
                local current_time=$(date +%s)
                local time_diff=$((current_time - last_modified))
                
                if [ $time_diff -lt 600 ]; then  # 10 minutes = 600 seconds
                    print_status "$GREEN" "✅ vod_sync_monitor: Active (last run: ${time_diff}s ago)"
                else
                    print_status "$YELLOW" "⚠️ vod_sync_monitor: Inactive (last run: ${time_diff}s ago)"
                fi
            else
                print_status "$RED" "❌ vod_sync_monitor: Not running"
            fi
        else
            local pid_file="$PID_DIR/${service}.pid"
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                if ps -p "$pid" > /dev/null 2>&1; then
                    print_status "$GREEN" "✅ $service: Running (PID: $pid)"
                else
                    print_status "$RED" "❌ $service: Not running"
                fi
            else
                print_status "$RED" "❌ $service: Not running"
            fi
        fi
    done
    
    echo ""
    print_status "$BLUE" "Health Checks:"
    echo "=============="
    
    if check_redis_health; then
        print_status "$GREEN" "✅ Redis: Healthy"
    else
        print_status "$RED" "❌ Redis: Unhealthy"
    fi
    
    if check_postgresql_health; then
        print_status "$GREEN" "✅ PostgreSQL: Healthy"
    else
        print_status "$RED" "❌ PostgreSQL: Unhealthy"
    fi
    
    if check_admin_ui_health; then
        print_status "$GREEN" "✅ Admin UI: Healthy"
    else
        print_status "$RED" "❌ Admin UI: Unhealthy"
    fi
    
    if check_dashboard_health; then
        print_status "$GREEN" "✅ Monitoring Dashboard: Healthy"
    else
        print_status "$RED" "❌ Monitoring Dashboard: Unhealthy"
    fi
}

# Function to handle cleanup on exit
cleanup() {
    print_status "$BLUE" "Shutting down gracefully..."
    stop_all_services
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main function
main() {
    echo "🚀 Starting Centralized Archivist System"
    echo "============================================================"
    
    # Setup directories
    setup_directories
    
    # Check dependencies
    if ! check_dependencies; then
        print_status "$RED" "Dependency check failed. Exiting."
        exit 1
    fi
    
    # Start all services
    if ! start_all_services; then
        print_status "$RED" "Failed to start all services. Exiting."
        exit 1
    fi
    
    # Show final status
    echo ""
    show_status
    
    # Print access information
    echo ""
    print_status "$GREEN" "🎉 Centralized Archivist System Started Successfully!"
    echo "============================================================"
    print_status "$BLUE" "📊 Admin UI: http://0.0.0.0:$ADMIN_UI_PORT"
    print_status "$BLUE" "📈 Monitoring Dashboard: http://localhost:$DASHBOARD_PORT"
    print_status "$BLUE" "📚 API Documentation: http://0.0.0.0:$ADMIN_UI_PORT/api/docs"
    print_status "$BLUE" "🔗 Unified Queue API: http://0.0.0.0:$ADMIN_UI_PORT/api/unified-queue/docs"
    print_status "$BLUE" "⏰ VOD Processing Schedule: ${VOD_PROCESSING_TIME:-19:00} daily"
    print_status "$BLUE" "🔄 Celery Workers: 2 concurrent workers active"
    print_status "$BLUE" "📅 Scheduled Tasks: Daily caption check, VOD processing, cleanup"
    print_status "$BLUE" "🎬 Flex Server Integration: Direct file access enabled"
    print_status "$BLUE" "📋 Sequential Processing: Videos processed one at a time"
    print_status "$BLUE" "🔄 Auto-restart: Enabled (max $MAX_RESTART_ATTEMPTS attempts)"
    echo "============================================================"
    
    # Keep script running
    while true; do
        sleep 10
        # Optional: Add periodic health checks here
    done
}

# Run main function
main "$@" 