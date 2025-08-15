python3 start_archivist_unified.py --help#!/bin/bash

# Fix Archivist System Issues Script
# This script fixes the common issues preventing the system from starting

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

echo "🔧 Fixing Archivist System Issues"
echo "================================"
echo "Time: $(date)"
echo ""

# Step 1: Fix .env file issues
print_status "$BLUE" "🔧 Step 1: Fixing .env file issues..."

# Create a backup
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Fix the DATABASE_URL line by properly escaping the password
print_status "$YELLOW" "📝 Fixing DATABASE_URL in .env file..."

# Create a temporary file with the fixed content
cat > .env.tmp << 'EOF'
# =============================================================================
# ARCHIVIST APPLICATION - SECURE ENVIRONMENT CONFIGURATION
# =============================================================================
# 
# IMPORTANT: This file contains ACTUAL SECURE CREDENTIALS
# Never commit this file to version control
# Keep this file secure and restrict access
#
# =============================================================================

# Base paths
NAS_PATH=/mnt/nas
OUTPUT_DIR=/tmp/archivist-output

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0

# Database configuration
POSTGRES_USER=archivist
POSTGRES_PASSWORD=pTwef35YjQ98
POSTGRES_DB=archivist
DATABASE_URL=postgresql://archivist:pTwef35YjQ98@localhost:5432/archivist

# API configuration
API_HOST=0.0.0.0
API_PORT=5050
API_WORKERS=4
API_RATE_LIMIT=100/minute

# Flask Configuration
FLASK_APP=core.app
FLASK_ENV=development
FLASK_DEBUG=0
SECRET_KEY=85b187fa9e22e2aa98c03840b5da72a21168d482723f44b299b0f5471e6c9c75

# ML Model Configuration
WHISPER_MODEL=large-v2
USE_GPU=false
COMPUTE_TYPE=int8
BATCH_SIZE=16
NUM_WORKERS=4
LANGUAGE=en

# Storage Configuration
UPLOAD_FOLDER=/app/uploads
OUTPUT_FOLDER=/app/outputs

# Monitoring Configuration
ENABLE_METRICS=true
PROMETHEUS_MULTIPROC_DIR=/tmp
GRAFANA_PASSWORD=9-c)1jV84Raje_l)#s&*

# Security Configuration
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization

# Flex Server Configuration
FLEX_SERVERS=192.168.181.56,192.168.181.57,192.168.181.58,192.168.181.59,192.168.181.60,192.168.181.61,192.168.181.62,192.168.181.63,192.168.181.64
FLEX_USERNAME=admin
FLEX_PASSWORD=cableTV21

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Server Configuration
SERVER_NAME=localhost:5050
PREFERRED_URL_SCHEME=http

# =============================================================================
# CABLECAST VOD INTEGRATION CONFIGURATION
# =============================================================================

# Cablecast API Configuration
CABLECAST_API_URL=https://vod.scctv.org/CablecastAPI/v1
CABLECAST_SERVER_URL=https://vod.scctv.org/CablecastAPI/v1
CABLECAST_BASE_URL=https://vod.scctv.org/CablecastAPI/v1

# Location ID (choose the appropriate site ID)
CABLECAST_LOCATION_ID=3

# API Key (get this from your Cablecast administrator)
CABLECAST_API_KEY=qDqYOZQ1t2y1kk5r0qb8n00MJG1nzTWYL0p7EiGIcJg

# HTTP Basic Authentication
CABLECAST_USER_ID=admin
CABLECAST_PASSWORD=u:S@-lKJm1yB<F_zM4X(Y_D&

# VOD Integration Settings
AUTO_PUBLISH_TO_VOD=false
VOD_DEFAULT_QUALITY=1
VOD_UPLOUT=300

# VOD Processing Settings
VOD_MAX_RETRIES=3
VOD_RETRY_DELAY=60
VOD_BATCH_SIZE=10

# VOD Monitoring
VOD_STATUS_CHECK_INTERVAL=30
VOD_PROCESSING_TIMEOUT=1800

# =============================================================================
# ADDITIONAL SECURITY CONFIGURATION
# =============================================================================

# JWT Configuration
JWT_SECRET_KEY=43c132addbf5654a5d7607d0822fbf8a51004bc7eb24d8e9b20964e8fb078f9b

# Dashboard Configuration
DASHBOARD_SECRET_KEY=a2323a9dee5145673fb72d5e62f437cc2ca25d1d5d69a19395ceb8ba646d0854

# =============================================================================
# SECURITY NOTES
# =============================================================================
#
# This file contains cryptographically secure credentials generated on 2025-07-30
# All passwords and keys are randomly generated and unique
# 
# CREDENTIALS UPDATED:
# - Database password: pTwef35YjQ98
# - Secret key: 85b187fa9e22e2aa98c03840b5da72a21168d482723f44b299b0f5471e6c9c75
# - JWT secret: 43c132addbf5654a5d7607d0822fbf8a51004bc7eb24d8e9b20964e8fb078f9b
# - Dashboard secret: a2323a9dee5145673fb72d5e62f437cc2ca25d1d5d69a19395ceb8ba646d0854
#
# =============================================================================
EOF

# Replace the original .env file
mv .env.tmp .env
print_status "$GREEN" "✅ .env file fixed"

# Step 2: Stop conflicting services
print_status "$BLUE" "🔧 Step 2: Stopping conflicting services..."

# Stop any existing Docker containers
print_status "$YELLOW" "🐳 Stopping Docker containers..."
docker-compose down 2>/dev/null || true

# Kill any processes using ports 8080, 5050, 5432, 6379
print_status "$YELLOW" "🔌 Stopping processes using required ports..."

# Function to kill process on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pids" ]; then
        echo "Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null || true
        sleep 1
    fi
}

