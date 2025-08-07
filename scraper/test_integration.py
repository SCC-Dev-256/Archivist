#!/usr/bin/env python3
# PURPOSE: Test the complete PDF to Flex server integration pipeline
# DEPENDENCIES: pdf_to_flex_integration, requests, json
# MODIFICATION NOTES: v1.0 - Integration testing

import json
import os
import sys
from pathlib import Path

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_to_flex_integration import PDFToFlexIntegration


def test_flex_server_connectivity():
    """Test connectivity to Flex server API."""
    print("🔍 Testing Flex Server Connectivity...")
    
    integration = PDFToFlexIntegration()
    status = integration.get_flex_server_status()
    
    if status.get('success'):
        print("✅ Flex servers are accessible")
        mounts = status.get('data', {}).get('mount_points', [])
        for mount in mounts:
            print(f"   📁 {mount['path']}: {mount['status']}")
        return True
    else:
        print(f"❌ Flex server error: {status.get('error')}")
        return False


def test_city_mappings():
    """Test city to Flex server mappings."""
    print("\n🗺️  Testing City Mappings...")
    
    integration = PDFToFlexIntegration()
    
    test_cities = [
        "Oakdale", "Mahtomedi", "White Bear Township", 
        "Grant", "Birchwood", "Lake Elmo"
    ]
    
    for city in test_cities:
        mapping = integration.get_city_mapping(city)
        if mapping:
            print(f"✅ {city} → {mapping.flex_server} ({mapping.mount_path})")
        else:
            print(f"❌ {city} → No mapping found")
    
    return True


def test_api_endpoints():
    """Test API endpoint accessibility."""
    print("\n🔗 Testing API Endpoints...")
    
    integration = PDFToFlexIntegration()
    
    # Test mount points endpoint
    try:
        response = integration.session.get(f"{integration.api_base_url}/api/mount-points")
        if response.status_code == 200:
            print("✅ /api/mount-points - Accessible")
        else:
            print(f"❌ /api/mount-points - HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ /api/mount-points - Error: {e}")
    
    # Test browse endpoint
    try:
        response = integration.session.get(f"{integration.api_base_url}/api/browse?path=/mnt/flex-1")
        if response.status_code == 200:
            print("✅ /api/browse - Accessible")
        else:
            print(f"❌ /api/browse - HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ /api/browse - Error: {e}")
    
    return True


def test_sample_integration():
    """Test integration with a small sample of scraped results."""
    print("\n🧪 Testing Sample Integration...")
    
    # Check for results file
    results_files = [
        "civicengage_enhanced_results.json",
        "comprehensive_results.json", 
        "results.json"
    ]
    
    results_file = None
    for file in results_files:
        if os.path.exists(file):
            results_file = file
            break
    
    if not results_file:
        print("❌ No results file found. Please run the scraper first.")
        return False
    
    print(f"📄 Using results file: {results_file}")
    
    # Load and analyze results
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print(f"📊 Found {len(results)} PDFs in results")
    
    # Show sample of cities
    cities = list(set(item.get('city', 'Unknown') for item in results))
    print(f"🏙️  Cities: {', '.join(cities[:5])}{'...' if len(cities) > 5 else ''}")
    
    # Test with first few results
    sample_size = min(3, len(results))
    sample_results = results[:sample_size]
    
    print(f"\n🧪 Testing with {sample_size} sample PDFs...")
    
    # Create temporary results file for testing
    test_file = "test_integration_sample.json"
    with open(test_file, 'w') as f:
        json.dump(sample_results, f, indent=2)
    
    # Run integration test
    integration = PDFToFlexIntegration()
    
    try:
        # Note: This will actually try to download and upload files
        # Set download_dir to a test directory
        test_results = integration.process_scraped_results(
            test_file, 
            download_dir="test_downloads"
        )
        
        if 'summary' in test_results:
            summary = test_results['summary']
            print(f"\n📊 Test Integration Summary:")
            print(f"   Total PDFs: {summary['total_pdfs']}")
            print(f"   Processed: {summary['processed']}")
            print(f"   Failed: {summary['failed']}")
            
            if summary['processed'] > 0:
                print("✅ Integration test successful!")
                return True
            else:
                print("❌ Integration test failed - no files processed")
                return False
        else:
            print("❌ Integration test failed - no summary generated")
            return False
            
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)


def main():
    """Main test function."""
    print("PDF to Flex Server Integration Test")
    print("=" * 50)
    
    tests = [
        ("Flex Server Connectivity", test_flex_server_connectivity),
        ("City Mappings", test_city_mappings),
        ("API Endpoints", test_api_endpoints),
        ("Sample Integration", test_sample_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Integration system is ready.")
        print("\nNext steps:")
        print("1. Run the scraper to get fresh PDF results")
        print("2. Run the integration: python3 scraper/pdf_to_flex_integration.py")
        print("3. Check the VOD system for retranscription jobs")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 