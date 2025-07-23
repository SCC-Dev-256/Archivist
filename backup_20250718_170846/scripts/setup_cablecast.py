#!/usr/bin/env python3
"""Interactive setup script for Cablecast configuration.

This script helps you configure the Cablecast environment variables
by prompting for the necessary credentials and creating/updating the .env file.

Usage:
    python scripts/setup_cablecast.py
"""

import os
import sys
from pathlib import Path

def get_input(prompt, default="", password=False):
    """Get user input with optional default value."""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    if password:
        import getpass
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    
    return value if value else default

def update_env_file(env_path, updates):
    """Update .env file with new values."""
    # Read existing .env file
    env_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Create a set of keys to update
    update_keys = set(updates.keys())
    
    # Update existing lines
    updated_lines = []
    for line in env_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            updated_lines.append(line)
            continue
        
        if '=' in line:
            key = line.split('=')[0].strip()
            if key in update_keys:
                updated_lines.append(f"{key}={updates[key]}")
                update_keys.remove(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add new lines for remaining keys
    for key in update_keys:
        updated_lines.append(f"{key}={updates[key]}")
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.write('\n'.join(updated_lines) + '\n')

def main():
    """Main setup function."""
    print("🚀 Cablecast Configuration Setup")
    print("=" * 50)
    print()
    print("This script will help you configure Cablecast HTTP Basic Authentication.")
    print("You'll need your Cablecast username, password, and location ID.")
    print()
    
    # Check if .env file exists
    env_path = Path('.env')
    if not env_path.exists():
        print("⚠️  No .env file found. Creating one from .env.example...")
        example_path = Path('.env.example')
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            print("✅ Created .env file from .env.example")
        else:
            print("❌ No .env.example file found. Please create a .env file manually.")
            return 1
    
    # Get current values
    current_values = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    current_values[key.strip()] = value.strip()
    
    print("📝 Please provide your Cablecast credentials:")
    print()
    
    # Get Cablecast configuration
    updates = {}
    
    # Server URL
    current_url = current_values.get('CABLECAST_SERVER_URL', 'https://rays-house.cablecast.net')
    server_url = get_input("Cablecast Server URL", current_url)
    if server_url:
        updates['CABLECAST_SERVER_URL'] = server_url
    
    # Username
    current_username = current_values.get('CABLECAST_USER_ID', '')
    username = get_input("Cablecast Username", current_username)
    if username:
        updates['CABLECAST_USER_ID'] = username
    
    # Password
    current_password = current_values.get('CABLECAST_PASSWORD', '')
    password = get_input("Cablecast Password", current_password, password=True)
    if password:
        updates['CABLECAST_PASSWORD'] = password
    
    # Location ID
    current_location = current_values.get('CABLECAST_LOCATION_ID', '123456')
    location_id = get_input("Cablecast Location ID", current_location)
    if location_id:
        updates['CABLECAST_LOCATION_ID'] = location_id
    
    # API Key (optional)
    current_api_key = current_values.get('CABLECAST_API_KEY', 'your_api_key_here')
    api_key = get_input("Cablecast API Key (optional)", current_api_key)
    if api_key and api_key != 'your_api_key_here':
        updates['CABLECAST_API_KEY'] = api_key
    
    # Update .env file
    if updates:
        update_env_file(env_path, updates)
        print()
        print("✅ Updated .env file with Cablecast configuration")
        print()
        
        # Show summary
        print("📋 Configuration Summary:")
        print(f"   Server URL: {updates.get('CABLECAST_SERVER_URL', current_url)}")
        print(f"   Username: {updates.get('CABLECAST_USER_ID', current_username)}")
        print(f"   Password: {'*' * len(updates.get('CABLECAST_PASSWORD', current_password))}")
        print(f"   Location ID: {updates.get('CABLECAST_LOCATION_ID', current_location)}")
        if 'CABLECAST_API_KEY' in updates:
            print(f"   API Key: {'*' * len(updates['CABLECAST_API_KEY'])}")
        print()
        
        # Test connection
        print("🧪 Testing connection...")
        try:
            # Import after setting up environment
            from core.cablecast_client import CablecastAPIClient
            
            client = CablecastAPIClient()
            if client.test_connection():
                print("✅ Connection successful!")
                print()
                print("🎉 Cablecast configuration is complete!")
                print()
                print("Next steps:")
                print("1. Run the full test: python scripts/test_cablecast_auth.py")
                print("2. Start using the VOD integration in your application")
                print("3. Check the documentation: docs/CABLECAST_SETUP.md")
                return 0
            else:
                print("❌ Connection failed. Please check your credentials.")
                print()
                print("Troubleshooting:")
                print("1. Verify your username and password")
                print("2. Check that the server URL is correct")
                print("3. Ensure your user has API access permissions")
                print("4. Check network connectivity to the Cablecast server")
                return 1
                
        except Exception as e:
            print(f"❌ Error testing connection: {e}")
            print()
            print("Please check your configuration and try again.")
            return 1
    else:
        print("ℹ️  No changes made to configuration.")
        return 0

if __name__ == "__main__":
    exit(main()) 