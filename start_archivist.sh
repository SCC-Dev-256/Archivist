#!/bin/bash

# Unified Archivist System Startup Script
# This script provides backward compatibility while using the new unified startup system

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

show_help() {
    echo "Unified Archivist System Startup"
    echo "================================"
    echo ""
    echo "Usage: $0 [mode] [options]"
    echo ""
    echo "Modes:"
    echo "  complete     - Full system with all features (default)"
    echo "  simple       - Basic system with alternative ports"
    echo "  integrated   - Integrated dashboard mode"
    echo "  vod-only     - VOD processing only"
    echo "  centralized  - Centralized service management"
    echo ""
    echo "Options:"
    echo "  --ports admin=8080,dashboard=5051  - Custom port configuration"
    echo "  --concurrency 4                    - Celery worker concurrency"
    echo "  --log-level INFO                   - Logging level"
    echo "  --config-file config.json          - Load configuration from file"
    echo "  --dry-run                          - Show what would be started"
    echo "  --status                           - Show system status"
    echo "  --help                             - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 complete"
    echo "  $0 simple --ports admin=5052,dashboard=5053"
    echo "  $0 vod-only --concurrency 2"
    echo "  $0 --config-file production.json"
    echo ""
    echo "Legacy compatibility:"
    echo "  $0                    - Same as: $0 complete"
    echo "  $0 --simple           - Same as: $0 simple"
    echo "  $0 --integrated       - Same as: $0 integrated"
    echo "  $0 --vod-only         - Same as: $0 vod-only"
}

# Parse arguments and convert legacy options
parse_args() {
    local mode="complete"
    local args=()
    
    # Handle case where no arguments are passed
    if [[ $# -eq 0 ]]; then
        echo "complete"
        return 0
    fi
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --simple)
                mode="simple"
                shift
                ;;
            --integrated)
                mode="integrated"
                shift
                ;;
            --vod-only)
                mode="vod-only"
                shift
                ;;
            --centralized)
                mode="centralized"
                shift
                ;;
            complete|simple|integrated|vod-only|centralized)
                mode="$1"
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    # Build the Python command
    local python_args=("$mode")
    python_args+=("${args[@]}")
    
    # Convert array to space-separated string
    printf "%s " "${python_args[@]}"
}

# Check if Python script exists
check_python_script() {
    if [[ ! -f "start_archivist_unified.py" ]]; then
        print_status "$RED" "❌ Error: start_archivist_unified.py not found"
        print_status "$YELLOW" "💡 Make sure you're running this from the project root directory"
        exit 1
    fi
}

# Check Python environment
check_python_env() {
    if ! command -v python3 >/dev/null 2>&1; then
        print_status "$RED" "❌ Error: python3 not found"
        print_status "$YELLOW" "💡 Please install Python 3.8 or higher"
        exit 1
    fi
    
    # Check if required modules are available
    if ! python3 -c "import loguru, psutil" 2>/dev/null; then
        print_status "$YELLOW" "⚠️  Warning: Some required Python modules may not be installed"
        print_status "$YELLOW" "💡 Run: pip install -r requirements.txt"
    fi
}

# Main function
main() {
    print_status "$BLUE" "🚀 Unified Archivist System Startup"
    echo ""
    
    # Check prerequisites
    check_python_script
    check_python_env
    
    # Parse arguments
    local python_args
    python_args=$(parse_args "$@")
    
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
    
    # Run the Python script
    print_status "$BLUE" "📋 Starting with arguments: $python_args"
    echo ""
    
    # Use eval to properly handle the arguments
    eval "python3 start_archivist_unified.py $python_args"
}

# Run main function with all arguments
main "$@" 