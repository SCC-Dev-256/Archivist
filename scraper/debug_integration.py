#!/usr/bin/env python3
# PURPOSE: Debug script for testing integration components
# DEPENDENCIES: pdf_to_flex_integration, pdf_stitcher
# MODIFICATION NOTES: v1.0 - Debug testing for integration system

import json
import os
import sys
from pathlib import Path

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_to_flex_integration import PDFToFlexIntegration
from pdf_stitcher import PDFStitcher


def test_api_connectivity():
    """Test API connectivity."""
    print("🔌 Testing API connectivity...")
    
    integration = PDFToFlexIntegration()
    health = integration.check_api_health()
    
    if health['success']:
        print(f"✅ API is healthy: {health['status']}")
        return True
    else:
        print(f"❌ API health check failed: {health['error']}")
        return False


def test_cablecast_mapper():
    """Test Cablecast show mapper import and functionality."""
    print("\n🎬 Testing Cablecast show mapper...")
    
    try:
        integration = PDFToFlexIntegration()
        
        # Test show matching
        result = integration.find_matching_cablecast_show("Birchwood", "2025-01-15", "Agenda")
        
        if result is None:
            print("⚠️  No matching show found (this is expected if no shows exist)")
        else:
            print(f"✅ Found matching show: {result['title']} (ID: {result['show_id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Cablecast mapper test failed: {e}")
        return False


def test_pdf_stitching():
    """Test PDF stitching functionality."""
    print("\n📄 Testing PDF stitching...")
    
    try:
        stitcher = PDFStitcher()
        
        # Test with sample data
        sample_results = {
            'processed': [
                {
                    'city': 'Birchwood',
                    'meeting_date': '2025-01-15',
                    'document_type': 'Agenda',
                    'local_path': '/tmp/test1.pdf'
                },
                {
                    'city': 'Birchwood', 
                    'meeting_date': '2025-01-15',
                    'document_type': 'Minutes',
                    'local_path': '/tmp/test2.pdf'
                }
            ],
            'unmatched': []
        }
        
        grouped = stitcher.group_pdfs_by_city_and_date(sample_results)
        print(f"✅ Grouped {len(grouped)} cities")
        
        for city, dates in grouped.items():
            print(f"   {city}: {len(dates)} date groups")
        
        return True
        
    except Exception as e:
        print(f"❌ PDF stitching test failed: {e}")
        return False


def test_results_file():
    """Test if results file exists and is valid."""
    print("\n📁 Testing results file...")
    
    possible_files = [
        "../clean_final_results.json",
        "../civicengage_enhanced_results.json", 
        "../comprehensive_results.json",
        "clean_final_results.json",
        "civicengage_enhanced_results.json"
    ]
    
    for file in possible_files:
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    print(f"✅ Found valid results file: {file} ({len(data)} items)")
                    return True
                else:
                    print(f"⚠️  Results file {file} exists but is not a list")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Results file {file} has invalid JSON: {e}")
            except Exception as e:
                print(f"❌ Error reading {file}: {e}")
    
    print("❌ No valid results file found")
    return False


def test_flex_server_mappings():
    """Test Flex server mappings."""
    print("\n🗂️  Testing Flex server mappings...")
    
    integration = PDFToFlexIntegration()
    
    test_cities = ["Birchwood", "Oakdale", "Mahtomedi", "Unknown"]
    
    for city in test_cities:
        mapping = integration.get_city_mapping(city)
        if mapping:
            print(f"✅ {city} -> {mapping.flex_server} ({mapping.mount_path})")
        else:
            print(f"⚠️  {city} -> No mapping found")
    
    return True


def main():
    """Run all debug tests."""
    print("🔍 Integration System Debug Tests")
    print("=" * 50)
    
    tests = [
        ("API Connectivity", test_api_connectivity),
        ("Cablecast Mapper", test_cablecast_mapper),
        ("PDF Stitching", test_pdf_stitching),
        ("Results File", test_results_file),
        ("Flex Server Mappings", test_flex_server_mappings)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n📊 Debug Test Summary:")
    print("=" * 30)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 