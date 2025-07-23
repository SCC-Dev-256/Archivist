#!/bin/bash

# Create CIFS Credentials File from Environment Variables
# This script reads the FLEX_USERNAME and FLEX_PASSWORD from .env and creates the credentials file

set -e

echo "Creating CIFS credentials file from environment variables..."

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    # Source only the specific variables we need, avoiding comments and special characters
    FLEX_USERNAME=$(grep '^FLEX_USERNAME=' .env | cut -d'=' -f2)
    FLEX_PASSWORD=$(grep '^FLEX_PASSWORD=' .env | cut -d'=' -f2)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if credentials are available
if [ -z "$FLEX_USERNAME" ] || [ -z "$FLEX_PASSWORD" ]; then
    echo "Error: FLEX_USERNAME or FLEX_PASSWORD not found in .env file"
    exit 1
fi

echo "Username: $FLEX_USERNAME"
echo "Password: [HIDDEN]"

# Create credentials file
sudo tee /etc/flex-credentials > /dev/null << EOF
# CIFS Credentials for Flex Servers
username=$FLEX_USERNAME
password=$FLEX_PASSWORD
domain=
EOF

# Set proper permissions
sudo chmod 600 /etc/flex-credentials
sudo chown root:root /etc/flex-credentials

echo "Credentials file created at /etc/flex-credentials"
echo "Permissions set to 600 (root:root)"

# Verify the file was created
if [ -f /etc/flex-credentials ]; then
    echo "✓ Credentials file created successfully"
    echo "File permissions: $(ls -la /etc/flex-credentials)"
else
    echo "✗ Failed to create credentials file"
    exit 1
fi 