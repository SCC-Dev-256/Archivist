#!/bin/bash

# Simple Archivist Startup Script
# Uses different ports to avoid conflicts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

echo "🚀 Simple Archivist Startup"
echo "==========================="
echo "Time: $(date)"
echo ""

# Set environment variables
export FLASK_APP=core.app
export FLASK_ENV=development
export FLASK_DEBUG=0
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Use different ports to avoid conflicts
export API_PORT=5052
export DASHBOARD_PORT=5053

print_status "$BLUE" "🔍 Checking dependencies..."

# Check Redis
if redis-cli ping >/dev/null 2>&1; then
    print_status "$GREEN" "✅ Redis: OK"
else
    print_status "$RED" "❌ Redis: Not running"
    exit 1
fi

# Check PostgreSQL
if pg_isready >/dev/null 2>&1; then
    print_status "$GREEN" "✅ PostgreSQL: OK"
else
    print_status "$RED" "❌ PostgreSQL: Not running"
    exit 1
fi

print_status "$GREEN" "✅ All dependencies ready"
echo ""

print_status "$BLUE" "🚀 Starting Archivist on alternative ports..."
print_status "$YELLOW" "📊 Dashboard will be on: http://localhost:5053"
print_status "$YELLOW" "🖥️  Admin UI will be on: http://localhost:5052"
echo ""

# Start the integrated system with custom ports
python3 scripts/deployment/start_integrated_system.py 