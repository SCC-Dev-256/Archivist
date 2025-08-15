#!/usr/bin/env python3
"""
Comprehensive Test Script for Unified Archivist System

This script tests all modes and configurations of the unified startup system
to ensure everything works correctly before migration.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(cmd: List[str], description: str) -> Dict[str, Any]:
    """Run a command and return results."""
    print(f"🧪 Testing: {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        success = result.returncode == 0
        print(f"   Status: {'✅ PASS' if success else '❌ FAIL'}")
        
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        
        if result.stderr and not success:
            print(f"   Error: {result.stderr.strip()}")
        
        return {
            "success": success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
        
    except subprocess.TimeoutExpired:
        print(f"   Status: ❌ TIMEOUT")
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out",
            "returncode": -1
        }
    except Exception as e:
        print(f"   Status: ❌ ERROR")
        print(f"   Error: {str(e)}")
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

def test_help_command():
    """Test help command functionality."""
    print("\n" + "="*60)
    print("🔍 TEST 1: Help Command")
    print("="*60)
    
    # Test Python script help
    result1 = run_command(
        ["python3", "start_archivist_unified.py", "--help"],
        "Python script help"
    )
    
    # Test shell script help
    result2 = run_command(
        ["./start_archivist.sh", "--help"],
        "Shell script help"
    )
    
    return result1["success"] and result2["success"]

def test_dry_run_modes():
    """Test dry-run mode for all startup modes."""
    print("\n" + "="*60)
    print("🔍 TEST 2: Dry-Run Modes")
    print("="*60)
    
    modes = ["complete", "simple", "integrated", "vod-only", "centralized"]
    results = {}
    
    for mode in modes:
        print(f"\n--- Testing {mode.upper()} mode ---")
        
        # Test Python script
        result = run_command(
            ["python3", "start_archivist_unified.py", mode, "--dry-run"],
            f"Python {mode} mode dry-run"
        )
        results[f"python_{mode}"] = result["success"]
        
        # Test shell script
        result = run_command(
            ["./start_archivist.sh", mode, "--dry-run"],
            f"Shell {mode} mode dry-run"
        )
        results[f"shell_{mode}"] = result["success"]
    
    return results

def test_configuration_files():
    """Test configuration file loading."""
    print("\n" + "="*60)
    print("🔍 TEST 3: Configuration Files")
    print("="*60)
    
    config_files = ["config/dev.json", "config/staging.json", "config/production.json"]
    results = {}
    
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"\n--- Testing {config_file} ---")
            
            # Test loading config file
            result = run_command(
                ["python3", "start_archivist_unified.py", "--config-file", config_file, "--dry-run"],
                f"Load {config_file}"
            )
            results[config_file] = result["success"]
            
            # Validate JSON syntax
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
                print(f"   JSON Syntax: ✅ VALID")
            except json.JSONDecodeError as e:
                print(f"   JSON Syntax: ❌ INVALID - {e}")
                results[config_file] = False
        else:
            print(f"\n--- {config_file} not found ---")
            results[config_file] = False
    
    return results

def test_port_configurations():
    """Test custom port configurations."""
    print("\n" + "="*60)
    print("🔍 TEST 4: Port Configurations")
    print("="*60)
    
    port_tests = [
        ("admin=8081,dashboard=5052", "Alternative ports"),
        ("admin=9000,dashboard=9001", "High ports"),
        ("admin=5050,dashboard=5051", "Low ports")
    ]
    
    results = {}
    
    for ports, description in port_tests:
        print(f"\n--- Testing {description} ---")
        
        result = run_command(
            ["python3", "start_archivist_unified.py", "complete", "--ports", ports, "--dry-run"],
            f"Custom ports: {ports}"
        )
        results[ports] = result["success"]
    
    return results

def test_status_command():
    """Test status command functionality."""
    print("\n" + "="*60)
    print("🔍 TEST 5: Status Command")
    print("="*60)
    
    # Test status command
    result = run_command(
        ["python3", "start_archivist_unified.py", "--status"],
        "System status"
    )
    
    return result["success"]

def test_legacy_compatibility():
    """Test legacy option compatibility."""
    print("\n" + "="*60)
    print("🔍 TEST 6: Legacy Compatibility")
    print("="*60)
    
    legacy_tests = [
        (["--simple"], "Legacy --simple option"),
        (["--integrated"], "Legacy --integrated option"),
        (["--vod-only"], "Legacy --vod-only option"),
        (["--centralized"], "Legacy --centralized option")
    ]
    
    results = {}
    
    for args, description in legacy_tests:
        print(f"\n--- Testing {description} ---")
        
        result = run_command(
            ["./start_archivist.sh"] + args + ["--dry-run"],
            f"Legacy: {' '.join(args)}"
        )
        results[description] = result["success"]
    
    return results

def test_error_handling():
    """Test error handling and edge cases."""
    print("\n" + "="*60)
    print("🔍 TEST 7: Error Handling")
    print("="*60)
    
    error_tests = [
        (["invalid-mode"], "Invalid mode"),
        (["--config-file", "nonexistent.json"], "Non-existent config file"),
        (["--ports", "invalid=format"], "Invalid port format"),
        (["--concurrency", "0"], "Invalid concurrency")
    ]
    
    results = {}
    
    for args, description in error_tests:
        print(f"\n--- Testing {description} ---")
        
        result = run_command(
            ["python3", "start_archivist_unified.py"] + args,
            f"Error case: {' '.join(args)}"
        )
        # For error handling, we expect these to fail gracefully
        results[description] = not result["success"]  # Should fail gracefully
    
    return results

def generate_test_report(all_results: Dict[str, Any]):
    """Generate a comprehensive test report."""
    print("\n" + "="*60)
    print("📊 TEST REPORT")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, results in all_results.items():
        print(f"\n🔍 {test_name.upper()}:")
        
        if isinstance(results, dict):
            for subtest, success in results.items():
                total_tests += 1
                if success:
                    passed_tests += 1
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {status} {subtest}")
        else:
            total_tests += 1
            if results:
                passed_tests += 1
            status = "✅ PASS" if results else "❌ FAIL"
            print(f"   {status}")
    
    print(f"\n📈 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! The unified system is ready for migration.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Please review the issues before migration.")
        return False

def main():
    """Main test function."""
    print("🧪 Unified Archivist System - Comprehensive Test Suite")
    print("="*60)
    print("This script tests all aspects of the unified startup system")
    print("to ensure it's ready for migration from the old scripts.")
    print("="*60)
    
    all_results = {}
    
    # Run all tests
    all_results["Help Command"] = test_help_command()
    all_results["Dry-Run Modes"] = test_dry_run_modes()
    all_results["Configuration Files"] = test_configuration_files()
    all_results["Port Configurations"] = test_port_configurations()
    all_results["Status Command"] = test_status_command()
    all_results["Legacy Compatibility"] = test_legacy_compatibility()
    all_results["Error Handling"] = test_error_handling()
    
    # Generate report
    success = generate_test_report(all_results)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 