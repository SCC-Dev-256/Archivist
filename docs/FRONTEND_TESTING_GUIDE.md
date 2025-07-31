# Frontend Testing Guide

## Overview

This guide covers the comprehensive frontend testing suite for the Archivist application. The testing suite includes GUI testing, WebSocket functionality testing, performance testing, accessibility testing, and integration testing.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Categories](#test-categories)
3. [Setup Instructions](#setup-instructions)
4. [Running Tests](#running-tests)
5. [Test Reports](#test-reports)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)
8. [CI/CD Integration](#cicd-integration)

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Chrome or Chromium browser
- Virtual environment (recommended)
- Web server running on localhost:5050

### One-Command Setup

```bash
# Run the setup script
chmod +x setup_frontend_testing.sh
./setup_frontend_testing.sh
```

### Quick Test Run

```bash
# Start the web server (in one terminal)
python3 test_web_ui.py

# Run quick tests (in another terminal)
./quick_frontend_test.sh
```

## Test Categories

### 1. GUI Testing (`test_frontend_gui.py`)

**Purpose**: Test user interface rendering, navigation, and interactions

**Coverage**:
- UI rendering and layout
- Navigation and tab functionality
- File browser interface
- Analytics dashboard
- Real-time tasks interface
- Controls interface
- Live metrics display
- Flex servers panel
- Responsive design
- Accessibility features
- Error handling and feedback

**Key Features**:
- Selenium WebDriver automation
- Cross-browser compatibility testing
- Responsive design validation
- Visual element verification

### 2. WebSocket Testing (`test_websocket_functionality.py`)

**Purpose**: Test real-time communication and live updates

**Coverage**:
- Socket.IO connection management
- Real-time system metrics updates
- Task progress updates
- Queue status updates
- Error handling and reconnection
- Message broadcasting
- Client-server communication
- Performance and latency testing
- Concurrent connections

**Key Features**:
- Socket.IO client testing
- Real-time data validation
- Connection reliability testing
- Performance benchmarking

### 3. Integration Testing

**Purpose**: Test frontend-backend integration

**Coverage**:
- Admin dashboard rendering
- API endpoint integration
- Real-time updates integration
- UI interactions and form validation
- Dashboard API integration
- Task management and control
- System status and monitoring
- Error handling and edge cases

### 4. Performance Testing

**Purpose**: Validate application performance

**Coverage**:
- Page load times
- Response latency
- Concurrent user handling
- Resource usage monitoring

### 5. Accessibility Testing

**Purpose**: Ensure application accessibility

**Coverage**:
- WCAG compliance
- Semantic HTML structure
- Alt text for images
- Form labels and accessibility
- Keyboard navigation
- Screen reader compatibility

## Setup Instructions

### Step 1: Environment Setup

```bash
# Create virtual environment
python3 -m venv venv_py311
source venv_py311/bin/activate

# Install dependencies
pip install -r requirements-frontend-test.txt
```

### Step 2: Browser Setup

The setup script will automatically detect and configure Chrome/Chromium. If manual setup is needed:

```bash
# Install Chrome (Ubuntu/Debian)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt-get update
sudo apt-get install -y google-chrome-stable

# Install ChromeDriver
python3 -c "
from webdriver_manager.chrome import ChromeDriverManager
ChromeDriverManager().install()
"
```

### Step 3: Configuration

The test configuration is automatically created in `tests/frontend/test_config.py`. Key settings:

```python
TEST_CONFIG = {
    'base_url': 'http://localhost:5050',
    'headless': True,
    'timeout': 10,
    'window_size': '1920,1080'
}
```

## Running Tests

### Quick Tests

```bash
# Run basic functionality tests
./quick_frontend_test.sh
```

### Full Test Suite

```bash
# Run comprehensive test suite
./run_frontend_tests.sh
```

### Individual Test Modules

```bash
# Run GUI tests only
python3 tests/frontend/test_frontend_gui.py

# Run WebSocket tests only
python3 tests/frontend/test_websocket_functionality.py

# Run comprehensive test runner
python3 tests/frontend/run_frontend_tests.py
```

### Pytest Integration

```bash
# Run with pytest
pytest tests/frontend/ -v

# Run with coverage
pytest tests/frontend/ --cov=frontend --cov-report=html
```

## Test Reports

### Report Locations

- **JSON Reports**: `frontend_test_report_YYYYMMDD_HHMMSS.json`
- **HTML Reports**: `tests/frontend/reports/`
- **Screenshots**: `tests/frontend/screenshots/`
- **Logs**: `tests/frontend/logs/`

### Report Structure

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "duration": 45.2,
  "overall_success": true,
  "summary": {
    "total_suites": 5,
    "passed_suites": 5,
    "failed_suites": 0,
    "success_rate": 100.0
  },
  "test_suites": {
    "GUI Testing": {
      "success": true,
      "message": "GUI Testing: 11/11 tests passed",
      "details": {...}
    }
  },
  "recommendations": [...]
}
```

### Reading Reports

1. **Overall Status**: Check `overall_success` field
2. **Test Suite Results**: Review individual suite results
3. **Performance Metrics**: Check load times and latency
4. **Recommendations**: Follow suggested improvements

## Troubleshooting

### Common Issues

#### 1. Chrome/ChromeDriver Issues

**Problem**: ChromeDriver not found or incompatible
```bash
# Solution: Reinstall ChromeDriver
python3 -c "
from webdriver_manager.chrome import ChromeDriverManager
ChromeDriverManager().install()
"
```

#### 2. WebSocket Connection Issues

**Problem**: WebSocket tests failing
```bash
# Check if server is running
curl http://localhost:5050

# Check Socket.IO endpoint
curl http://localhost:5050/socket.io/
```

#### 3. Selenium Timeout Issues

**Problem**: Tests timing out
```python
# Increase timeout in test_config.py
TEST_CONFIG['timeout'] = 20
```

#### 4. Missing Dependencies

**Problem**: Import errors
```bash
# Reinstall dependencies
pip install -r requirements-frontend-test.txt --force-reinstall
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python3 tests/frontend/run_frontend_tests.py
```

### Headless Mode Issues

If tests fail in headless mode:

```bash
# Run with visible browser
export SELENIUM_HEADLESS=false
python3 tests/frontend/test_frontend_gui.py
```

## Advanced Configuration

### Environment Variables

```bash
# Test configuration
export TEST_BASE_URL=http://localhost:5050
export SELENIUM_HEADLESS=true
export SELENIUM_TIMEOUT=10
export SELENIUM_IMPLICIT_WAIT=5

# WebSocket configuration
export WEBSOCKET_TIMEOUT=5
export WEBSOCKET_RECONNECT_ATTEMPTS=3
export WEBSOCKET_MESSAGE_TIMEOUT=10

# Performance configuration
export LOAD_TIME_THRESHOLD=3.0
export MAX_LOAD_TIME_THRESHOLD=5.0
export CONCURRENT_USERS=10

# Accessibility configuration
export WCAG_LEVEL=AA
export CHECK_IMAGES=true
export CHECK_FORMS=true
export CHECK_SEMANTICS=true
```

### Custom Test Configuration

Create custom test configuration:

```python
# tests/frontend/custom_config.py
CUSTOM_CONFIG = {
    'base_url': 'http://staging.example.com',
    'headless': False,
    'screenshot_on_failure': True,
    'video_recording': True
}
```

### Parallel Testing

Run tests in parallel:

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run parallel tests
pytest tests/frontend/ -n 4
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests

on: [push, pull_request]

jobs:
  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install Chrome
      run: |
        sudo apt-get update
        sudo apt-get install -y google-chrome-stable
    
    - name: Install dependencies
      run: |
        pip install -r requirements-frontend-test.txt
    
    - name: Start web server
      run: |
        python3 test_web_ui.py &
        sleep 10
    
    - name: Run frontend tests
      run: |
        python3 tests/frontend/run_frontend_tests.py
    
    - name: Upload test results
      uses: actions/upload-artifact@v2
      with:
        name: frontend-test-results
        path: frontend_test_report_*.json
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install -r requirements-frontend-test.txt'
            }
        }
        
        stage('Start Server') {
            steps {
                sh 'python3 test_web_ui.py &'
                sh 'sleep 10'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'python3 tests/frontend/run_frontend_tests.py'
            }
        }
        
        stage('Publish Results') {
            steps {
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'tests/frontend/reports',
                    reportFiles: 'index.html',
                    reportName: 'Frontend Test Report'
                ])
            }
        }
    }
}
```

## Best Practices

### 1. Test Organization

- Keep tests focused and atomic
- Use descriptive test names
- Group related tests together
- Maintain test independence

### 2. Test Data Management

- Use fixtures for test data
- Clean up after tests
- Avoid hardcoded test data
- Use environment-specific configurations

### 3. Error Handling

- Test both success and failure scenarios
- Validate error messages
- Test edge cases
- Handle timeouts gracefully

### 4. Performance Considerations

- Run tests in parallel when possible
- Use headless mode for CI/CD
- Optimize test execution time
- Monitor resource usage

### 5. Maintenance

- Update tests when UI changes
- Keep dependencies current
- Monitor test flakiness
- Regular test review and cleanup

## Support and Contributing

### Getting Help

1. Check the troubleshooting section
2. Review test logs in `tests/frontend/logs/`
3. Enable debug mode for detailed output
4. Check GitHub issues for known problems

### Contributing

1. Follow the existing test structure
2. Add comprehensive documentation
3. Include both positive and negative test cases
4. Ensure tests are reliable and maintainable

### Reporting Issues

When reporting issues, include:

- Test configuration
- Error logs
- Screenshots (if applicable)
- Steps to reproduce
- Environment details

---

**Next Steps**: Start with the quick setup and run basic tests to validate your environment, then proceed to comprehensive testing based on your needs.

# NEXT STEP: Run the setup script and begin frontend testing 