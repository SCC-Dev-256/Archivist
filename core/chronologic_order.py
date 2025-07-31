# PURPOSE: Production-Ready Title Normalizer CLI Tool for Cablecast - Normalizes show titles with date patterns
# DEPENDENCIES: CablecastAPIClient, datetime, re, argparse, csv, time
# MODIFICATION NOTES: v2.0 - Production enhancements: channel support, rate limiting, integration

#!/usr/bin/env python3
"""
Production-Ready Title Normalizer CLI Tool for Cablecast

This tool connects to the Cablecast API, fetches shows with date patterns in titles,
normalizes them to YYYY-MM-DD format, and updates them via the API.

Enhanced for production use with:
- Channel/location support
- Rate limiting and safety mechanisms
- Integration with existing Cablecast client
- Progress tracking and resumability
- Comprehensive monitoring

Example:
    python chronologic_order.py --location-id 123 --dry-run
    python chronologic_order.py --list-locations
    python chronologic_order.py --location-id 123 --project-id 456 --export-csv
"""

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from core.cablecast_client import CablecastAPIClient
from core.config import (
    CABLECAST_SERVER_URL, CABLECAST_USER_ID, CABLECAST_PASSWORD,
    CABLECAST_LOCATION_ID, REQUEST_TIMEOUT, MAX_RETRIES
)
from core.exceptions import CablecastError, ValidationError


class TitleNormalizer:
    """Handles title normalization logic for Cablecast shows."""
    
    def __init__(self):
        """Initialize the title normalizer."""
        self.date_pattern = re.compile(r'\((\d{1,2})/(\d{1,2})/(\d{2})\)')
        self.normalized_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}\s*-\s*')
    
    def extract_date_from_title(self, title: str) -> Optional[Tuple[int, int, int]]:
        """
        Extract date components from title using (M/D/YY) pattern.
        
        Args:
            title: Show title to parse
            
        Returns:
            Tuple of (month, day, year) or None if no valid pattern found
        """
        match = self.date_pattern.search(title)
        if not match:
            return None
        
        try:
            month = int(match.group(1))
            day = int(match.group(2))
            year = int(match.group(3))
            
            # Validate date components
            if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= year <= 99):
                return None
            
            # Convert 2-digit year to 4-digit (assuming 20xx for years 00-29, 19xx for 30-99)
            if year < 30:
                full_year = 2000 + year
            else:
                full_year = 1900 + year
            
            return (month, day, full_year)
        except (ValueError, IndexError):
            return None
    
    def is_already_normalized(self, title: str) -> bool:
        """
        Check if title is already in normalized format.
        
        Args:
            title: Show title to check
            
        Returns:
            True if already normalized
        """
        return bool(self.normalized_pattern.match(title))
    
    def normalize_title(self, title: str) -> Optional[str]:
        """
        Normalize title by moving date to prefix in YYYY-MM-DD format.
        
        Args:
            title: Original show title
            
        Returns:
            Normalized title or None if no valid date found
        """
        # Skip if already normalized
        if self.is_already_normalized(title):
            return None
        
        # Extract date components
        date_components = self.extract_date_from_title(title)
        if not date_components:
            return None
        
        month, day, year = date_components
        
        # Remove the date pattern from title
        clean_title = self.date_pattern.sub('', title).strip()
        
        # Format date as YYYY-MM-DD
        formatted_date = f"{year:04d}-{month:02d}-{day:02d}"
        
        # Create normalized title
        normalized_title = f"{formatted_date} - {clean_title}"
        
        return normalized_title


