#!/usr/bin/env python3
"""Test script for Cablecast HTTP Basic Authentication.

This script tests the connection to the Cablecast API using HTTP Basic Authentication
and verifies that the credentials are working properly.

Usage:
    python scripts/test_cablecast_auth.py
"""

import os
import sys
import base64
import requests
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import (
    CABLECAST_SERVER_URL, CABLECAST_USER_ID, CABLECAST_PASSWORD,
    REQUEST_TIMEOUT
)
from core.cablecast_client import CablecastAPIClient
from loguru import logger

def test_basic_auth_manual():
    """Test HTTP Basic Authentication manually using requests."""
    print("🔐 Testing HTTP Basic Authentication manually...")
    
    if not CABLECAST_USER_ID or not CABLECAST_PASSWORD:
        print("❌ Error: CABLECAST_USER_ID and CABLECAST_PASSWORD must be set")
        return False
    
    # Create Basic Auth header
    credentials = f"{CABLECAST_USER_ID}:{CABLECAST_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Test endpoint - try to get shows
    test_url = f"{CABLECAST_SERVER_URL}/api/v1/shows"
    
    try:
        print(f"🌐 Testing connection to: {test_url}")
        print(f"👤 Username: {CABLECAST_USER_ID}")
        print(f"🔑 Password: {'*' * len(CABLECAST_PASSWORD)}")
        
        response = requests.get(
            test_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Authentication successful!")
            data = response.json()
            shows_count = len(data.get('shows', []))
            print(f"📺 Found {shows_count} shows")
            return True
        elif response.status_code == 401:
            print("❌ Authentication failed - check username and password")
            print(f"📄 Response: {response.text}")
            return False
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_cablecast_client():
    """Test the CablecastAPIClient class."""
    print("\n🔧 Testing CablecastAPIClient class...")
    
    try:
        client = CablecastAPIClient()
        
        # Test connection
        if client.test_connection():
            print("✅ CablecastAPIClient connection successful!")
            
            # Test getting shows
            shows = client.get_shows(limit=5)
            print(f"📺 Retrieved {len(shows)} shows")
            
            # Test getting VODs
            vods = client.get_vods(limit=5)
            print(f"🎬 Retrieved {len(vods)} VODs")
            
            # Test getting locations
            locations = client.get_locations()
            print(f"📍 Retrieved {len(locations)} locations")
            
            return True
        else:
            print("❌ CablecastAPIClient connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CablecastAPIClient: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Cablecast HTTP Basic Authentication Test")
    print("=" * 50)
    
    # Check environment variables
    print("🔍 Checking environment variables...")
    print(f"🌐 Server URL: {CABLECAST_SERVER_URL}")
    print(f"👤 User ID: {CABLECAST_USER_ID or 'NOT SET'}")
    print(f"🔑 Password: {'SET' if CABLECAST_PASSWORD else 'NOT SET'}")
    print()
    
    # Test manual authentication
    manual_success = test_basic_auth_manual()
    
    # Test client class
    client_success = test_cablecast_client()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"🔐 Manual Auth: {'✅ PASS' if manual_success else '❌ FAIL'}")
    print(f"🔧 Client Class: {'✅ PASS' if client_success else '❌ FAIL'}")
    
    if manual_success and client_success:
        print("\n🎉 All tests passed! HTTP Basic Authentication is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check your credentials and server URL.")
        return 1

if __name__ == "__main__":
    exit(main()) 