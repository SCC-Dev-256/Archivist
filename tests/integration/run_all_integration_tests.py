#!/usr/bin/env python3
"""
Integration Test Runner

This script runs all integration tests across all seven phases:
1. Database ↔ Service Integration
2. API Integration
3. External Service Integration
4. System Integration
5. Monitoring Integration
6. Critical Path Integration
7. Admin UI Integration

Usage:
    python run_all_integration_tests.py [--phase PHASE] [--verbose] [--report]
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def run_phase_1_tests():
    """Run Phase 1: Database ↔ Service Integration Tests."""
    logger.info("🚀 Starting Phase 1: Database ↔ Service Integration Tests")
    
    try:
        from tests.integration.test_database_service_integration import run_database_service_integration_tests
        success = run_database_service_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 1 tests failed: {e}")
        return False


def run_phase_2_tests():
    """Run Phase 2: API Integration Tests."""
    logger.info("🚀 Starting Phase 2: API Integration Tests")
    
    try:
        from tests.integration.test_api_integration import run_api_integration_tests
        success = run_api_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 2 tests failed: {e}")
        return False


def run_phase_3_tests():
    """Run Phase 3: External Service Integration Tests."""
    logger.info("🚀 Starting Phase 3: External Service Integration Tests")
    
    try:
        from tests.integration.test_external_service_integration import run_external_service_integration_tests
        success = run_external_service_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 3 tests failed: {e}")
        return False


def run_phase_4_tests():
    """Run Phase 4: System Integration Tests."""
    logger.info("🚀 Starting Phase 4: System Integration Tests")
    
    try:
        from tests.integration.test_system_integration import run_system_integration_tests
        success = run_system_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 4 tests failed: {e}")
        return False


def run_phase_5_tests():
    """Run Phase 5: Monitoring Integration Tests."""
    logger.info("🚀 Starting Phase 5: Monitoring Integration Tests")
    
    try:
        from tests.integration.test_monitoring_integration import run_monitoring_integration_tests
        success = run_monitoring_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 5 tests failed: {e}")
        return False


def run_phase_6_tests():
    """Run Phase 6: Critical Path Integration Tests."""
    logger.info("🚀 Starting Phase 6: Critical Path Integration Tests")
    
    try:
        from tests.integration.test_critical_path_integration import run_critical_path_integration_tests
        success = run_critical_path_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 6 tests failed: {e}")
        return False


def run_phase_7_tests():
    """Run Phase 7: Admin UI Integration Tests."""
    logger.info("🚀 Starting Phase 7: Admin UI Integration Tests")
    
    try:
        from tests.integration.test_admin_ui_integration import run_admin_ui_integration_tests
        success = run_admin_ui_integration_tests()
        return success
    except Exception as e:
        logger.error(f"❌ Phase 7 tests failed: {e}")
        return False


def generate_integration_test_report(results):
    """Generate a comprehensive integration test report."""
    logger.info("📊 Generating Integration Test Report")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success, _ in results if success)
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    
    report = f"""
# Integration Test Report

## 📈 Summary
- **Total Tests:** {total_tests}
- **Passed:** {passed_tests}
- **Failed:** {failed_tests}
- **Success Rate:** {success_rate:.1f}%

## 📋 Detailed Results

