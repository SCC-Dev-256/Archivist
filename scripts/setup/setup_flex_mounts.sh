#!/bin/bash

# Flex Mount Setup Script
# This script sets up CIFS mounts for flex servers with proper permissions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Flex Server CIFS mounts...${NC}"

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    # Source only the specific variables we need, avoiding comments and special characters
    FLEX_USERNAME=$(grep '^FLEX_USERNAME=' .env | cut -d'=' -f2)
    FLEX_PASSWORD=$(grep '^FLEX_PASSWORD=' .env | cut -d'=' -f2)
    
    if [ -z "$FLEX_USERNAME" ] || [ -z "$FLEX_PASSWORD" ]; then
        echo -e "${RED}Error: FLEX_USERNAME or FLEX_PASSWORD not found in .env file${NC}"
        exit 1
    fi
    
    echo "Found credentials: username=$FLEX_USERNAME, password=[HIDDEN]"
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Create credentials file with actual values
echo "Creating CIFS credentials file..."
sudo tee /etc/flex-credentials > /dev/null << EOF
# CIFS Credentials for Flex Servers
username=${FLEX_USERNAME}
password=${FLEX_PASSWORD}
domain=
EOF

# Set proper permissions on credentials file
sudo chmod 600 /etc/flex-credentials
sudo chown root:root /etc/flex-credentials

echo -e "${GREEN}Credentials file created at /etc/flex-credentials${NC}"

# Get user and group IDs
USER_ID=1000  # schum user ID
GROUP_ID=1001  # archivist_users group ID

echo "User ID: $USER_ID (schum)"
echo "Group ID: $GROUP_ID (archivist_users)"

# Create mount directories if they don't exist
echo "Creating mount directories..."
for i in {1..9}; do
    sudo mkdir -p /mnt/flex-$i
done

# Unmount existing mounts
echo "Unmounting existing flex mounts..."
for i in {1..9}; do
    if mountpoint -q /mnt/flex-$i; then
        sudo umount /mnt/flex-$i
    fi
done

# Mount commands for each flex server
echo "Mounting flex servers with proper permissions..."

# Flex 1 - 192.168.181.56
sudo mount -t cifs //192.168.181.56/contentdrive /mnt/flex-1 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 2 - 192.168.181.57
sudo mount -t cifs //192.168.181.57/contentdrive /mnt/flex-2 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 3 - 192.168.181.58
sudo mount -t cifs //192.168.181.58/contentdrive /mnt/flex-3 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 4 - 192.168.181.59
sudo mount -t cifs //192.168.181.59/contentdrive /mnt/flex-4 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 5 - 192.168.181.60
sudo mount -t cifs //192.168.181.60/contentdrive /mnt/flex-5 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 6 - 192.168.181.61
sudo mount -t cifs //192.168.181.61/contentdrive /mnt/flex-6 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 7 - 192.168.181.62
sudo mount -t cifs //192.168.181.62/contentdrive /mnt/flex-7 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 8 - 192.168.181.63
sudo mount -t cifs //192.168.181.63/contentdrive /mnt/flex-8 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

# Flex 9 - 192.168.181.64
sudo mount -t cifs //192.168.181.64/contentdrive /mnt/flex-9 \
    -o credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0

echo -e "${GREEN}All flex mounts completed!${NC}"

# Verify mounts
echo "Verifying mounts..."
mount | grep flex

# Test write access
echo "Testing write access..."
for i in {1..9}; do
    if mountpoint -q /mnt/flex-$i; then
        if touch /mnt/flex-$i/test_write_$(date +%s) 2>/dev/null; then
            echo -e "${GREEN}✓ /mnt/flex-$i: Write access OK${NC}"
            rm -f /mnt/flex-$i/test_write_*
        else
            echo -e "${RED}✗ /mnt/flex-$i: Write access FAILED${NC}"
        fi
    else
        echo -e "${RED}✗ /mnt/flex-$i: Not mounted${NC}"
    fi
done

echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo -e "${YELLOW}To make these mounts permanent, add the following lines to /etc/fstab:${NC}"
echo ""
echo "# Flex Server CIFS Mounts"
echo "//192.168.181.56/contentdrive /mnt/flex-1 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.57/contentdrive /mnt/flex-2 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.58/contentdrive /mnt/flex-3 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.59/contentdrive /mnt/flex-4 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.60/contentdrive /mnt/flex-5 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.61/contentdrive /mnt/flex-6 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.62/contentdrive /mnt/flex-7 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.63/contentdrive /mnt/flex-8 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0"
echo "//192.168.181.64/contentdrive /mnt/flex-9 cifs credentials=/etc/flex-credentials,uid=$USER_ID,gid=$GROUP_ID,file_mode=0664,dir_mode=0775,vers=3.0,_netdev 0 0" 