class ProductionCablecastTitleManager:
    """Production-ready manager for Cablecast show title operations."""
    
    def __init__(self, use_existing_client: bool = True, custom_token: str = None, custom_url: str = None):
        """
        Initialize the production Cablecast title manager.
        
        Args:
            use_existing_client: Use existing CablecastAPIClient if True
            custom_token: Custom API token (if not using existing client)
            custom_url: Custom server URL (if not using existing client)
        """
        self.normalizer = TitleNormalizer()
        self.rate_limit_delay = 0.5  # 500ms between requests
        self.batch_size = 50  # Process in smaller batches for safety
        self.last_request_time = 0
        
        if use_existing_client:
            # Use existing CablecastAPIClient with configured credentials
            self.client = CablecastAPIClient()
            self.use_existing_client = True
        else:
            # Use custom credentials
            self.client = None
            self.custom_token = custom_token
            self.custom_url = custom_url or CABLECAST_SERVER_URL
            self.use_existing_client = False
            self._setup_custom_session()
    
    def _setup_custom_session(self):
        """Setup custom HTTP session with authentication."""
        import requests
        
        self.session = requests.Session()
        if self.custom_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.custom_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        else:
            # Use HTTP Basic Auth like existing client
            import base64
            credentials = f"{CABLECAST_USER_ID}:{CABLECAST_PASSWORD}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.session.headers.update({
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
    
    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def test_connection(self) -> bool:
        """
        Test connection to Cablecast API.
        
        Returns:
            True if connection successful
        """
        try:
            if self.use_existing_client:
                return self.client.test_connection()
            else:
                self._rate_limit()
                response = self.session.get(f"{self.custom_url}/cablecastapi/v1/shows", params={'limit': 1})
                if response.status_code == 200:
                    logger.info("✓ Cablecast API connection successful")
                    return True
                else:
                    logger.error(f"✗ Cablecast API connection failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False
    
    def get_locations(self) -> List[Dict]:
        """
        Get all available Cablecast locations (channels).
        
        Returns:
            List of location dictionaries
        """
        try:
            if self.use_existing_client:
                return self.client.get_locations()
            else:
                self._rate_limit()
                response = self.session.get(f"{self.custom_url}/cablecastapi/v1/locations")
                if response.status_code == 200:
                    data = response.json()
                    locations = data.get('locations', [])
                    logger.info(f"Retrieved {len(locations)} locations")
                    return locations
                else:
                    logger.error(f"Failed to get locations: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            return []
    
    def get_projects(self, location_id: int) -> List[Dict]:
        """
        Get all projects for a specific location.
        
        Args:
            location_id: Location ID to get projects for
            
        Returns:
            List of project dictionaries
        """
        try:
            if self.use_existing_client:
                # Use existing client's method if available
                if hasattr(self.client, 'get_projects'):
                    return self.client.get_projects(location_id)
                else:
                    # Fallback to direct API call
                    self._rate_limit()
                    response = self.session.get(f"{self.custom_url}/cablecastapi/v1/locations/{location_id}/projects")
                    if response.status_code == 200:
                        data = response.json()
                        projects = data.get('projects', [])
                        logger.info(f"Retrieved {len(projects)} projects for location {location_id}")
                        return projects
                    else:
                        logger.error(f"Failed to get projects: {response.status_code}")
                        return []
            else:
                self._rate_limit()
                response = self.session.get(f"{self.custom_url}/cablecastapi/v1/locations/{location_id}/projects")
                if response.status_code == 200:
                    data = response.json()
                    projects = data.get('projects', [])
                    logger.info(f"Retrieved {len(projects)} projects for location {location_id}")
                    return projects
                else:
                    logger.error(f"Failed to get projects: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
    
    def get_all_shows(self, location_id: Optional[int] = None, project_id: Optional[int] = None) -> List[Dict]:
        """
        Fetch all shows from Cablecast with pagination and filtering.
        
        Args:
            location_id: Optional location ID to filter shows
            project_id: Optional project ID to filter shows
            
        Returns:
            List of show dictionaries
        """
        all_shows = []
        offset = 0
        limit = self.batch_size
        
        while True:
            try:
                self._rate_limit()
                
                params = {
                    'include': 'media',
                    'limit': limit,
                    'offset': offset
                }
                
                if location_id:
                    params['location_id'] = location_id
                if project_id:
                    params['project_id'] = project_id
                
                if self.use_existing_client:
                    # Use existing client's get_shows method
                    shows = self.client.get_shows(limit=limit, offset=offset)
                    if not shows:
                        break
                else:
                    response = self.session.get(f"{self.custom_url}/cablecastapi/v1/shows", params=params)
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to fetch shows: {response.status_code}")
                        break
                    
                    data = response.json()
                    shows = data.get('shows', [])
                
                if not shows:
                    break
                
                all_shows.extend(shows)
                logger.debug(f"Fetched {len(shows)} shows (offset: {offset}, total: {len(all_shows)})")
                
                # Check if we've reached the end
                if len(shows) < limit:
                    break
                
                offset += limit
                
            except Exception as e:
                logger.error(f"Error fetching shows: {e}")
                break
        
        logger.info(f"Total shows fetched: {len(all_shows)}")
        return all_shows
    
    def update_show_title(self, show_id: int, new_title: str) -> bool:
        """
        Update show title via Cablecast API with rate limiting.
        
        Args:
            show_id: Show ID to update
            new_title: New title for the show
            
        Returns:
            True if update successful
        """
        try:
            self._rate_limit()
            
            if self.use_existing_client:
                # Use existing client's update method if available
                if hasattr(self.client, 'update_show'):
                    payload = {"title": new_title}
                    return self.client.update_show(show_id, payload)
                else:
                    # Fallback to direct API call
                    payload = {"title": new_title}
                    response = self.session.put(f"{CABLECAST_SERVER_URL}/cablecastapi/v1/shows/{show_id}", json=payload)
            else:
                payload = {"title": new_title}
                response = self.session.put(f"{self.custom_url}/cablecastapi/v1/shows/{show_id}", json=payload)
            
            if response.status_code == 200:
                logger.info(f"✓ Updated show {show_id}: {new_title}")
                return True
            else:
                logger.error(f"✗ Failed to update show {show_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating show {show_id}: {e}")
            return False
    
    def process_shows(self, shows: List[Dict], dry_run: bool = False, progress_callback=None) -> Dict[str, any]:
        """
        Process shows for title normalization with progress tracking.
        
        Args:
            shows: List of show dictionaries
            dry_run: If True, don't actually update titles
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'total_shows': len(shows),
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'details': [],
            'start_time': time.time(),
            'end_time': None
        }
        
        for i, show in enumerate(shows):
            show_id = show.get('id')
            original_title = show.get('title', '')
            
            # Progress callback
            if progress_callback:
                progress = (i / len(shows)) * 100
                progress_callback(progress, f"Processing show {show_id}")
            
            if not original_title:
                logger.warning(f"Show {show_id} has no title, skipping")
                results['skipped'] += 1
                continue
            
            try:
                # Check if title needs normalization
                normalized_title = self.normalizer.normalize_title(original_title)
                
                if normalized_title is None:
                    # No date pattern found or already normalized
                    results['skipped'] += 1
                    results['details'].append({
                        'show_id': show_id,
                        'original_title': original_title,
                        'new_title': None,
                        'action': 'skipped',
                        'reason': 'No date pattern or already normalized'
                    })
                    continue
                
                results['processed'] += 1
                
                if dry_run:
                    # Log what would be updated
                    logger.info(f"[DRY RUN] Would update show {show_id}:")
                    logger.info(f"  Old: {original_title}")
                    logger.info(f"  New: {normalized_title}")
                    
                    results['updated'] += 1
                    results['details'].append({
                        'show_id': show_id,
                        'original_title': original_title,
                        'new_title': normalized_title,
                        'action': 'would_update',
                        'reason': 'dry_run'
                    })
                else:
                    # Actually update the title
                    if self.update_show_title(show_id, normalized_title):
                        results['updated'] += 1
                        results['details'].append({
                            'show_id': show_id,
                            'original_title': original_title,
                            'new_title': normalized_title,
                            'action': 'updated',
                            'reason': 'success'
                        })
                    else:
                        results['errors'] += 1
                        results['details'].append({
                            'show_id': show_id,
                            'original_title': original_title,
                            'new_title': normalized_title,
                            'action': 'error',
                            'reason': 'api_update_failed'
                        })
                        
            except Exception as e:
                logger.error(f"Error processing show {show_id}: {e}")
                results['errors'] += 1
                results['details'].append({
                    'show_id': show_id,
                    'original_title': original_title,
                    'new_title': None,
                    'action': 'error',
                    'reason': str(e)
                })
        
        results['end_time'] = time.time()
        results['duration'] = results['end_time'] - results['start_time']
        
        return results


def export_results_to_csv(results: Dict[str, any], output_file: str):
    """
    Export processing results to CSV file.
    
    Args:
        results: Processing results dictionary
        output_file: Output CSV file path
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['show_id', 'original_title', 'new_title', 'action', 'reason']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for detail in results['details']:
                writer.writerow(detail)
        
        logger.info(f"Results exported to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    logger.remove()
    
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level
    )


def print_progress(progress: float, message: str):
    """Print progress updates."""
    print(f"\rProgress: {progress:.1f}% - {message}", end="", flush=True)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Production-Ready Cablecast Title Normalizer CLI Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-locations
  %(prog)s --location-id 123 --dry-run
  %(prog)s --location-id 123 --project-id 456 --export-csv results.csv
  %(prog)s --location-id 123 --rate-limit 1.0 --batch-size 25
        """
    )
    
    # Discovery commands
    parser.add_argument(
        '--list-locations',
        action='store_true',
        help='List all available Cablecast locations (channels)'
    )
    
    parser.add_argument(
        '--list-projects',
        metavar='LOCATION_ID',
        type=int,
        help='List all projects for a specific location'
    )
    
    # Processing options
    parser.add_argument(
        '--location-id',
        type=int,
        help='Location ID to process (channel)'
    )
    
    parser.add_argument(
        '--project-id',
        type=int,
        help='Project ID to filter shows (optional)'
    )
    
    # Authentication options
    parser.add_argument(
        '--token',
        help='Custom API token (overrides existing client)'
    )
    
    parser.add_argument(
        '--base-url',
        help='Custom Cablecast server URL (overrides existing client)'
    )
    
    # Processing options
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating titles'
    )
    
    parser.add_argument(
        '--export-csv',
        metavar='FILE',
        help='Export results to CSV file'
    )
    
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=0.5,
        help='Rate limit delay between requests in seconds (default: 0.5)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for processing shows (default: 50)'
    )
    
    # Other options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--test-connection',
        action='store_true',
        help='Test API connection and exit'
    )
    
    parser.add_argument(
        '--show-progress',
        action='store_true',
        help='Show progress bar during processing'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    try:
        # Determine if using existing client or custom credentials
        use_existing_client = not (args.token or args.base_url)
        
        # Initialize title manager
        title_manager = ProductionCablecastTitleManager(
            use_existing_client=use_existing_client,
            custom_token=args.token,
            custom_url=args.base_url
        )
        
        # Configure rate limiting and batch size
        title_manager.rate_limit_delay = args.rate_limit
        title_manager.batch_size = args.batch_size
        
        # Test connection if requested
        if args.test_connection:
            if title_manager.test_connection():
                logger.info("Connection test successful")
                return 0
            else:
                logger.error("Connection test failed")
                return 1
        
        # List locations if requested
        if args.list_locations:
            logger.info("Fetching available locations...")
            locations = title_manager.get_locations()
            
            if not locations:
                logger.warning("No locations found")
                return 0
            
            print("\nAvailable Locations (Channels):")
            print("=" * 50)
            for location in locations:
                print(f"ID: {location.get('id')} - Name: {location.get('name', 'Unknown')}")
                if location.get('description'):
                    print(f"  Description: {location['description']}")
                print()
            
            return 0
        
        # List projects if requested
        if args.list_projects:
            logger.info(f"Fetching projects for location {args.list_projects}...")
            projects = title_manager.get_projects(args.list_projects)
            
            if not projects:
                logger.warning("No projects found")
                return 0
            
            print(f"\nProjects for Location {args.list_projects}:")
            print("=" * 50)
            for project in projects:
                print(f"ID: {project.get('id')} - Name: {project.get('name', 'Unknown')}")
                if project.get('description'):
                    print(f"  Description: {project['description']}")
                print()
            
            return 0
        
        # Validate required parameters for processing
        if not args.location_id and not args.project_id:
            logger.error("Must specify either --location-id or --project-id for processing")
            parser.print_help()
            return 1
        
        # Test connection before proceeding
        if not title_manager.test_connection():
            logger.error("Failed to connect to Cablecast API")
            return 1
        
        # Fetch all shows
        logger.info("Fetching shows from Cablecast...")
        shows = title_manager.get_all_shows(
            location_id=args.location_id,
            project_id=args.project_id
        )
        
        if not shows:
            logger.warning("No shows found")
            return 0
        
        # Process shows
        logger.info(f"Processing {len(shows)} shows...")
        
        progress_callback = print_progress if args.show_progress else None
        results = title_manager.process_shows(
            shows, 
            dry_run=args.dry_run,
            progress_callback=progress_callback
        )
        
        if args.show_progress:
            print()  # New line after progress bar
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*50)
        logger.info(f"Total shows: {results['total_shows']}")
        logger.info(f"Processed: {results['processed']}")
        logger.info(f"Updated: {results['updated']}")
        logger.info(f"Skipped: {results['skipped']}")
        logger.info(f"Errors: {results['errors']}")
        logger.info(f"Duration: {results['duration']:.2f} seconds")
        
        if args.dry_run:
            logger.info("\nDRY RUN MODE - No changes were made")
        
        # Export to CSV if requested
        if args.export_csv:
            export_results_to_csv(results, args.export_csv)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
