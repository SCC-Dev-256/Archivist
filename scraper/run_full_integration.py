#!/usr/bin/env python3
# PURPOSE: Complete PDF to Flex Server integration with VOD consolidation
# DEPENDENCIES: pdf_to_flex_integration, pdf_stitcher, json
# MODIFICATION NOTES: v1.0 - Complete integration workflow

import json
import os
import sys
from pathlib import Path
import time

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_to_flex_integration import PDFToFlexIntegration
from pdf_stitcher import PDFStitcher


def run_full_integration(results_file: str = None):
    """Run the complete PDF integration workflow."""
    print("🚀 Complete PDF to Flex Server Integration")
    print("=" * 60)
    
    # Step 1: Find results file
    if not results_file:
        possible_files = [
            "../clean_final_results.json",
            "../civicengage_enhanced_results.json",
            "../comprehensive_results.json",
            "clean_final_results.json",
            "civicengage_enhanced_results.json"
        ]
        
        for file in possible_files:
            if os.path.exists(file):
                results_file = file
                break
    
    if not results_file or not os.path.exists(results_file):
        print("❌ No results file found. Please run the scraper first.")
        return False
    
    print(f"📄 Using results file: {results_file}")
    
    # Step 2: Initialize integration system
    print("\n🔧 Initializing integration system...")
    integration = PDFToFlexIntegration()
    
    # Step 2.5: Check API health
    print("\n🏥 Checking API health...")
    health_check = integration.check_api_health()
    if not health_check['success']:
        print(f"❌ API health check failed: {health_check['error']}")
        print("   Please ensure the Archivist API is running on port 8080")
        return False
    else:
        print(f"✅ API is healthy (response time: {health_check['response_time']:.2f}s)")
    
    # Step 3: Process PDFs and integrate with Flex servers
    print("\n📥 Processing PDFs and uploading to Flex servers...")
    integration_results = integration.process_scraped_results(results_file)
    
    if 'error' in integration_results:
        print(f"❌ Integration failed: {integration_results['error']}")
        return False
    
    # Step 4: Display integration summary
    summary = integration_results['summary']
    print(f"\n📊 Integration Summary:")
    print(f"   Total PDFs: {summary['total_pdfs']}")
    print(f"   Successfully processed: {summary['processed']}")
    print(f"   Unmatched (need manual review): {summary['unmatched']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Shows matched: {summary['shows_matched']}")
    print(f"   Cities: {', '.join(summary['cities_processed'])}")
    
    # Step 5: PDF Stitching and Consolidation
    print("\n🔗 Stitching PDFs for VOD consolidation...")
    stitcher = PDFStitcher()
    stitching_results = stitcher.process_integration_results("pdf_integration_results.json")
    
    if 'error' in stitching_results:
        print(f"❌ Stitching failed: {stitching_results['error']}")
        return False
    
    # Step 6: Display stitching summary
    stitch_summary = stitching_results['summary']
    print(f"\n📄 Stitching Summary:")
    print(f"   Cities processed: {stitch_summary['total_cities']}")
    print(f"   Consolidated PDFs: {stitch_summary['consolidated_pdfs']}")
    print(f"   Single PDFs: {stitch_summary['single_pdfs']}")
    print(f"   Total PDFs processed: {stitch_summary['total_pdfs_processed']}")
    
    # Step 7: Show detailed results
    if stitching_results['consolidated_pdfs']:
        print(f"\n🎯 Consolidated PDFs created:")
        for pdf in stitching_results['consolidated_pdfs']:
            print(f"   ✅ {pdf['city']} - {pdf['date']}: {pdf['total_pages']} documents")
            print(f"      📁 {pdf['consolidated_path']}")
    
    if integration_results['unmatched']:
        print(f"\n⚠️  PDFs needing manual review:")
        for pdf in integration_results['unmatched'][:5]:  # Show first 5
            print(f"   📄 {pdf['city']} - {pdf.get('meeting_date', 'No date')}: {pdf.get('document_type', 'Unknown')}")
        if len(integration_results['unmatched']) > 5:
            print(f"   ... and {len(integration_results['unmatched']) - 5} more")
    
    # Step 8: Final summary
    print(f"\n🎉 Integration Complete!")
    print(f"   📊 Total PDFs processed: {summary['total_pdfs']}")
    print(f"   🔗 Shows matched: {summary['shows_matched']}")
    print(f"   📄 Consolidated documents: {stitch_summary['consolidated_pdfs']}")
    print(f"   ⚠️  Manual review needed: {summary['unmatched']}")
    
    print(f"\n📁 Results saved to:")
    print(f"   - pdf_integration_results.json")
    print(f"   - pdf_stitching_results.json")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Review unmatched PDFs for manual show linking")
    print(f"   2. Check consolidated PDFs in Flex server directories")
    print(f"   3. Verify VOD entries in Cablecast system")
    print(f"   4. Test streaming of consolidated documents with VOD content")
    
    return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run complete PDF integration workflow')
    parser.add_argument('--results-file', help='Path to results JSON file')
    parser.add_argument('--test', action='store_true', help='Run in test mode with limited PDFs')
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Running in test mode...")
        # Create a small test file
        test_file = "test_integration_sample.json"
        if not os.path.exists(test_file):
            print("❌ Test file not found. Please create a test sample first.")
            return False
    
    success = run_full_integration(args.results_file)
    
    if success:
        print("\n✅ Integration workflow completed successfully!")
        return 0
    else:
        print("\n❌ Integration workflow failed!")
        return 1


if __name__ == "__main__":
    exit(main()) 