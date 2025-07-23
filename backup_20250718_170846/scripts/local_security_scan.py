#!/usr/bin/env python3
"""
Local Security Scanning Script
Replaces GitHub Actions security checks with local tools.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print(f"Error: {e}")
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print("Error output:")
            print(e.stderr)
        return False

def main():
    """Run all security checks locally."""
    print("🔒 Local Security Scan for Archivist")
    print("Replacing GitHub Actions with local tools")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    results = []
    
    # 1. Dependency vulnerability scan (replaces dependency-check)
    print("\n1. Checking for vulnerable dependencies...")
    success = run_command(
        ["safety", "check", "--json"],
        "Dependency vulnerability scan with Safety"
    )
    results.append(("Dependency Scan", success))
    
    # 2. Code security scan (replaces security-scan)
    print("\n2. Scanning code for security issues...")
    success = run_command(
        ["bandit", "-r", "core", "-f", "json", "-o", "bandit-report.json"],
        "Code security scan with Bandit"
    )
    results.append(("Code Security Scan", success))
    
    # 3. Advanced security scan (replaces semgrep)
    print("\n3. Running advanced security analysis...")
    success = run_command(
        ["semgrep", "scan", "--config=auto", "--json", "--output=semgrep-report.json"],
        "Advanced security scan with Semgrep"
    )
    results.append(("Advanced Security Scan", success))
    
    # 4. Code formatting check (replaces lint-and-format)
    print("\n4. Checking code formatting...")
    success = run_command(
        ["python", "-m", "black", "--check", "--diff", "core"],
        "Code formatting check with Black"
    )
    results.append(("Code Formatting", success))
    
    # 5. Linting check
    print("\n5. Running code linting...")
    success = run_command(
        ["python", "-m", "flake8", "core", "--max-line-length=88"],
        "Code linting with Flake8"
    )
    results.append(("Code Linting", success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SECURITY SCAN SUMMARY")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for check_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{check_name:<25} {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All security checks passed!")
        return 0
    else:
        print("⚠️  Some security checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 