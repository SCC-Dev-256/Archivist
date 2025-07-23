#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log directories
LOG_DIR="/opt/Archivist/logs"
TRANSCRIPTION_DIR="$LOG_DIR/transcription"
MEMORY_DIR="$LOG_DIR/memory"
SYSTEM_DIR="$LOG_DIR/system"

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to print error messages
print_error() {
    echo -e "${RED}Error: $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}Success: $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}Warning: $1${NC}"
}

# Function to get latest log file
get_latest_log() {
    local dir=$1
    local pattern=$2
    find "$dir" -name "$pattern" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" "
}

# Function to display transcription logs
show_transcription_logs() {
    print_section "Transcription Logs"
    
    # Get latest transcription log
    latest_log=$(get_latest_log "$TRANSCRIPTION_DIR" "transcription_*.log")
    if [ -n "$latest_log" ]; then
        echo "Latest transcription log: $latest_log"
        echo "Last 20 lines:"
        tail -n 20 "$latest_log"
    else
        print_warning "No transcription logs found"
    fi
    
    # Get latest debug JSON
    latest_json=$(get_latest_log "$TRANSCRIPTION_DIR" "debug_*.json")
    if [ -n "$latest_json" ]; then
        echo -e "\nLatest debug JSON: $latest_json"
        echo "Content:"
        jq '.' "$latest_json" 2>/dev/null || cat "$latest_json"
    else
        print_warning "No debug JSON files found"
    fi
}

# Function to display memory logs
show_memory_logs() {
    print_section "Memory Usage Logs"
    
    latest_memory_log=$(get_latest_log "$MEMORY_DIR" "memory_*.log")
    if [ -n "$latest_memory_log" ]; then
        echo "Latest memory log: $latest_memory_log"
        echo "Last 10 entries:"
        tail -n 50 "$latest_memory_log"
    else
        print_warning "No memory logs found"
    fi
}

# Function to display system logs
show_system_logs() {
    print_section "System Resource Logs"
    
    latest_system_log=$(get_latest_log "$SYSTEM_DIR" "system_*.log")
    if [ -n "$latest_system_log" ]; then
        echo "Latest system log: $latest_system_log"
        echo "Last 10 entries:"
        tail -n 50 "$latest_system_log"
    else
        print_warning "No system logs found"
    fi
}

# Function to show current system status
show_current_status() {
    print_section "Current System Status"
    
    echo "Memory Usage:"
    free -h
    
    echo -e "\nDisk Usage:"
    df -h
    
    echo -e "\nTop Memory Processes:"
    ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -n 10
    
    echo -e "\nPython Processes:"
    ps aux | grep python | grep -v grep
}

# Function to show log file sizes
show_log_sizes() {
    print_section "Log File Sizes"
    
    echo "Transcription Logs:"
    du -sh "$TRANSCRIPTION_DIR"/* 2>/dev/null || echo "No transcription logs"
    
    echo -e "\nMemory Logs:"
    du -sh "$MEMORY_DIR"/* 2>/dev/null || echo "No memory logs"
    
    echo -e "\nSystem Logs:"
    du -sh "$SYSTEM_DIR"/* 2>/dev/null || echo "No system logs"
}

# Main execution
echo -e "${BLUE}=== Archivist Debug Log Viewer ===${NC}"
echo "Current time: $(date)"
echo "Log directory: $LOG_DIR"

# Check if log directories exist
for dir in "$TRANSCRIPTION_DIR" "$MEMORY_DIR" "$SYSTEM_DIR"; do
    if [ ! -d "$dir" ]; then
        print_warning "Directory not found: $dir"
    fi
done

# Show all logs
show_transcription_logs
show_memory_logs
show_system_logs
show_current_status
show_log_sizes

print_section "End of Log Report"
echo "Report generated at: $(date)" 