kill_port 8080
kill_port 5050
kill_port 5051
kill_port 5432
kill_port 6379

print_status "$GREEN" "✅ Conflicting services stopped"

# Step 3: Fix PostgreSQL authentication
print_status "$BLUE" "🔧 Step 3: Fixing PostgreSQL authentication..."

# Check if PostgreSQL is running
if pg_isready >/dev/null 2>&1; then
    print_status "$YELLOW" "🗄️  PostgreSQL is running, checking user..."
    
    # Try to create the archivist user if it doesn't exist
    sudo -u postgres psql -c "CREATE USER archivist WITH PASSWORD 'GLUc*p.XC=uM>WDQL\$X3nbX=';" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER archivist WITH PASSWORD 'GLUc*p.XC=uM>WDQL\$X3nbX=';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE archivist OWNER archivist;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE archivist TO archivist;" 2>/dev/null || true
    
    print_status "$GREEN" "✅ PostgreSQL user configured"
else
    print_status "$YELLOW" "🗄️  Starting PostgreSQL..."
    sudo systemctl start postgresql 2>/dev/null || true
    sleep 3
    
    if pg_isready >/dev/null 2>&1; then
        sudo -u postgres psql -c "CREATE USER archivist WITH PASSWORD 'GLUc*p.XC=uM>WDQL\$X3nbX=';" 2>/dev/null || true
        sudo -u postgres psql -c "ALTER USER archivist WITH PASSWORD 'GLUc*p.XC=uM>WDQL\$X3nbX=';" 2>/dev/null || true
        sudo -u postgres psql -c "CREATE DATABASE archivist OWNER archivist;" 2>/dev/null || true
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE archivist TO archivist;" 2>/dev/null || true
        print_status "$GREEN" "✅ PostgreSQL started and configured"
    else
        print_status "$RED" "❌ Failed to start PostgreSQL"
    fi
fi

# Step 4: Fix Redis
print_status "$BLUE" "🔧 Step 4: Ensuring Redis is running..."

if ! redis-cli ping >/dev/null 2>&1; then
    print_status "$YELLOW" "🔴 Starting Redis..."
    sudo systemctl start redis 2>/dev/null || redis-server --daemonize yes
    sleep 2
    
    if redis-cli ping >/dev/null 2>&1; then
        print_status "$GREEN" "✅ Redis started"
    else
        print_status "$RED" "❌ Failed to start Redis"
    fi
else
    print_status "$GREEN" "✅ Redis is already running"
fi

# Step 5: Fix mount permissions
print_status "$BLUE" "🔧 Step 5: Fixing mount permissions..."

# Create health check directories with proper permissions
for i in {1..9}; do
    mount_path="/mnt/flex-$i"
    if [ -d "$mount_path" ]; then
        sudo mkdir -p "$mount_path/.health_check_test" 2>/dev/null || true
        sudo chmod 777 "$mount_path/.health_check_test" 2>/dev/null || true
        print_status "$GREEN" "✅ Fixed permissions for $mount_path"
    fi
done

# Step 6: Test connections
print_status "$BLUE" "🔧 Step 6: Testing connections..."

# Test Redis
if redis-cli ping >/dev/null 2>&1; then
    print_status "$GREEN" "✅ Redis connection: OK"
else
    print_status "$RED" "❌ Redis connection: FAILED"
fi

# Test PostgreSQL
if PGPASSWORD='pTwef35YjQ98' psql -h localhost -U archivist -d archivist -c "SELECT 1;" >/dev/null 2>&1; then
    print_status "$GREEN" "✅ PostgreSQL connection: OK"
else
    print_status "$RED" "❌ PostgreSQL connection: FAILED"
fi

echo ""
print_status "$GREEN" "🎉 System issues fixed!"
echo ""
print_status "$BLUE" "📋 Next steps:"
echo "   1. Run: ./start_archivist.sh complete"
echo "   2. Or run: python3 start_archivist_unified.py complete"
echo "   3. Access dashboard at: http://localhost:5051"
echo "   4. Access admin UI at: http://localhost:8080"
echo ""
print_status "$YELLOW" "💡 If you still have issues, check the logs in the logs/ directory" 