"""
    
    # Group results by phase
    phases = {
        'Phase 1 - Database ↔ Service': [],
        'Phase 2 - API Integration': [],
        'Phase 3 - External Services': [],
        'Phase 4 - System Integration': [],
        'Phase 5 - Monitoring Integration': [],
        'Phase 6 - Critical Path Integration': [],
        'Phase 7 - Admin UI Integration': []
    }
    
    for test_name, success, message in results:
        if 'database_service' in test_name.lower():
            phases['Phase 1 - Database ↔ Service'].append((test_name, success, message))
        elif 'api' in test_name.lower():
            phases['Phase 2 - API Integration'].append((test_name, success, message))
        elif 'external_service' in test_name.lower():
            phases['Phase 3 - External Services'].append((test_name, success, message))
        elif 'system' in test_name.lower():
            phases['Phase 4 - System Integration'].append((test_name, success, message))
        elif 'monitoring' in test_name.lower():
            phases['Phase 5 - Monitoring Integration'].append((test_name, success, message))
        elif 'critical_path' in test_name.lower():
            phases['Phase 6 - Critical Path Integration'].append((test_name, success, message))
        elif 'admin_ui' in test_name.lower():
            phases['Phase 7 - Admin UI Integration'].append((test_name, success, message))
    
    for phase_name, phase_results in phases.items():
        if phase_results:
            phase_passed = sum(1 for _, success, _ in phase_results if success)
            phase_total = len(phase_results)
            phase_rate = (phase_passed / phase_total) * 100 if phase_total > 0 else 0
            
            report += f"### {phase_name}\n"
            report += f"- **Passed:** {phase_passed}/{phase_total} ({phase_rate:.1f}%)\n\n"
            
            for test_name, success, message in phase_results:
                status = "✅ PASS" if success else "❌ FAIL"
                report += f"- {status} {test_name}: {message}\n"
            
            report += "\n"
    
    # Add recommendations
    report += "## 🎯 Recommendations\n\n"
    
    if success_rate >= 90:
        report += "✅ **Excellent!** Integration test coverage is comprehensive and reliable.\n"
    elif success_rate >= 75:
        report += "⚠️ **Good progress.** Some areas need attention but overall coverage is solid.\n"
    elif success_rate >= 50:
        report += "🔧 **Needs work.** Several integration areas require improvement.\n"
    else:
        report += "🚨 **Critical issues.** Integration test coverage needs significant improvement.\n"
    
    if failed_tests > 0:
        report += "\n### Priority Actions:\n"
        report += "1. **Review failed tests** - Investigate and fix failing integration scenarios\n"
        report += "2. **Improve error handling** - Ensure graceful failure recovery\n"
        report += "3. **Enhance test coverage** - Add missing integration scenarios\n"
        report += "4. **Performance optimization** - Address any performance issues identified\n"
        report += "5. **Monitoring validation** - Verify monitoring and alerting systems\n"
        report += "6. **Critical path validation** - Ensure core business workflows are reliable\n"
    
    return report


def main():
    """Main integration test runner."""
    parser = argparse.ArgumentParser(description='Run Archivist integration tests')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3, 4, 5, 6, 7], 
                       help='Run specific phase only (1-7)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--report', '-r', action='store_true',
                       help='Generate detailed report')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    logger.info("🎯 Archivist Integration Test Suite")
    logger.info("=" * 50)
    
    # Define phases
    phases = [
        ("Phase 1: Database ↔ Service Integration", run_phase_1_tests),
        ("Phase 2: API Integration", run_phase_2_tests),
        ("Phase 3: External Service Integration", run_phase_3_tests),
        ("Phase 4: System Integration", run_phase_4_tests),
        ("Phase 5: Monitoring Integration", run_phase_5_tests),
        ("Phase 6: Critical Path Integration", run_phase_6_tests),
        ("Phase 7: Admin UI Integration", run_phase_7_tests)
    ]
    
    # Run tests
    all_results = []
    start_time = time.time()
    
    if args.phase:
        # Run specific phase
        phase_idx = args.phase - 1
        if 0 <= phase_idx < len(phases):
            phase_name, phase_func = phases[phase_idx]
            logger.info(f"🎯 Running {phase_name}")
            success = phase_func()
            all_results.append((phase_name, success, "Completed"))
        else:
            logger.error(f"Invalid phase number: {args.phase}")
            return 1
    else:
        # Run all phases
        for phase_name, phase_func in phases:
            logger.info(f"🎯 Running {phase_name}")
            success = phase_func()
            all_results.append((phase_name, success, "Completed"))
    
    # Calculate overall results
    total_time = time.time() - start_time
    total_phases = len(all_results)
    passed_phases = sum(1 for _, success, _ in all_results if success)
    
    # Generate summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 INTEGRATION TEST SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Phases: {total_phases}")
    logger.info(f"Passed: {passed_phases}")
    logger.info(f"Failed: {total_phases - passed_phases}")
    logger.info(f"Success Rate: {(passed_phases/total_phases)*100:.1f}%")
    logger.info(f"Total Time: {total_time:.2f}s")
    
    # Generate detailed report if requested
    if args.report:
        report = generate_integration_test_report(all_results)
        
        # Save report to file
        report_file = f"integration_test_report_{int(time.time())}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"📄 Detailed report saved to: {report_file}")
        
        # Also print to console
        print("\n" + report)
    
    # Return appropriate exit code
    if passed_phases == total_phases:
        logger.info("🎉 All integration tests passed!")
        return 0
    else:
        logger.error(f"❌ {total_phases - passed_phases} phase(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 