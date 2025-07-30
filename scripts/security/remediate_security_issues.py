#!/usr/bin/env python3
"""
Security Remediation Script for Archivist Application

This script helps remediate the critical security issues identified in the
security audit by backing up current credentials and providing guidance for
secure updates.

Usage:
    python scripts/security/remediate_security_issues.py

This script will:
1. Backup current .env file
2. Identify hardcoded credentials
3. Provide guidance for secure credential management
4. Help create secure environment variable configuration
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import re

def backup_env_file():
    """Backup the current .env file with timestamp."""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ No .env file found to backup")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f'.env.backup_{timestamp}')
    
    try:
        shutil.copy2(env_path, backup_path)
        print(f"✅ Backed up .env to {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Error backing up .env: {e}")
        return None

def identify_hardcoded_credentials():
    """Identify hardcoded credentials in the .env file."""
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ No .env file found")
        return []
    
    hardcoded_creds = []
    
    # Patterns to identify hardcoded credentials
    patterns = [
        (r'POSTGRES_PASSWORD=([^#\s]+)', 'Database Password'),
        (r'FLEX_PASSWORD=([^#\s]+)', 'Flex Server Password'),
        (r'CABLECAST_PASSWORD=([^#\s]+)', 'Cablecast Password'),
        (r'GRAFANA_PASSWORD=([^#\s]+)', 'Grafana Password'),
        (r'SECRET_KEY=([^#\s]+)', 'Flask Secret Key'),
        (r'CABLECAST_API_KEY=([^#\s]+)', 'Cablecast API Key'),
        (r'REDIS_PASSWORD=([^#\s]+)', 'Redis Password'),
    ]
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
            
        for pattern, cred_type in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match and match not in ['', 'your_', 'placeholder']:
                    hardcoded_creds.append({
                        'type': cred_type,
                        'value': match,
                        'pattern': pattern
                    })
    
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
    
    return hardcoded_creds

def create_secure_env_template():
    """Create a secure .env template with placeholders."""
    template_content = """# =============================================================================
# ARCHIVIST APPLICATION - SECURE ENVIRONMENT CONFIGURATION
# =============================================================================
# 
# IMPORTANT: Replace all placeholder values with secure credentials
# Never commit this file with actual credentials to version control
#
# =============================================================================

# Base paths
NAS_PATH=/mnt/nas
OUTPUT_DIR=/tmp/archivist-output

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${REDIS_PASSWORD}

# Database configuration
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=archivist
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/archivist

# API configuration
API_HOST=0.0.0.0
API_PORT=5050
API_WORKERS=4
API_RATE_LIMIT=100/minute

# Flask Configuration
FLASK_APP=core.app
FLASK_ENV=development
FLASK_DEBUG=0
SECRET_KEY=${SECRET_KEY}

# ML Model Configuration
WHISPER_MODEL=large-v2
USE_GPU=false
COMPUTE_TYPE=int8
BATCH_SIZE=16
NUM_WORKERS=4
LANGUAGE=en

# Storage Configuration
UPLOAD_FOLDER=/app/uploads
OUTPUT_FOLDER=/app/outputs

# Monitoring Configuration
ENABLE_METRICS=true
PROMETHEUS_MULTIPROC_DIR=/tmp
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}

# Security Configuration
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization

# Flex Server Configuration
FLEX_SERVERS=192.168.181.56,192.168.181.57,192.168.181.58,192.168.181.59,192.168.181.60,192.168.181.61,192.168.181.62,192.168.181.63,192.168.181.64
FLEX_USERNAME=${FLEX_USERNAME}
FLEX_PASSWORD=${FLEX_PASSWORD}

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# Server Configuration
SERVER_NAME=localhost:5050
PREFERRED_URL_SCHEME=http

# =============================================================================
# CABLECAST VOD INTEGRATION CONFIGURATION
# =============================================================================

# Cablecast API Configuration
CABLECAST_API_URL=https://vod.scctv.org/CablecastAPI/v1
CABLECAST_SERVER_URL=https://vod.scctv.org/CablecastAPI/v1

# Location ID (choose the appropriate site ID)
CABLECAST_LOCATION_ID=3

# API Key (get this from your Cablecast administrator)
CABLECAST_API_KEY=${CABLECAST_API_KEY}

