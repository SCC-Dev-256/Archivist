#!/usr/bin/env python3
"""
Secure Credential Generator for Archivist Application

This script generates secure passwords, secret keys, and other credentials
for the Archivist application. It follows security best practices and
generates cryptographically secure random values.

Usage:
    python scripts/security/generate_secure_credentials.py

Security Features:
- Uses cryptographically secure random number generation
- Generates strong passwords with mixed character sets
- Creates secure secret keys for Flask and JWT
- Provides different strength levels for different use cases
"""

import secrets
import string
import os
import sys
from pathlib import Path

def generate_secure_password(length=32, include_special=True):
    """
    Generate a cryptographically secure password.
    
    Args:
        length (int): Length of the password
        include_special (bool): Whether to include special characters
    
    Returns:
        str: Secure password
    """
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one character from each required set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits)
    ]
    
    if include_special:
        password.append(secrets.choice(special))
        # Add remaining characters
        all_chars = lowercase + uppercase + digits + special
    else:
        # Add remaining characters (no special chars)
        all_chars = lowercase + uppercase + digits
    
    # Fill the rest of the password
    for _ in range(length - len(password)):
        password.append(secrets.choice(all_chars))
    
    # Shuffle the password
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    
    return ''.join(password_list)

def generate_secret_key(length=64):
    """
    Generate a cryptographically secure secret key.
    
    Args:
        length (int): Length of the secret key in bytes
    
    Returns:
        str: Hex-encoded secret key
    """
    return secrets.token_hex(length)

def generate_api_key(length=32):
    """
    Generate a secure API key.
    
    Args:
        length (int): Length of the API key
    
    Returns:
        str: Secure API key
    """
    # Use URL-safe base64 encoding for API keys
    return secrets.token_urlsafe(length)

def main():
    """Main function to generate all credentials."""
    print("🔐 Archivist Secure Credential Generator")
    print("=" * 50)
    print()
    print("This script generates secure credentials for the Archivist application.")
    print("⚠️  IMPORTANT: Keep these credentials secure and never share them!")
    print()
    
    # Generate credentials
    credentials = {
        "Database Password": generate_secure_password(24, include_special=True),
        "Flex Server Password": generate_secure_password(24, include_special=True),
        "Cablecast Password": generate_secure_password(24, include_special=True),
        "Grafana Password": generate_secure_password(20, include_special=True),
        "Flask Secret Key": generate_secret_key(32),
        "JWT Secret Key": generate_secret_key(32),
        "Dashboard Secret Key": generate_secret_key(32),
        "Cablecast API Key": generate_api_key(32),
        "Redis Password": generate_secure_password(16, include_special=False),
    }
    
    # Display credentials
    print("📋 Generated Credentials:")
    print("-" * 30)
    for name, value in credentials.items():
        print(f"{name}: {value}")
    
    print()
    print("🔧 Environment Variables to Set:")
    print("-" * 30)
    
    env_vars = {
        "POSTGRES_PASSWORD": credentials["Database Password"],
        "FLEX_PASSWORD": credentials["Flex Server Password"],
        "CABLECAST_PASSWORD": credentials["Cablecast Password"],
        "GRAFANA_PASSWORD": credentials["Grafana Password"],
        "SECRET_KEY": credentials["Flask Secret Key"],
        "JWT_SECRET_KEY": credentials["JWT Secret Key"],
        "DASHBOARD_SECRET_KEY": credentials["Dashboard Secret Key"],
        "CABLECAST_API_KEY": credentials["Cablecast API Key"],
        "REDIS_PASSWORD": credentials["Redis Password"],
    }
    
    for var, value in env_vars.items():
        print(f"export {var}='{value}'")
    
    print()
    print("📝 .env File Entries:")
    print("-" * 30)
    for var, value in env_vars.items():
        print(f"{var}={value}")
    
    print()
    print("🚨 SECURITY REMINDERS:")
    print("-" * 30)
    print("1. ✅ Store these credentials securely")
    print("2. ✅ Never commit them to version control")
    print("3. ✅ Use different passwords for each service")
    print("4. ✅ Rotate credentials regularly")
    print("5. ✅ Use environment variables in production")
    print("6. ✅ Consider using a secrets management solution")
    
    print()
    print("💡 Next Steps:")
    print("-" * 30)
    print("1. Copy the .env entries to your .env file")
    print("2. Update your database passwords")
    print("3. Update your Flex server credentials")
    print("4. Update your Cablecast credentials")
    print("5. Test all services with new credentials")
    print("6. Remove old credentials from version control")
    
    # Option to save to file
    save_to_file = input("\n💾 Save credentials to a secure file? (y/N): ").lower().strip()
    if save_to_file == 'y':
        filename = input("Enter filename (default: archivist_credentials.txt): ").strip()
        if not filename:
            filename = "archivist_credentials.txt"
        
        try:
            with open(filename, 'w') as f:
                f.write("# Archivist Application Credentials\n")
                f.write("# Generated on: " + str(Path(__file__).stat().st_mtime) + "\n")
                f.write("# KEEP THIS FILE SECURE!\n\n")
                
                f.write("# Environment Variables:\n")
                for var, value in env_vars.items():
                    f.write(f"{var}={value}\n")
                
                f.write("\n# Individual Credentials:\n")
                for name, value in credentials.items():
                    f.write(f"# {name}: {value}\n")
            
            # Set secure permissions
            os.chmod(filename, 0o600)
            print(f"✅ Credentials saved to {filename} with secure permissions")
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
    
    print()
    print("🎉 Credential generation complete!")
    print("Remember to update your application configuration with these new credentials.")

if __name__ == "__main__":
    main() 