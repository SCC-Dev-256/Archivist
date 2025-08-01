#!/bin/bash

# Create necessary directories
mkdir -p logs

# Set environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export TESTING=true

# Activate virtual environment
if [ -d "venv_py311" ]; then
    source venv_py311/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start monitoring in the background
echo "Starting system monitoring..."
python3 scripts/monitoring/monitor.py &
MONITOR_PID=$!

# Wait for monitoring to initialize
sleep 5

# Test API endpoints
echo "Testing API endpoints..."
curl -s http://localhost:5050/api/queue > /dev/null && echo "✓ Queue API working" || echo "✗ Queue API failed"
curl -s http://localhost:5050/api/browse > /dev/null && echo "✓ Browse API working" || echo "✗ Browse API failed"
curl -s http://localhost:5050/api/csrf-token > /dev/null && echo "✓ CSRF API working" || echo "✗ CSRF API failed"

# Stop monitoring
echo "Stopping system monitoring..."
kill $MONITOR_PID 2>/dev/null || true

# Analyze results
echo "Test results saved to:"
echo "- System monitoring: logs/health_check.json"
echo "- Monitoring logs: logs/monitor.log" 