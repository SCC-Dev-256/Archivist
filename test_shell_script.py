#!/usr/bin/env python3
"""
Simple test to verify shell script argument parsing
"""

import subprocess
import sys

def test_shell_script():
    """Test the shell script argument parsing."""
    print("🧪 Testing Shell Script Argument Parsing")
    print("="*50)
    
    # Test cases
    test_cases = [
        (["simple", "--dry-run"], "Simple mode with dry-run"),
        (["complete", "--dry-run"], "Complete mode with dry-run"),
        (["--simple", "--dry-run"], "Legacy simple mode with dry-run"),
        (["--help"], "Help command"),
    ]
    
    for args, description in test_cases:
        print(f"\n--- Testing: {description} ---")
        print(f"   Arguments: {args}")
        
        try:
            cmd = ["./start_archivist.sh"] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("   ✅ PASS")
            else:
                print("   ❌ FAIL")
                print(f"   Error: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    test_shell_script() 