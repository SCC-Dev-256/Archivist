#!/bin/bash
# Frontend Testing Setup Script
# PURPOSE: Install dependencies and prepare environment for frontend testing
# DEPENDENCIES: Python 3.8+, pip, Chrome/Chromium
# MODIFICATION NOTES: v1.0 - Initial frontend testing setup script

set -e  # Exit on any error

echo "=========================================="
echo "Frontend Testing Environment Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8.0"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_success "Python $python_version is compatible"
else
    print_error "Python $python_version is too old. Required: $required_version or higher"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv_py311" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv_py311
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv_py311/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install frontend testing dependencies
print_status "Installing frontend testing dependencies..."
pip install -r requirements-frontend-test.txt

# Check if Chrome/Chromium is installed
print_status "Checking for Chrome/Chromium installation..."

# Check for Chrome
if command -v google-chrome &> /dev/null; then
    print_success "Google Chrome is installed"
    CHROME_AVAILABLE=true
elif command -v chromium-browser &> /dev/null; then
    print_success "Chromium is installed"
    CHROME_AVAILABLE=true
elif command -v chromium &> /dev/null; then
    print_success "Chromium is installed"
    CHROME_AVAILABLE=true
else
    print_warning "Chrome/Chromium not found. Installing Chrome..."
    
    # Detect OS and install Chrome
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
            sudo apt-get update
            sudo apt-get install -y google-chrome-stable
        elif command -v yum &> /dev/null; then
            # CentOS/RHEL
            sudo yum install -y google-chrome-stable
        else
            print_error "Unsupported Linux distribution. Please install Chrome manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_error "Please install Chrome manually on macOS using Homebrew: brew install --cask google-chrome"
        exit 1
    else
        print_error "Unsupported operating system. Please install Chrome manually."
        exit 1
    fi
fi

# Install ChromeDriver using webdriver-manager
print_status "Setting up ChromeDriver..."
python3 -c "
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Download and setup ChromeDriver
driver_path = ChromeDriverManager().install()
print(f'ChromeDriver installed at: {driver_path}')

# Test ChromeDriver
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

try:
    driver = webdriver.Chrome(options=options)
    driver.quit()
    print('ChromeDriver test successful')
except Exception as e:
    print(f'ChromeDriver test failed: {e}')
    exit(1)
"

# Create test directories
print_status "Creating test directories..."
mkdir -p tests/frontend/reports
mkdir -p tests/frontend/screenshots
mkdir -p tests/frontend/logs

# Set up environment variables for testing
print_status "Setting up environment variables..."
export FLASK_ENV=testing
export TESTING=true
export SELENIUM_HEADLESS=true

# Create a test configuration file
cat > tests/frontend/test_config.py << 'EOF'
# Frontend Testing Configuration
# PURPOSE: Configuration settings for frontend testing
# DEPENDENCIES: Environment variables and test settings
# MODIFICATION NOTES: v1.0 - Initial test configuration

import os

# Test Configuration
TEST_CONFIG = {
    'base_url': os.getenv('TEST_BASE_URL', 'http://localhost:5050'),
    'headless': os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true',
    'timeout': int(os.getenv('SELENIUM_TIMEOUT', '10')),
    'implicit_wait': int(os.getenv('SELENIUM_IMPLICIT_WAIT', '5')),
    'window_size': os.getenv('SELENIUM_WINDOW_SIZE', '1920,1080'),
    'screenshot_dir': 'tests/frontend/screenshots',
    'report_dir': 'tests/frontend/reports',
    'log_dir': 'tests/frontend/logs'
}

# WebSocket Configuration
WEBSOCKET_CONFIG = {
    'connection_timeout': int(os.getenv('WEBSOCKET_TIMEOUT', '5')),
    'reconnection_attempts': int(os.getenv('WEBSOCKET_RECONNECT_ATTEMPTS', '3')),
    'message_timeout': int(os.getenv('WEBSOCKET_MESSAGE_TIMEOUT', '10'))
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    'load_time_threshold': float(os.getenv('LOAD_TIME_THRESHOLD', '3.0')),
    'max_load_time_threshold': float(os.getenv('MAX_LOAD_TIME_THRESHOLD', '5.0')),
    'concurrent_users': int(os.getenv('CONCURRENT_USERS', '10'))
}

# Accessibility Configuration
ACCESSIBILITY_CONFIG = {
    'wcag_level': os.getenv('WCAG_LEVEL', 'AA'),
    'check_images': os.getenv('CHECK_IMAGES', 'true').lower() == 'true',
    'check_forms': os.getenv('CHECK_FORMS', 'true').lower() == 'true',
    'check_semantics': os.getenv('CHECK_SEMANTICS', 'true').lower() == 'true'
}
EOF

print_success "Test configuration created"

# Create a simple test runner script
cat > run_frontend_tests.sh << 'EOF'
#!/bin/bash
# Frontend Test Runner Script
# PURPOSE: Run comprehensive frontend tests
# DEPENDENCIES: Python virtual environment, test modules
# MODIFICATION NOTES: v1.0 - Initial test runner script

set -e

echo "=========================================="
echo "Running Frontend Tests"
echo "=========================================="

# Activate virtual environment
source venv_py311/bin/activate

# Set environment variables
export FLASK_ENV=testing
export TESTING=true
export SELENIUM_HEADLESS=true

# Run the comprehensive frontend test suite
python3 tests/frontend/run_frontend_tests.py

echo "=========================================="
echo "Frontend Tests Complete"
echo "=========================================="
EOF

chmod +x run_frontend_tests.sh

# Create a quick test script
cat > quick_frontend_test.sh << 'EOF'
#!/bin/bash
# Quick Frontend Test Script
# PURPOSE: Run basic frontend tests quickly
# DEPENDENCIES: Python virtual environment
# MODIFICATION NOTES: v1.0 - Initial quick test script

set -e

echo "=========================================="
echo "Running Quick Frontend Tests"
echo "=========================================="

# Activate virtual environment
source venv_py311/bin/activate

# Set environment variables
export FLASK_ENV=testing
export TESTING=true
export SELENIUM_HEADLESS=true

# Run basic tests
echo "Testing WebSocket functionality..."
python3 tests/frontend/test_websocket_functionality.py

echo "Testing basic GUI functionality..."
python3 tests/frontend/test_frontend_gui.py

echo "=========================================="
echo "Quick Frontend Tests Complete"
echo "=========================================="
EOF

chmod +x quick_frontend_test.sh

print_success "Frontend testing environment setup complete!"

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Start your web server: python3 test_web_ui.py"
echo "2. Run quick tests: ./quick_frontend_test.sh"
echo "3. Run full test suite: ./run_frontend_tests.sh"
echo "4. View test reports in: tests/frontend/reports/"
echo "5. View screenshots in: tests/frontend/screenshots/"
echo ""

print_success "Frontend testing environment is ready!"

# NEXT STEP: Start the web server and run the frontend tests 