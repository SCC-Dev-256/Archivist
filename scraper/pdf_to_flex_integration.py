# PURPOSE: Integration system to pipe scraped PDFs into Flex servers with VOD labeling
# DEPENDENCIES: requests, pathlib, json, urllib.parse, os
# MODIFICATION NOTES: v1.0 - Initial implementation for Minnesota city PDF integration

from __future__ import annotations

import json
import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CityMapping:
    """Mapping of cities to their Flex server locations."""
    city: str
    flex_server: str
    mount_path: str
    description: str


class PDFToFlexIntegration:
    """Integration system to pipe scraped PDFs into Flex servers with VOD labeling."""
    
    def __init__(self, api_base_url: str = "http://localhost:8080", api_key: Optional[str] = None):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # Configure session for better reliability
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'Archivist-PDF-Integration/1.0',
            'Content-Type': 'application/json'
        })
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        
        # City to Flex server mapping
        self.city_mappings = [
            CityMapping("Birchwood", "flex-1", "/mnt/flex-1", "Birchwood City Council and community content"),
            CityMapping("Dellwood", "flex-2", "/mnt/flex-2", "Dellwood, Grant, and Willernie combined storage"),
            CityMapping("Grant", "flex-2", "/mnt/flex-2", "Dellwood, Grant, and Willernie combined storage"),
            CityMapping("Willernie", "flex-2", "/mnt/flex-2", "Dellwood, Grant, and Willernie combined storage"),
            CityMapping("Lake Elmo", "flex-3", "/mnt/flex-3", "Lake Elmo City Council and community content"),
            CityMapping("Mahtomedi", "flex-4", "/mnt/flex-4", "Mahtomedi City Council and community content"),
            # flex-5 and flex-6 are not allocated
            CityMapping("Oakdale", "flex-7", "/mnt/flex-7", "Oakdale City Council and community content"),
            CityMapping("White Bear Lake", "flex-8", "/mnt/flex-8", "White Bear Lake City Council and community content"),
            CityMapping("White Bear Township", "flex-9", "/mnt/flex-9", "White Bear Township Council and community content"),
        ]
        
        # Document type mapping for labeling
        self.document_types = {
            'agenda': 'City Council Agenda',
            'minutes': 'City Council Minutes', 
            'packet': 'Council Meeting Packet',
            'meeting': 'Council Meeting',
            'council': 'City Council',
            'resolution': 'City Resolution',
            'ordinance': 'City Ordinance'
        }

    def get_city_mapping(self, city: str) -> Optional[CityMapping]:
        """Get Flex server mapping for a city."""
        for mapping in self.city_mappings:
            if mapping.city.lower() == city.lower():
                return mapping
        return None

    def download_pdf(self, url: str, output_dir: Path) -> Optional[Path]:
        """Download a PDF file from URL."""
        try:
            logger.info(f"Downloading PDF: {url}")
            
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # Add timestamp to avoid conflicts
            timestamp = int(time.time())
            filename = f"{timestamp}_{filename}"
            
            output_path = output_dir / filename
            
            # Download the file
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded PDF to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF {url}: {e}")
            return None

    def upload_to_flex_server(self, pdf_path: Path, city: str, source_url: str) -> Dict[str, Any]:
        """Upload PDF to appropriate Flex server using the API."""
        try:
            # Get city mapping
            mapping = self.get_city_mapping(city)
            if not mapping:
                return {
                    'success': False,
                    'error': f'No Flex server mapping found for city: {city}'
                }
            
            logger.info(f"Uploading PDF for {city} to {mapping.flex_server}")
            
            # Prepare file for upload
            with open(pdf_path, 'rb') as f:
                files = {'file': (pdf_path.name, f, 'application/pdf')}
                
                # Prepare metadata
                metadata = {
                    'city': city,
                    'source_url': source_url,
                    'document_type': self._detect_document_type(pdf_path.name, source_url),
                    'upload_timestamp': int(time.time()),
                    'flex_server': mapping.flex_server
                }
                
                data = {'metadata': json.dumps(metadata)}
                
                # Upload to API endpoint
                upload_url = f"{self.api_base_url}/api/digitalfiles/upload"
                response = self.session.post(upload_url, files=files, data=data, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Successfully uploaded PDF to {mapping.flex_server}")
                    return {
                        'success': True,
                        'file_id': result.get('file_id'),
                        'flex_server': mapping.flex_server,
                        'path': result.get('path'),
                        'metadata': metadata
                    }
                else:
                    logger.error(f"Upload failed: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'Upload failed: {response.status_code}',
                        'response': response.text
                    }
                    
        except Exception as e:
            logger.error(f"Error uploading PDF to Flex server: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _detect_document_type(self, filename: str, source_url: str) -> str:
        """Detect document type from filename and URL."""
        text_to_check = f"{filename.lower()} {source_url.lower()}"
        
        for keyword, doc_type in self.document_types.items():
            if keyword in text_to_check:
                return doc_type
        
        return "City Document"

    def _extract_meeting_date(self, filename: str, source_url: str) -> Optional[str]:
        """Extract meeting date from filename or URL."""
        import re
        from datetime import datetime
        
        # Date patterns to look for
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
            r'(\d{8})',              # YYYYMMDD
            r'(\d{4}_\d{2}_\d{2})',  # YYYY_MM_DD
            r'(\d{2}_\d{2}_\d{4})',  # MM_DD_YYYY
        ]
        
        # Check filename first
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                try:
                    # Parse and standardize the date
                    if len(date_str) == 8 and '_' not in date_str:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                    elif '-' in date_str:
                        if len(date_str.split('-')[0]) == 4:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                    elif '_' in date_str:
                        if len(date_str.split('_')[0]) == 4:
                            date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%m_%d_%Y')
                    else:
                        continue
                    
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # Check URL if no date found in filename
        for pattern in date_patterns:
            match = re.search(pattern, source_url)
            if match:
                date_str = match.group(1)
                try:
                    # Same parsing logic as above
                    if len(date_str) == 8 and '_' not in date_str:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                    elif '-' in date_str:
                        if len(date_str.split('-')[0]) == 4:
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                    elif '_' in date_str:
                        if len(date_str.split('_')[0]) == 4:
                            date_obj = datetime.strptime(date_str, '%Y_%m_%d')
                        else:
                            date_obj = datetime.strptime(date_str, '%m_%d_%Y')
                    else:
                        continue
                    
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return None

    def _detect_meeting_type(self, filename: str, source_url: str) -> str:
        """Detect meeting type from filename and URL."""
        text_to_check = f"{filename.lower()} {source_url.lower()}"
        
        meeting_types = {
            'special': 'SpecialCouncil',
            'regular': 'RegularCouncil',
            'planning': 'PlanningCommission',
            'council': 'CityCouncil',
            'commission': 'CityCommission',
            'board': 'CityBoard',
            'committee': 'CityCommittee'
        }
        
        for keyword, meeting_type in meeting_types.items():
            if keyword in text_to_check:
                return meeting_type
        
        return "CityCouncil"  # Default

    def _generate_standardized_filename(self, city: str, date: str, document_type: str, meeting_type: str) -> str:
        """Generate standardized filename for PDF."""
        # Clean up document type for filename
        doc_type_clean = document_type.replace(' ', '').replace('City', '')
        
        # Clean up meeting type
        meeting_clean = meeting_type.replace('City', '')
        
        return f"{city}_{date}_{doc_type_clean}_{meeting_clean}.pdf"

    def find_matching_cablecast_show(self, city: str, date: str, document_type: str) -> Optional[Dict]:
        """Find matching Cablecast show based on city and date (same day only)."""
        try:
            # Add parent directory to path for core imports
            import sys
            import os
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Use the existing Cablecast show mapper
            from core.cablecast_show_mapper import CablecastShowMapper
            
            mapper = CablecastShowMapper()
            
            # Create a mock video path for matching
            mock_video_path = f"/mnt/flex-1/{city}_{date}_meeting.mp4"
            
            # Get show suggestions
            suggestions = mapper.get_show_suggestions(mock_video_path, limit=10)
            
            # Filter for exact date matches only
            exact_matches = []
            for suggestion in suggestions:
                if suggestion.get('date') == date:
                    exact_matches.append(suggestion)
            
            if exact_matches:
                # Return the best match (highest similarity score)
                best_match = max(exact_matches, key=lambda x: x['similarity_score'])
                return {
                    'show_id': best_match['show_id'],
                    'title': best_match['title'],
                    'date': best_match['date'],
                    'similarity_score': best_match['similarity_score']
                }
            
            return None
            
        except ImportError as e:
            logger.warning(f"Cablecast show mapper not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error finding matching Cablecast show: {e}")
            return None

    def create_vod_entry(self, file_id: str, city: str, document_type: str, show_match: Optional[Dict] = None) -> Dict[str, Any]:
        """Create VOD entry for the uploaded PDF as sidecar file."""
        try:
            logger.info(f"Creating VOD entry for file {file_id}")
            
            vod_data = {
                'file_id': file_id,
                'title': f"{city} - {document_type}",
                'description': f"City Council document from {city}",
                'category': 'City Council Documents',
                'auto_transcribe': False,  # No captioning needed
                'quality': 1,
                'attachment_type': 'sidecar',  # Mark as sidecar file
                'show_id': show_match.get('show_id') if show_match else None
            }
            
            vod_url = f"{self.api_base_url}/api/vod/create"
            response = self.session.post(vod_url, json=vod_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Created VOD entry: {result.get('vod_id')}")
                return {
                    'success': True,
                    'vod_id': result.get('vod_id'),
                    'title': vod_data['title'],
                    'show_id': show_match.get('show_id') if show_match else None
                }
            else:
                logger.error(f"VOD creation failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'VOD creation failed: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error creating VOD entry: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def process_scraped_results(self, results_file: str, download_dir: str = "downloads") -> Dict[str, Any]:
        """Process scraped PDF results and integrate with Flex servers."""
        try:
            # Load scraped results
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            logger.info(f"Processing {len(results)} scraped PDFs")
            
            # Create download directory
            download_path = Path(download_dir)
            download_path.mkdir(exist_ok=True)
            
            # Process each PDF
            processed = []
            failed = []
            unmatched = []  # PDFs without matching shows
            
            for item in results:
                try:
                    url = item['url']
                    city = item['city']
                    source = item.get('source', url)
                    
                    logger.info(f"Processing PDF for {city}: {url}")
                    
                    # Download PDF
                    pdf_path = self.download_pdf(url, download_path)
                    if not pdf_path:
                        failed.append({
                            'url': url,
                            'city': city,
                            'error': 'Download failed'
                        })
                        continue
                    
                    # Extract metadata
                    date = self._extract_meeting_date(pdf_path.name, source)
                    document_type = self._detect_document_type(pdf_path.name, source)
                    meeting_type = self._detect_meeting_type(pdf_path.name, source)
                    
                    # Generate standardized filename
                    if date:
                        standardized_name = self._generate_standardized_filename(
                            city, date, document_type, meeting_type
                        )
                    else:
                        standardized_name = pdf_path.name
                    
                    # Find matching Cablecast show (same day only)
                    show_match = None
                    if date:
                        show_match = self.find_matching_cablecast_show(city, date, document_type)
                    
                    # Upload to Flex server
                    upload_result = self.upload_to_flex_server(pdf_path, city, source)
                    if not upload_result['success']:
                        failed.append({
                            'url': url,
                            'city': city,
                            'error': upload_result['error']
                        })
                        continue
                    
                    # Create VOD entry as sidecar file
                    vod_result = self.create_vod_entry(
                        upload_result['file_id'], 
                        city, 
                        document_type,
                        show_match
                    )
                    
                    processed_item = {
                        'url': url,
                        'city': city,
                        'file_id': upload_result['file_id'],
                        'flex_server': upload_result['flex_server'],
                        'document_type': document_type,
                        'meeting_type': meeting_type,
                        'meeting_date': date,
                        'standardized_name': standardized_name,
                        'vod_id': vod_result.get('vod_id') if vod_result['success'] else None,
                        'show_id': show_match.get('show_id') if show_match else None,
                        'show_match_score': show_match.get('similarity_score') if show_match else None,
                        'local_path': str(pdf_path)
                    }
                    
                    if show_match:
                        processed.append(processed_item)
                        logger.info(f"Successfully processed PDF for {city} (matched to show {show_match['show_id']})")
                    else:
                        unmatched.append(processed_item)
                        logger.info(f"Processed PDF for {city} (no matching show found - manual review needed)")
                    
                except Exception as e:
                    logger.error(f"Error processing PDF {item.get('url', 'unknown')}: {e}")
                    failed.append({
                        'url': item.get('url', 'unknown'),
                        'city': item.get('city', 'unknown'),
                        'error': str(e)
                    })
            
            # Generate summary
            summary = {
                'total_pdfs': len(results),
                'processed': len(processed),
                'unmatched': len(unmatched),
                'failed': len(failed),
                'cities_processed': list(set(p['city'] for p in processed + unmatched)),
                'flex_servers_used': list(set(p['flex_server'] for p in processed + unmatched)),
                'shows_matched': len([p for p in processed if p.get('show_id')]),
                'needs_manual_review': len(unmatched)
            }
            
            # Save processing results
            results_data = {
                'summary': summary,
                'processed': processed,
                'unmatched': unmatched,  # PDFs that need manual show matching
                'failed': failed,
                'timestamp': int(time.time())
            }
            
            with open('pdf_integration_results.json', 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"Integration complete. Summary: {summary}")
            return results_data
            
        except Exception as e:
            logger.error(f"Error processing scraped results: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_flex_server_status(self) -> Dict[str, Any]:
        """Get status of all Flex servers."""
        try:
            status_url = f"{self.api_base_url}/api/mount-points"
            response = self.session.get(status_url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Failed to get mount status: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_city_documents(self, city: str) -> Dict[str, Any]:
        """List all documents for a specific city."""
        try:
            mapping = self.get_city_mapping(city)
            if not mapping:
                return {
                    'success': False,
                    'error': f'No mapping found for city: {city}'
                }
            
            browse_url = f"{self.api_base_url}/api/browse"
            params = {'path': mapping.mount_path}
            response = self.session.get(browse_url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'Failed to browse {mapping.mount_path}: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def check_api_health(self) -> Dict[str, Any]:
        """Check if the API is accessible and healthy."""
        try:
            # Try to connect to the API using digitalfiles endpoint
            health_url = f"{self.api_base_url}/api/digitalfiles"
            response = self.session.get(health_url, timeout=10)
            
            if response.status_code in [200, 404, 405]:  # Any response means API is running
                return {
                    'success': True,
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'status': f'HTTP {response.status_code}',
                    'error': response.text
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'status': 'connection_error',
                'error': f'Cannot connect to {self.api_base_url}'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'status': 'timeout',
                'error': 'API request timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }


def main():
    """Main integration function."""
    print("PDF to Flex Server Integration")
    print("=" * 50)
    
    # Initialize integration
    integration = PDFToFlexIntegration()
    
    # Check Flex server status
    print("\nChecking Flex server status...")
    status = integration.get_flex_server_status()
    if status.get('success'):
        print("✅ Flex servers are accessible")
    else:
        print(f"❌ Flex server error: {status.get('error')}")
        return
    
    # Process scraped results
    results_file = "civicengage_enhanced_results.json"  # or your results file
    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        print("Please run the scraper first to generate results.")
        return
    
    print(f"\nProcessing scraped results from: {results_file}")
    results = integration.process_scraped_results(results_file)
    
    # Display summary
    if 'summary' in results:
        summary = results['summary']
        print(f"\n📊 Integration Summary:")
        print(f"   Total PDFs: {summary['total_pdfs']}")
        print(f"   Processed: {summary['processed']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Cities: {', '.join(summary['cities_processed'])}")
        print(f"   Flex Servers: {', '.join(summary['flex_servers_used'])}")
        
        if summary['failed'] > 0:
            print(f"\n❌ Failed items: {summary['failed']}")
            for failure in results['failed'][:5]:  # Show first 5 failures
                print(f"   - {failure['city']}: {failure['error']}")
    
    print(f"\n📁 Results saved to: pdf_integration_results.json")


if __name__ == "__main__":
    main() 