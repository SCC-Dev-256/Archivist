#!/bin/bash
"""
Frontend Quality Gate Script

This script runs a comprehensive set of frontend tests to ensure code quality
before committing changes. It should be run as a pre-commit hook or manually
before pushing changes.
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/opt/Archivist"
VENV_PATH="$PROJECT_ROOT/venv_py311"
BASE_URL="http://localhost:5050"
TEST_TIMEOUT=300  # 5 minutes

echo -e "${BLUE}🎯 Frontend Quality Gate${NC}"
echo "=================================="

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    else
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

# Function to check if web server is running
check_web_server() {
    echo -e "${BLUE}Checking web server status...${NC}"
    
    if curl -s "$BASE_URL" > /dev/null 2>&1; then
        print_status "PASS" "Web server is running"
        return 0
    else
        print_status "FAIL" "Web server is not running"
        echo "Starting web server..."
        cd "$PROJECT_ROOT"
        source "$VENV_PATH/bin/activate"
        python3 test_web_ui.py &
        SERVER_PID=$!
        
        # Wait for server to start
        for i in {1..30}; do
            if curl -s "$BASE_URL" > /dev/null 2>&1; then
                print_status "PASS" "Web server started successfully"
                return 0
            fi
            sleep 1
        done
        
        print_status "FAIL" "Failed to start web server"
        return 1
    fi
}

# Function to run quick tests
run_quick_tests() {
    echo -e "${BLUE}Running quick frontend tests...${NC}"
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    # Run quick GUI tests
    echo "Running GUI tests..."
    if python3 tests/frontend/test_frontend_gui.py > /tmp/gui_test.log 2>&1; then
        print_status "PASS" "GUI tests passed"
    else
        print_status "FAIL" "GUI tests failed"
        echo "GUI test log:"
        tail -20 /tmp/gui_test.log
        return 1
    fi
    
    # Run WebSocket tests
    echo "Running WebSocket tests..."
    if python3 tests/frontend/test_websocket_functionality.py > /tmp/websocket_test.log 2>&1; then
        print_status "PASS" "WebSocket tests passed"
    else
        print_status "FAIL" "WebSocket tests failed"
        echo "WebSocket test log:"
        tail -20 /tmp/websocket_test.log
        return 1
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}Running performance tests...${NC}"
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    if python3 tests/frontend/test_performance.py > /tmp/performance_test.log 2>&1; then
        print_status "PASS" "Performance tests passed"
    else
        print_status "FAIL" "Performance tests failed"
        echo "Performance test log:"
        tail -20 /tmp/performance_test.log
        return 1
    fi
}

# Function to check code quality
check_code_quality() {
    echo -e "${BLUE}Checking code quality...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Check for TODO/FIXME comments
    echo "Checking for TODO/FIXME comments..."
    TODO_COUNT=$(grep -r "TODO\|FIXME" core/templates/ core/static/ tests/frontend/ 2>/dev/null | wc -l)
    if [ "$TODO_COUNT" -eq 0 ]; then
        print_status "PASS" "No TODO/FIXME comments found"
    else
        print_status "WARN" "Found $TODO_COUNT TODO/FIXME comments"
        grep -r "TODO\|FIXME" core/templates/ core/static/ tests/frontend/ 2>/dev/null | head -5
    fi
    
    # Check for console.log statements in production code
    echo "Checking for console.log statements..."
    CONSOLE_COUNT=$(grep -r "console\.log" core/templates/ core/static/ 2>/dev/null | wc -l)
    if [ "$CONSOLE_COUNT" -eq 0 ]; then
        print_status "PASS" "No console.log statements found"
    else
        print_status "WARN" "Found $CONSOLE_COUNT console.log statements"
        grep -r "console\.log" core/templates/ core/static/ 2>/dev/null | head -5
    fi
    
    # Check file sizes
    echo "Checking file sizes..."
    LARGE_FILES=$(find core/static/ -name "*.js" -o -name "*.css" | xargs ls -lh | awk '$5 ~ /[0-9]+M/ {print $9 " (" $5 ")"}')
    if [ -z "$LARGE_FILES" ]; then
        print_status "PASS" "No large static files found"
    else
        print_status "WARN" "Large static files found:"
        echo "$LARGE_FILES"
    fi
}

# Function to generate report
generate_report() {
    echo -e "${BLUE}Generating quality report...${NC}"
    
    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"
    
    # Run comprehensive test suite
    if python3 tests/frontend/run_frontend_tests.py > /tmp/comprehensive_test.log 2>&1; then
        print_status "PASS" "Comprehensive tests passed"
        
        # Extract summary from log
        echo "Test Summary:"
        grep -A 10 "FRONTEND TESTING SUMMARY" /tmp/comprehensive_test.log || echo "Summary not found"
        
    else
        print_status "FAIL" "Comprehensive tests failed"
        echo "Comprehensive test log:"
        tail -30 /tmp/comprehensive_test.log
        return 1
    fi
}

# Function to cleanup
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo "Stopping web server..."
        kill $SERVER_PID 2>/dev/null || true
    fi
    
    # Clean up temporary files
    rm -f /tmp/gui_test.log /tmp/websocket_test.log /tmp/performance_test.log /tmp/comprehensive_test.log
}

# Main execution
main() {
    local exit_code=0
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check prerequisites
    if ! command -v python3 &> /dev/null; then
        print_status "FAIL" "Python3 is not installed"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        print_status "FAIL" "curl is not installed"
        exit 1
    fi
    
    # Run quality checks
    if ! check_web_server; then
        exit_code=1
    fi
    
    if ! run_quick_tests; then
        exit_code=1
    fi
    
    if ! run_performance_tests; then
        exit_code=1
    fi
    
    check_code_quality  # This is informational, doesn't fail the gate
    
    if ! generate_report; then
        exit_code=1
    fi
    
    # Final result
    echo ""
    echo "=================================="
    if [ $exit_code -eq 0 ]; then
        print_status "PASS" "Frontend Quality Gate: ALL CHECKS PASSED"
        echo -e "${GREEN}🎉 Your frontend changes are ready for commit!${NC}"
    else
        print_status "FAIL" "Frontend Quality Gate: SOME CHECKS FAILED"
        echo -e "${RED}🔧 Please fix the issues above before committing.${NC}"
    fi
    
    exit $exit_code
}

# Run main function
main "$@" 