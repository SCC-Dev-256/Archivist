#!/usr/bin/env python3
"""
Quick Validation Script for Unified Archivist System

This script performs a quick validation of the core functionality
to ensure the unified system is working correctly.
"""

import os
import sys
import subprocess
from pathlib import Path

def test_basic_functionality():
    """Test basic functionality of the unified system."""
    print("🧪 Quick Validation: Unified Archivist System")
    print("="*50)
    
    # Test 1: Help command
    print("\n1. Testing help command...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("   ✅ Help command works")
        else:
            print("   ❌ Help command failed")
            return False
    except Exception as e:
        print(f"   ❌ Help command error: {e}")
        return False
    
    # Test 2: Status command
    print("\n2. Testing status command...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "--status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("   ✅ Status command works")
        else:
            print("   ❌ Status command failed")
            return False
    except Exception as e:
        print(f"   ❌ Status command error: {e}")
        return False
    
    # Test 3: Dry-run complete mode
    print("\n3. Testing complete mode dry-run...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "complete", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            print("   ✅ Complete mode dry-run works")
        else:
            print("   ❌ Complete mode dry-run failed")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Complete mode error: {e}")
        return False
    
    # Test 4: Configuration file loading
    print("\n4. Testing configuration file loading...")
    config_file = "config/dev.json"
    if Path(config_file).exists():
        try:
            result = subprocess.run(
                ["python3", "start_archivist_unified.py", "--config-file", config_file, "--dry-run"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                print("   ✅ Configuration file loading works")
            else:
                print("   ❌ Configuration file loading failed")
                print(f"   Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"   ❌ Configuration file error: {e}")
            return False
    else:
        print("   ⚠️  Configuration file not found, skipping")
    
    # Test 5: Port configuration
    print("\n5. Testing port configuration...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "simple", "--ports", "admin=8081,dashboard=5052", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            print("   ✅ Port configuration works")
        else:
            print("   ❌ Port configuration failed")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Port configuration error: {e}")
        return False
    
    # Test 6: Shell script compatibility
    print("\n6. Testing shell script compatibility...")
    try:
        result = subprocess.run(
            ["./start_archivist.sh", "simple", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            print("   ✅ Shell script compatibility works")
        else:
            print("   ❌ Shell script compatibility failed")
            print(f"   Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Shell script error: {e}")
        return False
    
    print("\n🎉 All basic functionality tests passed!")
    return True

def test_error_handling():
    """Test error handling."""
    print("\n" + "="*50)
    print("🔍 Testing Error Handling")
    print("="*50)
    
    # Test invalid mode
    print("\n1. Testing invalid mode...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "invalid-mode"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("   ✅ Invalid mode handled gracefully")
        else:
            print("   ❌ Invalid mode not handled properly")
            return False
    except Exception as e:
        print(f"   ❌ Invalid mode test error: {e}")
        return False
    
    # Test invalid config file
    print("\n2. Testing invalid config file...")
    try:
        result = subprocess.run(
            ["python3", "start_archivist_unified.py", "--config-file", "nonexistent.json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("   ✅ Invalid config file handled gracefully")
        else:
            print("   ❌ Invalid config file not handled properly")
            return False
    except Exception as e:
        print(f"   ❌ Invalid config file test error: {e}")
        return False
    
    print("\n🎉 All error handling tests passed!")
    return True

def main():
    """Main validation function."""
    print("🚀 Unified Archivist System - Quick Validation")
    print("="*60)
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed!")
        sys.exit(1)
    
    # Test error handling
    if not test_error_handling():
        print("\n❌ Error handling tests failed!")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("🎉 VALIDATION COMPLETE!")
    print("="*60)
    print("✅ All tests passed successfully")
    print("✅ The unified system is working correctly")
    print("✅ Ready for migration from old scripts")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Run the comprehensive test suite: python3 test_unified_system.py")
    print("2. Test with actual startup: ./start_archivist.sh dev --dry-run")
    print("3. Proceed with migration if all tests pass")
    
    sys.exit(0)

if __name__ == "__main__":
    main() 