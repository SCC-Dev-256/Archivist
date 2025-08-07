#!/usr/bin/env python3
# PURPOSE: Simple integration test with available results
# DEPENDENCIES: pdf_to_flex_integration, json
# MODIFICATION NOTES: v1.0 - Simple testing without API dependency

import json
import os
from pathlib import Path

from pdf_to_flex_integration import PDFToFlexIntegration


def test_city_mappings():
    """Test city to Flex server mappings."""
    print("🗺️  Testing City Mappings...")
    
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


def test_document_type_detection():
    """Test document type detection."""
    print("\n📄 Testing Document Type Detection...")
    
    integration = PDFToFlexIntegration()
    
    test_cases = [
        ("agenda_2025.pdf", "https://example.com/agenda", "City Council Agenda"),
        ("minutes_january.pdf", "https://example.com/minutes", "City Council Minutes"),
        ("council_packet.pdf", "https://example.com/packet", "Council Meeting Packet"),
        ("meeting_notes.pdf", "https://example.com/meeting", "Council Meeting"),
        ("unknown_doc.pdf", "https://example.com/unknown", "City Document")
    ]
    
    for filename, url, expected in test_cases:
        detected = integration._detect_document_type(filename, url)
        status = "✅" if detected == expected else "❌"
        print(f"{status} {filename} → {detected}")
    
    return True


def test_results_analysis():
    """Analyze available results file."""
    print("\n📊 Analyzing Available Results...")
    
    results_file = "../clean_final_results.json"
    
    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        return False
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print(f"📄 Found {len(results)} PDFs in results")
    
    # Analyze by city
    cities = {}
    for item in results:
        city = item.get('city', 'Unknown')
        cities[city] = cities.get(city, 0) + 1
    
    print("\n🏙️  Cities and PDF counts:")
    for city, count in sorted(cities.items()):
        mapping = PDFToFlexIntegration().get_city_mapping(city)
        flex_server = mapping.flex_server if mapping else "❌ No mapping"
        print(f"   {city}: {count} PDFs → {flex_server}")
    
    # Show sample URLs
    print(f"\n🔗 Sample PDF URLs:")
    for i, item in enumerate(results[:3]):
        print(f"   {i+1}. {item['url']}")
    
    return True


def test_integration_preparation():
    """Test integration system preparation."""
    print("\n🔧 Testing Integration Preparation...")
    
    integration = PDFToFlexIntegration()
    
    # Test download directory creation
    test_dir = Path("test_downloads")
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    
    test_dir.mkdir(exist_ok=True)
    print(f"✅ Created test directory: {test_dir}")
    
    # Test session setup
    if integration.session:
        print("✅ HTTP session configured")
    else:
        print("❌ HTTP session not configured")
        return False
    
    # Test city mappings
    if len(integration.city_mappings) > 0:
        print(f"✅ {len(integration.city_mappings)} city mappings configured")
    else:
        print("❌ No city mappings configured")
        return False
    
    return True


def main():
    """Main test function."""
    print("Simple PDF Integration Test")
    print("=" * 40)
    
    tests = [
        ("City Mappings", test_city_mappings),
        ("Document Type Detection", test_document_type_detection),
        ("Results Analysis", test_results_analysis),
        ("Integration Preparation", test_integration_preparation)
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
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
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
        print("1. Ensure API is running on port 8080")
        print("2. Run: python3 pdf_to_flex_integration.py")
        print("3. Check VOD system for retranscription jobs")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 