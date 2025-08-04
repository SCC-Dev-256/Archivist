#!/bin/bash

# Fix Mount Permissions Script
# This script fixes permissions for flex mount directories

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

# Flex mount directories
FLEX_MOUNTS=(
    "/mnt/flex-1"
    "/mnt/flex-2"
    "/mnt/flex-3"
    "/mnt/flex-4"
    "/mnt/flex-5"
    "/mnt/flex-6"
    "/mnt/flex-7"
    "/mnt/flex-8"
)

print_status "$BLUE" "🔧 Fixing Mount Permissions"
echo "=================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_status "$YELLOW" "⚠️  Running as root - this is fine for fixing permissions"
else
    print_status "$YELLOW" "⚠️  Not running as root - some operations may fail"
    print_status "$YELLOW" "💡 Consider running with sudo if you encounter permission errors"
fi

echo ""

# Fix permissions for each mount
for mount in "${FLEX_MOUNTS[@]}"; do
    if [[ -d "$mount" ]]; then
        print_status "$BLUE" "🔧 Fixing permissions for $mount"
        
        # Check if it's actually a mount point
        if mountpoint -q "$mount"; then
            print_status "$GREEN" "✅ $mount is a valid mount point"
            
            # Fix ownership (try without sudo first)
            if chown -R $USER:$USER "$mount" 2>/dev/null; then
                print_status "$GREEN" "✅ Fixed ownership for $mount"
            else
                print_status "$YELLOW" "⚠️  Could not fix ownership for $mount (may need sudo)"
            fi
            
            # Fix permissions
            if chmod -R 755 "$mount" 2>/dev/null; then
                print_status "$GREEN" "✅ Fixed permissions for $mount"
            else
                print_status "$YELLOW" "⚠️  Could not fix permissions for $mount (may need sudo)"
            fi
            
            # Test write access
            test_file="$mount/.health_check_test"
            if touch "$test_file" 2>/dev/null; then
                rm -f "$test_file"
                print_status "$GREEN" "✅ Write access confirmed for $mount"
            else
                print_status "$RED" "❌ Write access failed for $mount"
            fi
            
        else
            print_status "$YELLOW" "⚠️  $mount exists but is not mounted"
        fi
    else
        print_status "$YELLOW" "⚠️  $mount does not exist"
    fi
    
    echo ""
done

# Create health check directories if they don't exist
print_status "$BLUE" "📁 Creating health check directories"
for mount in "${FLEX_MOUNTS[@]}"; do
    if [[ -d "$mount" ]]; then
        health_dir="$mount/.archivist_health"
        if [[ ! -d "$health_dir" ]]; then
            if mkdir -p "$health_dir" 2>/dev/null; then
                print_status "$GREEN" "✅ Created health check directory: $health_dir"
            else
                print_status "$YELLOW" "⚠️  Could not create health check directory: $health_dir"
            fi
        else
            print_status "$GREEN" "✅ Health check directory exists: $health_dir"
        fi
    fi
done

echo ""
print_status "$GREEN" "🎉 Mount permission fix completed!"
echo ""
print_status "$BLUE" "📋 Summary:"
print_status "$BLUE" "  - Checked ${#FLEX_MOUNTS[@]} flex mount directories"
print_status "$BLUE" "  - Fixed ownership and permissions where possible"
print_status "$BLUE" "  - Created health check directories"
print_status "$BLUE" "  - Tested write access"
echo ""
print_status "$YELLOW" "💡 If you still see permission errors, run this script with sudo:"
print_status "$YELLOW" "   sudo ./scripts/setup/fix_mount_permissions.sh" 