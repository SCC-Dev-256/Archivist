#!/bin/bash

# Create necessary directories
mkdir -p logs

# Start monitoring in the background
echo "Starting system monitoring..."
python3 scripts/monitor.py &
MONITOR_PID=$!

# Wait for monitoring to initialize
sleep 5

# Run load test
echo "Running load test..."
python3 tests/load_test.py

# Stop monitoring
echo "Stopping system monitoring..."
kill $MONITOR_PID

# Analyze results
echo "Test results saved to:"
echo "- Load test results: load_test_results.json"
echo "- System monitoring: logs/health_check.json"
echo "- Monitoring logs: logs/monitor.log" 