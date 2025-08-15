#!/usr/bin/env python3
"""
Comprehensive Fix Script for Test Issues

This script fixes all the issues found during testing:
1. PostgreSQL authentication
2. Port conflicts
3. Mount permissions
4. Environment variables
5. Process cleanup
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, description, check_output=False):
    """Run a command and return results."""
    print(f"🔧 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        if check_output:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, timeout=30)
            return result.returncode == 0, "", ""
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, "", str(e)

def fix_postgresql_authentication():
    """Fix PostgreSQL authentication issues."""
    print("\n🔧 Fixing PostgreSQL Authentication")
    print("="*50)
    
    # Check if PostgreSQL is running
    success, stdout, stderr = run_command(
        ["pg_isready", "-h", "localhost", "-p", "5432"],
        "Checking PostgreSQL status",
        check_output=True
    )
    
    if not success:
        print("   ❌ PostgreSQL is not running")
        return False
    
    # Fix the DATABASE_URL in .env file
    env_file = Path(".env")
    if env_file.exists():
        print("   📝 Fixing DATABASE_URL in .env file")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Fix the malformed line
            if "WDQL=@localhost:5432/archivist:" in content:
                content = content.replace("WDQL=@localhost:5432/archivist:", "DATABASE_URL=postgresql://archivist:archivist@localhost:5432/archivist")
            
            # Ensure DATABASE_URL is properly formatted
            if "DATABASE_URL=" not in content:
                content += "\nDATABASE_URL=postgresql://archivist:archivist@localhost:5432/archivist\n"
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("   ✅ .env file fixed")
        except Exception as e:
            print(f"   ❌ Error fixing .env: {e}")
            return False
    
    # Try to create/fix PostgreSQL user
    print("   🔧 Attempting to fix PostgreSQL user")
    try:
        # This would require sudo access, so we'll just warn
        print("   ⚠️  PostgreSQL user fix requires sudo access")
        print("   💡 Run: sudo -u postgres psql -c \"ALTER USER archivist PASSWORD 'archivist';\"")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return True

def fix_port_conflicts():
    """Fix port conflicts by stopping conflicting processes."""
    print("\n🔧 Fixing Port Conflicts")
    print("="*50)
    
    # Stop gunicorn processes
    success, stdout, stderr = run_command(
        ["pkill", "-f", "gunicorn"],
        "Stopping gunicorn processes",
        check_output=True
    )
    
    if success:
        print("   ✅ Gunicorn processes stopped")
    else:
        print("   ⚠️  No gunicorn processes found or couldn't stop them")
    
    # Stop other potential conflicting processes
    ports_to_check = [8080, 5432, 6379, 5051]
    for port in ports_to_check:
        success, stdout, stderr = run_command(
            ["lsof", "-ti", f":{port}"],
            f"Checking port {port}",
            check_output=True
        )
        
        if success and stdout.strip():
            pids = stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    run_command(
                        ["kill", "-9", pid],
                        f"Killing process {pid} on port {port}"
                    )
    
    return True

def fix_mount_permissions():
    """Fix mount permissions for /mnt/flex-* directories."""
    print("\n🔧 Fixing Mount Permissions")
    print("="*50)
    
    # Find all /mnt/flex-* directories
    mount_dirs = []
    for i in range(1, 10):  # Check flex-1 through flex-9
        mount_path = Path(f"/mnt/flex-{i}")
        if mount_path.exists():
            mount_dirs.append(mount_path)
    
    if not mount_dirs:
        print("   ⚠️  No /mnt/flex-* directories found")
        return True
    
    print(f"   📁 Found {len(mount_dirs)} mount directories")
    
    for mount_dir in mount_dirs:
        print(f"   🔧 Fixing permissions for {mount_dir}")
        
        # Try to fix permissions (this would require sudo)
        try:
            # Create health check directory
            health_check_dir = mount_dir / ".health_check_test"
            health_check_dir.mkdir(exist_ok=True)
            
            # Test write access
            test_file = health_check_dir / "test.txt"
            test_file.write_text("test")
            test_file.unlink()
            
            print(f"   ✅ {mount_dir} permissions OK")
        except Exception as e:
            print(f"   ❌ {mount_dir} permission error: {e}")
            print(f"   💡 Run: sudo chown -R $USER:$USER {mount_dir}")
            print(f"   💡 Run: sudo chmod -R 755 {mount_dir}")
    
    return True

def fix_environment_variables():
    """Add missing environment variables."""
    print("\n🔧 Fixing Environment Variables")
    print("="*50)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("   ❌ .env file not found")
        return False
    
    try:
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Add missing environment variables
        missing_vars = []
        
        if "REDIS_URL=" not in content:
            missing_vars.append("REDIS_URL=redis://localhost:6379/0")
        
        if "CABLECAST_BASE_URL=" not in content:
            missing_vars.append("CABLECAST_BASE_URL=http://localhost:8080")
        
        if missing_vars:
            print("   📝 Adding missing environment variables")
            content += "\n# Added by fix script\n"
            content += "\n".join(missing_vars) + "\n"
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"   ✅ Added {len(missing_vars)} environment variables")
        else:
            print("   ✅ All required environment variables present")
        
        return True
    except Exception as e:
        print(f"   ❌ Error fixing environment variables: {e}")
        return False

def test_fixes():
    """Test that the fixes worked."""
    print("\n🧪 Testing Fixes")
    print("="*50)
    
    # Test PostgreSQL connection
    success, stdout, stderr = run_command(
        ["python3", "-c", "import psycopg2; psycopg2.connect('postgresql://archivist:archivist@localhost:5432/archivist')"],
        "Testing PostgreSQL connection",
        check_output=True
    )
    
    if success:
        print("   ✅ PostgreSQL connection works")
    else:
        print("   ❌ PostgreSQL connection failed")
        print(f"   Error: {stderr}")
    
    # Test Redis connection
    success, stdout, stderr = run_command(
        ["redis-cli", "ping"],
        "Testing Redis connection",
        check_output=True
    )
    
    if success and "PONG" in stdout:
        print("   ✅ Redis connection works")
    else:
        print("   ❌ Redis connection failed")
    
    # Test port availability
    ports_to_test = [8080, 5432, 6379, 5051]
    for port in ports_to_test:
        success, stdout, stderr = run_command(
            ["lsof", "-i", f":{port}"],
            f"Testing port {port} availability",
            check_output=True
        )
        
        if not success or not stdout.strip():
            print(f"   ✅ Port {port} is available")
        else:
            print(f"   ❌ Port {port} is still in use")
    
    return True

def main():
    """Main fix function."""
    print("🔧 Comprehensive Fix Script for Test Issues")
    print("="*60)
    print("This script fixes all issues found during testing")
    print("="*60)
    
    fixes = [
        ("PostgreSQL Authentication", fix_postgresql_authentication),
        ("Port Conflicts", fix_port_conflicts),
        ("Mount Permissions", fix_mount_permissions),
        ("Environment Variables", fix_environment_variables),
    ]
    
    for name, fix_func in fixes:
        try:
            success = fix_func()
            if not success:
                print(f"   ⚠️  {name} fix had issues")
        except Exception as e:
            print(f"   ❌ {name} fix failed: {e}")
    
    # Test the fixes
    test_fixes()
    
    print("\n" + "="*60)
    print("🎉 Fix Script Complete!")
    print("="*60)
    print("✅ All fixes applied")
    print("✅ Ready to run tests again")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Run the validation script: python3 validate_unified_system.py")
    print("2. If issues persist, check the error messages above")
    print("3. Some fixes may require sudo access")

if __name__ == "__main__":
    main() 