# HTTP Basic Authentication
CABLECAST_USER_ID=${CABLECAST_USER_ID}
CABLECAST_PASSWORD=${CABLECAST_PASSWORD}

# VOD Integration Settings
AUTO_PUBLISH_TO_VOD=false
VOD_DEFAULT_QUALITY=1
VOD_UPLOAD_TIMEOUT=300

# VOD Processing Settings
VOD_MAX_RETRIES=3
VOD_RETRY_DELAY=60
VOD_BATCH_SIZE=10

# VOD Monitoring
VOD_STATUS_CHECK_INTERVAL=30
VOD_PROCESSING_TIMEOUT=1800
"""
    
    template_path = Path('.env.secure_template')
    try:
        with open(template_path, 'w') as f:
            f.write(template_content)
        print(f"✅ Created secure template: {template_path}")
        return template_path
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return None

def generate_remediation_plan(hardcoded_creds):
    """Generate a remediation plan based on identified issues."""
    print("\n🔧 REMEDIATION PLAN")
    print("=" * 50)
    
    if not hardcoded_creds:
        print("✅ No hardcoded credentials found!")
        return
    
    print("🚨 CRITICAL SECURITY ISSUES FOUND:")
    print()
    
    for i, cred in enumerate(hardcoded_creds, 1):
        print(f"{i}. {cred['type']}")
        print(f"   Current value: {cred['value'][:10]}...")
        print(f"   Action: Replace with environment variable")
        print()
    
    print("📋 IMMEDIATE ACTIONS REQUIRED:")
    print("1. Generate new secure credentials for each service")
    print("2. Update database passwords")
    print("3. Update Flex server credentials")
    print("4. Update Cablecast credentials")
    print("5. Generate new secret keys")
    print("6. Test all services with new credentials")
    print("7. Remove old credentials from version control")
    print()

def main():
    """Main remediation function."""
    print("🔒 Archivist Security Remediation Script")
    print("=" * 50)
    print()
    print("This script will help remediate critical security issues")
    print("identified in the security audit.")
    print()
    
    # Step 1: Backup current .env
    print("📦 Step 1: Backing up current .env file...")
    backup_path = backup_env_file()
    
    # Step 2: Identify hardcoded credentials
    print("\n🔍 Step 2: Identifying hardcoded credentials...")
    hardcoded_creds = identify_hardcoded_credentials()
    
    if hardcoded_creds:
        print(f"⚠️  Found {len(hardcoded_creds)} hardcoded credentials:")
        for cred in hardcoded_creds:
            print(f"   - {cred['type']}: {cred['value'][:10]}...")
    else:
        print("✅ No hardcoded credentials found!")
    
    # Step 3: Create secure template
    print("\n📝 Step 3: Creating secure environment template...")
    template_path = create_secure_env_template()
    
    # Step 4: Generate remediation plan
    generate_remediation_plan(hardcoded_creds)
    
    # Step 5: Provide next steps
    print("🚀 NEXT STEPS:")
    print("=" * 50)
    print()
    print("1. 🔐 Generate new secure credentials:")
    print("   python scripts/security/generate_secure_credentials.py")
    print()
    print("2. 📝 Update your .env file with new credentials")
    print("   (Use the template created as .env.secure_template)")
    print()
    print("3. 🔄 Update service passwords:")
    print("   - PostgreSQL database")
    print("   - Flex servers")
    print("   - Cablecast system")
    print("   - Grafana dashboard")
    print()
    print("4. 🧪 Test all services with new credentials")
    print()
    print("5. 🗑️  Remove old credentials from version control")
    print("   git filter-branch --force --index-filter")
    print("   'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all")
    print()
    print("6. 🔒 Set secure file permissions:")
    print("   chmod 600 .env")
    print("   chmod 600 .env.backup_*")
    print()
    
    if backup_path:
        print(f"📁 Backup created: {backup_path}")
    
    if template_path:
        print(f"📄 Template created: {template_path}")
    
    print()
    print("⚠️  IMPORTANT SECURITY REMINDERS:")
    print("- Never commit .env files to version control")
    print("- Use different passwords for each service")
    print("- Rotate credentials regularly")
    print("- Consider using a secrets management solution")
    print("- Monitor for credential exposure")
    
    print()
    print("🎉 Remediation script completed!")
    print("Please follow the next steps to secure your application.")

if __name__ == "__main__":
    main() 