#!/usr/bin/env python3
# PURPOSE: Process existing downloaded PDFs through stitching system
# DEPENDENCIES: pdf_stitcher, pathlib, json
# MODIFICATION NOTES: v1.0 - Process existing PDFs

import json
import os
import sys
from pathlib import Path
import time
from datetime import datetime

# Add scraper directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_stitcher import PDFStitcher


def create_integration_results_from_existing_pdfs():
    """Create integration results from existing downloaded PDFs."""
    print("📄 Processing Existing Downloaded PDFs")
    print("=" * 50)
    
    # Find existing PDFs
    downloads_dir = Path("downloads/birchwood")
    existing_pdfs = []
    
    for pdf_file in downloads_dir.glob("*.pdf"):
        if pdf_file.stat().st_size > 1000:  # Only real PDFs (not empty test files)
            existing_pdfs.append(pdf_file)
    
    print(f"📊 Found {len(existing_pdfs)} real PDFs:")
    for pdf in existing_pdfs:
        size = pdf.stat().st_size
        print(f"   - {pdf.name}: {size} bytes")
    
    # Create integration results structure
    integration_results = {
        'summary': {
            'total_pdfs': len(existing_pdfs),
            'processed': len(existing_pdfs),
            'unmatched': 0,
            'failed': 0,
            'cities_processed': ['Birchwood'],
            'flex_servers_used': ['flex-1'],
            'shows_matched': 0,
            'needs_manual_review': 0
        },
        'processed': [],
        'unmatched': [],
        'failed': [],
        'timestamp': int(time.time())
    }
    
    # Process each PDF
    for pdf_file in existing_pdfs:
        # Extract metadata from filename
        filename = pdf_file.name
        
        # Parse filename to extract date and document type
        if 'Council-Agenda' in filename:
            document_type = 'City Council Agenda'
        elif 'Council-Meeting-Packet' in filename:
            document_type = 'City Council Meeting Packet'
        elif 'Street-Maintenance' in filename:
            document_type = 'Street Maintenance Quote'
        else:
            document_type = 'Unknown Document'
        
        # Extract date from filename (timestamp format)
        timestamp_str = filename.split('_')[0]
        try:
            timestamp = int(timestamp_str)
            meeting_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        except:
            meeting_date = '2025-01-15'  # Default date
        
        # Determine meeting type
        if 'Special' in filename:
            meeting_type = 'SpecialCouncil'
        else:
            meeting_type = 'RegularCouncil'
        
        # Create processed entry
        processed_entry = {
            'city': 'Birchwood',
            'url': f'https://cityofbirchwood.com/wp-content/uploads/{meeting_date}/{filename}',
            'local_path': str(pdf_file),
            'filename': filename,
            'original_filename': filename,
            'document_type': document_type,
            'meeting_date': meeting_date,
            'meeting_type': meeting_type,
            'file_size': pdf_file.stat().st_size
        }
        
        integration_results['processed'].append(processed_entry)
        print(f"   ✅ Processed: {filename} ({document_type})")
    
    # Save integration results
    output_file = 'existing_pdfs_integration_results.json'
    with open(output_file, 'w') as f:
        json.dump(integration_results, f, indent=2)
    
    print(f"\n✅ Saved integration results to: {output_file}")
    return output_file


def process_through_stitching(integration_file):
    """Process the integration results through the stitching system."""
    print(f"\n🔗 Processing through PDF Stitching System")
    print("=" * 50)
    
    stitcher = PDFStitcher()
    stitching_results = stitcher.process_integration_results(integration_file)
    
    if 'error' in stitching_results:
        print(f"❌ Stitching failed: {stitching_results['error']}")
        return False
    
    # Display results
    stitch_summary = stitching_results['summary']
    print(f"\n📄 Stitching Summary:")
    print(f"   Cities processed: {stitch_summary['total_cities']}")
    print(f"   Consolidated PDFs: {stitch_summary['consolidated_pdfs']}")
    print(f"   Single PDFs: {stitch_summary['single_pdfs']}")
    print(f"   Total PDFs processed: {stitch_summary['total_pdfs_processed']}")
    
    # Show consolidated PDFs
    if stitching_results['consolidated_pdfs']:
        print(f"\n🎯 Consolidated PDFs created:")
        for pdf in stitching_results['consolidated_pdfs']:
            print(f"   ✅ {pdf['city']} - {pdf['date']}: {pdf['total_pages']} documents")
            print(f"      📁 {pdf['consolidated_path']}")
    
    # Verify files exist
    print(f"\n🔍 Verifying created files...")
    for pdf in stitching_results['consolidated_pdfs']:
        pdf_path = Path(pdf['consolidated_path'])
        if pdf_path.exists():
            size = pdf_path.stat().st_size
            print(f"   ✅ {pdf_path.name} exists ({size} bytes)")
        else:
            print(f"   ❌ {pdf_path.name} missing")
    
    return True


def main():
    """Main function to process existing PDFs."""
    print("🚀 Processing Existing PDFs Through Integration Pipeline")
    print("=" * 60)
    
    # Step 1: Create integration results from existing PDFs
    integration_file = create_integration_results_from_existing_pdfs()
    
    # Step 2: Process through stitching system
    success = process_through_stitching(integration_file)
    
    if success:
        print(f"\n🎉 Processing Complete!")
        print(f"📊 Results:")
        print(f"   - Integration results: {integration_file}")
        print(f"   - Stitching results: pdf_stitching_results.json")
        print(f"   - Consolidated PDFs: /mnt/flex-1/consolidated_documents/")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Review consolidated PDFs in Flex server")
        print(f"   2. Upload to VOD system when ready")
        print(f"   3. Run full integration with all 512 PDFs")
        
        return 0
    else:
        print(f"\n❌ Processing failed!")
        return 1


if __name__ == "__main__":
    exit(main()) 