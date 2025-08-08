# PURPOSE: PDF stitching utility for consolidating city documents by date
# DEPENDENCIES: pypdf, pathlib, json
# MODIFICATION NOTES: v1.0 - Initial implementation for VOD document consolidation

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import logging

try:
    from pypdf import PdfWriter, PdfReader
    PDFMERGING_AVAILABLE = True
except ImportError:
    print("pypdf not found. Attempting to install...")
    import subprocess
    import sys
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pypdf'], 
                      check=True, capture_output=True)
        from pypdf import PdfWriter, PdfReader
        PDFMERGING_AVAILABLE = True
        print("pypdf installed successfully")
    except (subprocess.CalledProcessError, ImportError) as e:
        print(f"Failed to install pypdf: {e}")
        print("PDF stitching will be disabled")
        PDFMERGING_AVAILABLE = False
        PdfMerger = None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFStitcher:
    """Utility for stitching PDFs by city and date for VOD consolidation."""
    
    def __init__(self, flex_server_base: str = "/mnt"):
        self.flex_server_base = Path(flex_server_base)
        
    def group_pdfs_by_city_and_date(self, integration_results: Dict[str, Any]) -> Dict[str, Dict[str, List[Dict]]]:
        """Group processed PDFs by city and date for stitching."""
        grouped = defaultdict(lambda: defaultdict(list))
        
        # Process both matched and unmatched PDFs
        all_pdfs = integration_results.get('processed', []) + integration_results.get('unmatched', [])
        
        for pdf in all_pdfs:
            city = pdf.get('city', 'Unknown')
            date = pdf.get('meeting_date')
            
            if date:
                grouped[city][date].append(pdf)
            else:
                # PDFs without dates go to 'unknown_date' group
                grouped[city]['unknown_date'].append(pdf)
        
        return dict(grouped)
    
    def stitch_city_date_pdfs(self, city: str, date: str, pdfs: List[Dict], 
                            output_dir: Path) -> Optional[Path]:
        """Stitch multiple PDFs for a city/date into a single consolidated PDF."""
        try:
            if not PDFMERGING_AVAILABLE:
                logger.error("PDF stitching not available - PyPDF2 not installed")
                return None
                
            if len(pdfs) == 1:
                # Single PDF, no stitching needed
                logger.info(f"Single PDF for {city} on {date}, no stitching needed")
                return None
            
            logger.info(f"Stitching {len(pdfs)} PDFs for {city} on {date}")
            
            # Sort PDFs by document type for logical order
            document_order = ['Agenda', 'Packet', 'Minutes', 'Other']
            sorted_pdfs = []
            
            for doc_type in document_order:
                for pdf in pdfs:
                    if doc_type.lower() in pdf.get('document_type', '').lower():
                        sorted_pdfs.append(pdf)
            
            # Add any remaining PDFs
            for pdf in pdfs:
                if pdf not in sorted_pdfs:
                    sorted_pdfs.append(pdf)
            
            # Create output filename
            output_filename = f"{city}_{date}_ConsolidatedDocuments.pdf"
            output_path = output_dir / output_filename
            
            # Stitch PDFs using PdfWriter (pypdf>=5)
            writer = PdfWriter()

            for pdf in sorted_pdfs:
                pdf_path = Path(pdf.get('local_path', ''))
                if not pdf_path.exists():
                    logger.warning(f"  PDF not found: {pdf_path}")
                    continue
                try:
                    # Prefer fast append if available, else copy pages
                    append = getattr(writer, 'append', None)
                    if append is not None:
                        append(str(pdf_path))
                    else:
                        reader = PdfReader(str(pdf_path))
                        for page in reader.pages:
                            writer.add_page(page)
                    logger.info(f"  Added: {pdf.get('document_type', 'Unknown')} - {pdf_path.name}")
                except Exception as e:
                    logger.error(f"  Error adding {pdf_path}: {e}")

            # Write consolidated PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info(f"Created consolidated PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error stitching PDFs for {city} on {date}: {e}")
            return None
    
    def process_integration_results(self, results_file: str = "pdf_integration_results.json") -> Dict[str, Any]:
        """Process integration results and create consolidated PDFs."""
        try:
            # Load integration results
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            logger.info("Processing integration results for PDF stitching...")
            
            # Group PDFs by city and date
            grouped_pdfs = self.group_pdfs_by_city_and_date(results)
            
            # Process each city
            stitching_results = {
                'consolidated_pdfs': [],
                'single_pdfs': [],
                'failed_stitches': [],
                'summary': {}
            }
            
            for city, date_groups in grouped_pdfs.items():
                logger.info(f"Processing {city}: {len(date_groups)} date groups")
                
                for date, pdfs in date_groups.items():
                    if date == 'unknown_date':
                        # Handle PDFs without dates
                        for pdf in pdfs:
                            stitching_results['single_pdfs'].append({
                                'city': city,
                                'date': 'unknown',
                                'pdf': pdf,
                                'reason': 'No date available'
                            })
                        continue
                    
                    # Create output directory for this city
                    city_output_dir = self.flex_server_base / f"flex-{self._get_flex_server_for_city(city)}" / "consolidated_documents" / city.lower().replace(' ', '_')
                    city_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Stitch PDFs for this date
                    consolidated_path = self.stitch_city_date_pdfs(city, date, pdfs, city_output_dir)
                    
                    if consolidated_path:
                        # Successfully created consolidated PDF
                        stitching_results['consolidated_pdfs'].append({
                            'city': city,
                            'date': date,
                            'consolidated_path': str(consolidated_path),
                            'source_pdfs': [pdf.get('file_id') for pdf in pdfs],
                            'document_types': [pdf.get('document_type') for pdf in pdfs],
                            'total_pages': len(pdfs)
                        })
                        
                        logger.info(f"  ✅ Consolidated {len(pdfs)} PDFs for {city} on {date}")
                    else:
                        # Single PDF or stitching failed
                        if len(pdfs) == 1:
                            stitching_results['single_pdfs'].append({
                                'city': city,
                                'date': date,
                                'pdf': pdfs[0],
                                'reason': 'Single PDF only'
                            })
                        else:
                            stitching_results['failed_stitches'].append({
                                'city': city,
                                'date': date,
                                'pdfs': pdfs,
                                'reason': 'Stitching failed'
                            })
            
            # Generate summary
            summary = {
                'total_cities': len(grouped_pdfs),
                'consolidated_pdfs': len(stitching_results['consolidated_pdfs']),
                'single_pdfs': len(stitching_results['single_pdfs']),
                'failed_stitches': len(stitching_results['failed_stitches']),
                'total_pdfs_processed': sum(len(pdfs) for date_groups in grouped_pdfs.values() for pdfs in date_groups.values())
            }
            
            stitching_results['summary'] = summary
            
            # Save stitching results
            with open('pdf_stitching_results.json', 'w') as f:
                json.dump(stitching_results, f, indent=2)
            
            logger.info(f"PDF stitching complete. Summary: {summary}")
            return stitching_results
            
        except Exception as e:
            logger.error(f"Error processing integration results: {e}")
            return {'error': str(e)}
    
    def _get_flex_server_for_city(self, city: str) -> str:
        """Get Flex server number for a city."""
        city_mapping = {
            'Birchwood': '1',
            'Dellwood': '2',
            'Grant': '2',
            'Willernie': '2',
            'Lake Elmo': '3',
            'Mahtomedi': '4',
            'Oakdale': '7',
            'White Bear Lake': '8',
            'White Bear Township': '9'
        }
        return city_mapping.get(city, '1')
    
    def create_vod_consolidated_entry(self, consolidated_pdf: Dict, api_base_url: str = "http://localhost:8080") -> Dict[str, Any]:
        """Create VOD entry for consolidated PDF."""
        try:
            import requests
            
            vod_data = {
                'file_path': consolidated_pdf['consolidated_path'],
                'title': f"{consolidated_pdf['city']} - {consolidated_pdf['date']} - Consolidated Documents",
                'description': f"Consolidated city documents for {consolidated_pdf['city']} on {consolidated_pdf['date']}. Includes: {', '.join(consolidated_pdf['document_types'])}",
                'category': 'Consolidated City Documents',
                'attachment_type': 'consolidated_pdf',
                'source_pdfs': consolidated_pdf['source_pdfs']
            }
            
            vod_url = f"{api_base_url}/api/vod/create"
            response = requests.post(vod_url, json=vod_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'vod_id': result.get('vod_id'),
                    'consolidated_pdf': consolidated_pdf
                }
            else:
                return {
                    'success': False,
                    'error': f'VOD creation failed: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """Main function for PDF stitching."""
    print("PDF Stitching Utility")
    print("=" * 40)
    
    stitcher = PDFStitcher()
    
    # Process integration results
    results = stitcher.process_integration_results()
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    # Display summary
    summary = results['summary']
    print(f"\n📊 Stitching Summary:")
    print(f"   Cities processed: {summary['total_cities']}")
    print(f"   Consolidated PDFs: {summary['consolidated_pdfs']}")
    print(f"   Single PDFs: {summary['single_pdfs']}")
    print(f"   Failed stitches: {summary['failed_stitches']}")
    print(f"   Total PDFs: {summary['total_pdfs_processed']}")
    
    # Show consolidated PDFs
    if results['consolidated_pdfs']:
        print(f"\n📄 Consolidated PDFs created:")
        for pdf in results['consolidated_pdfs']:
            print(f"   {pdf['city']} - {pdf['date']}: {pdf['total_pages']} documents")
    
    # Show single PDFs
    if results['single_pdfs']:
        print(f"\n📄 Single PDFs (no consolidation needed):")
        for pdf in results['single_pdfs'][:5]:  # Show first 5
            print(f"   {pdf['city']} - {pdf['date']}: {pdf['pdf'].get('document_type', 'Unknown')}")
    
    print(f"\n📁 Results saved to: pdf_stitching_results.json")


if __name__ == "__main__":
    main() 