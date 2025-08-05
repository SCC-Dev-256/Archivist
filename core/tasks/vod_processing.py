from __future__ import annotations

"""VOD Processing Tasks for Archivist application.

This module provides comprehensive VOD processing capabilities including:
- VOD discovery and monitoring
- Direct VOD URL access and downloading
- Automatic captioning with SCC files
- Video retranscoding with embedded captions
- Quality assurance and validation
- Member city-specific processing

Tasks:
- process_recent_vods: Process most recent VODs for each member city
- download_vod_content: Download VOD content from direct URLs
- caption_vod: Generate captions for a specific VOD
- retranscode_vod: Retranscode video with embedded captions
- validate_vod_quality: Quality assurance for processed VODs
"""

import os
import subprocess
import tempfile
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from urllib.parse import urlparse, urljoin

from loguru import logger
from core.config import MEMBER_CITIES, OUTPUT_DIR
from core.cablecast_client import CablecastAPIClient
from core.services import TranscriptionService

try:
    from core.utils.alerts import send_alert
except ImportError:
    def send_alert(level: str, message: str, **kwargs):
        logger.warning(f"[ALERT-{level.upper()}] {message} | Extra: {kwargs}")

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import errno
from core.monitoring.metrics import get_metrics_collector, track_vod_processing, track_api_call

# Import celery_app after other imports to avoid circular dependency
# Import celery_app after other imports to avoid circular dependency
from core.tasks import celery_app

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def extract_vod_url_from_cablecast(vod_data: Dict) -> Optional[str]:
    """Extract direct VOD URL from Cablecast VOD data."""
    # Try different possible URL fields
    possible_urls = [
        vod_data.get('url'),
        vod_data.get('stream_url'),
        vod_data.get('direct_url'),
        vod_data.get('vod_url'),
        vod_data.get('file_url')
    ]
    
    for url in possible_urls:
        if url and isinstance(url, str):
            # Check if it's a direct video URL
            if url.endswith(('.mp4', '.mov', '.avi', '.mkv')) or 'vod.mp4' in url:
                return url
    
    # If no direct URL found, try to construct from VOD ID and title
    vod_id = vod_data.get('id')
    title = vod_data.get('title', '').replace(' ', '-').replace('/', '-')
    
    if vod_id and title:
        # Construct URL based on the pattern from the example
        # https://reflect-vod-scctv.cablecast.tv/store-12/21438-WBT-Board-Meeting-42125-v1/vod.mp4
        base_url = "https://reflect-vod-scctv.cablecast.tv"
        store_path = f"store-12/{vod_id}-{title}/vod.mp4"
        constructed_url = f"{base_url}/{store_path}"
        
        logger.info(f"Constructed VOD URL: {constructed_url}")
        return constructed_url
    
    return None

# Replace download_vod_content with retry logic
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
    reraise=True
)
def download_vod_content(vod_url: str, output_path: str, timeout: int = 1800) -> bool:
    """Download VOD content from direct URL with retries."""
    import time
    metrics = get_metrics_collector()
    start_time = time.time()
    
    logger.info(f"Downloading VOD content from: {vod_url}")
    metrics.increment("vod_download_total")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        response = requests.get(vod_url, stream=True, timeout=timeout)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if downloaded_size % (10 * 1024 * 1024) == 0:
                        progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                        logger.info(f"Download progress: {progress:.1f}% ({downloaded_size / (1024*1024):.1f}MB)")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            duration = time.time() - start_time
            metrics.increment("vod_download_success")
            metrics.timer("download_duration", duration)
            logger.info(f"VOD content downloaded successfully: {output_path}")
            return True
        else:
            metrics.increment("vod_download_failed")
            logger.error(f"Download verification failed: {output_path}")
            return False
    except Exception as e:
        duration = time.time() - start_time
        metrics.increment("vod_download_failed")
        metrics.timer("download_duration", duration)
        logger.error(f"Error downloading VOD content: {e}")
        raise  # Let tenacity handle the retry

def get_vod_file_path(vod_data: Dict) -> Optional[str]:
    """Get VOD file path from local mounted drives or download if necessary.
    
    This function prioritizes local file access from mounted flex servers
    over downloading from Cablecast API URLs.
    """
    vod_id = vod_data.get('id', 'unknown')
    
    # First, check for local file paths on mounted drives
    local_paths = [
        vod_data.get('file_path'),
        vod_data.get('local_path'),
        vod_data.get('mount_path'),
        vod_data.get('flex_path')
    ]
    
    # Add common flex server paths
    for city_id, city_config in MEMBER_CITIES.items():
        mount_path = city_config.get('mount_path', f'/mnt/{city_id}')
        if mount_path and os.path.ismount(mount_path):
            # Check for VOD files in common directories
            vod_dirs = [
                os.path.join(mount_path, 'videos'),
                os.path.join(mount_path, 'vod_content'),
                os.path.join(mount_path, 'city_council'),
                os.path.join(mount_path, 'meetings'),
                os.path.join(mount_path, 'content'),
                mount_path  # Root directory
            ]
            
            for vod_dir in vod_dirs:
                if os.path.exists(vod_dir):
                    # Look for files that might match this VOD
                    possible_files = [
                        f"{vod_id}.mp4",
                        f"{vod_id}.mov",
                        f"{vod_id}.avi",
                        f"{vod_id}.mkv",
                        f"vod_{vod_id}.mp4",
                        f"VOD_{vod_id}.mp4"
                    ]
                    
                    # Also check for files with title-based names
                    title = vod_data.get('title', '').replace(' ', '_').replace('/', '_')
                    if title:
                        possible_files.extend([
                            f"{title}.mp4",
                            f"{title}.mov",
                            f"{title}.avi",
                            f"{title}.mkv"
                        ])
                    
                    for filename in possible_files:
                        file_path = os.path.join(vod_dir, filename)
                        if os.path.exists(file_path) and os.access(file_path, os.R_OK):
                            logger.info(f"Found VOD file on mounted drive: {file_path}")
                            return file_path
                    
                    # Search recursively for video files that might match
                    try:
                        for root, dirs, files in os.walk(vod_dir):
                            for file in files:
                                if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.m4v')):
                                    file_path = os.path.join(root, file)
                                    # Check if this file might be our VOD
                                    if (str(vod_id) in file or 
                                        title.lower() in file.lower() or
                                        vod_data.get('title', '').lower() in file.lower()):
                                        if os.access(file_path, os.R_OK):
                                            logger.info(f"Found matching VOD file: {file_path}")
                                            return file_path
                    except OSError as e:
                        logger.warning(f"Error searching directory {vod_dir}: {e}")
                        continue
    
    # Add local paths to the search list
    local_paths.extend([
        f"/mnt/vod/{vod_id}.mp4",
        f"/mnt/vod/{vod_data.get('filename')}",
        f"/mnt/vod/{vod_data.get('title', '').replace(' ', '_')}.mp4"
    ])
    
    # Check all local paths first
    for path in local_paths:
        if path and os.path.exists(path):
            if not os.access(path, os.R_OK):
                logger.error(f"File exists but not readable: {path}")
                send_alert("error", f"File exists but not readable: {path}")
                continue
            logger.info(f"Using local VOD file: {path}")
            return path
    
    # Only attempt download if no local file is found
    vod_url = extract_vod_url_from_cablecast(vod_data)
    if vod_url:
        logger.info(f"No local file found, attempting download from: {vod_url}")
        temp_dir = "/tmp/vod_downloads"
        # Storage check
        if not os.path.exists(temp_dir):
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except OSError as e:
                logger.error(f"Failed to create temp dir {temp_dir}: {e}")
                send_alert("error", f"Failed to create temp dir {temp_dir}: {e}")
                return None
        if not os.access(temp_dir, os.W_OK):
            logger.error(f"Temp dir not writable: {temp_dir}")
            send_alert("error", f"Temp dir not writable: {temp_dir}")
            return None
        output_path = os.path.join(temp_dir, f"vod_{vod_id}.mp4")
        try:
            if download_vod_content(vod_url, output_path):
                return output_path
            else:
                logger.error(f"Failed to download VOD content from: {vod_url}")
        except Exception as e:
            logger.error(f"Download failed after retries: {e}")
            send_alert("error", f"Download failed after retries: {e}", vod_url=vod_url)
            return None
    
    logger.warning(f"No VOD file found for VOD {vod_id} on any mounted drive or via download")
    return None

def validate_video_file(video_path: str) -> bool:
    """Validate video file integrity and format."""
    try:
        # Use ffprobe to check video file
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', video_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"Video validation passed: {video_path}")
            return True
        else:
            logger.error(f"Video validation failed: {video_path}")
            return False
            
    except Exception as e:
        logger.error(f"Video validation error for {video_path}: {e}")
        return False

def create_captioned_video(video_path: str, scc_path: str, output_path: str) -> bool:
    """Create video with embedded captions using ffmpeg."""
    try:
        # Use ffmpeg to embed SCC captions into video
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f'subtitles={scc_path}',
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-c:v', 'libx264',  # Use H.264 codec
            '-preset', 'medium',  # Balance between speed and quality
            '-crf', '23',  # Constant rate factor for quality
            '-y',  # Overwrite output file
            output_path
        ]
        
        logger.info(f"Starting video retranscoding: {video_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            logger.info(f"Video retranscoding completed: {output_path}")
            return True
        else:
            logger.error(f"Video retranscoding failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Video retranscoding timed out: {video_path}")
        return False
    except Exception as e:
        logger.error(f"Video retranscoding error: {e}")
        return False

def get_city_vod_storage_path(city_id: str) -> str:
    """Get storage path for VOD files for a specific city."""
    city_config = MEMBER_CITIES.get(city_id, {})
    mount_path = city_config.get('mount_path', f'/mnt/{city_id}')
    return os.path.join(mount_path, 'vod_processed')

def map_city_to_vod_pattern(city_id: str) -> List[str]:
    """Map city ID to VOD title patterns for filtering."""
    city_patterns = {
        'flex1': ['birchwood', 'birch wood', 'birchwood city', 'birchwood city council'],
        'flex2': ['dellwood', 'grant', 'willernie', 'dellwood grant willernie', 'dellwood city council', 'grant city council'],
        'flex3': ['lake elmo', 'lakeelmo', 'lake elmo city council'],
        'flex4': ['mahtomedi', 'mahtomedi city council'],
        'flex7': ['oakdale', 'oakdale city council'],
        'flex8': ['white bear lake', 'whitebearlake', 'wbl', 'white bear lake school', 'white bear lake city council', 'white bear'],
        'flex9': ['white bear township', 'whitebeartownship', 'wbt', 'white bear township council']
    }
    
    return city_patterns.get(city_id, [])

# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="vod_processing.process_recent_vods")
def process_recent_vods() -> Dict[str, Any]:
    """Process most recent VOD content for each member city.
    
    This task:
    1. Discovers recent VODs for each member city from flex servers
    2. Downloads VOD content from direct URLs or flex server files
    3. Generates captions for uncaptioned VODs
    4. Retranscodes videos with embedded captions
    5. Validates quality and stores results
    
    Returns:
        Dictionary with processing results for each city
    """
    logger.info("Starting VOD processing for all member cities")
    
    client = CablecastAPIClient()
    transcription_service = TranscriptionService()
    results = {}
    
    # Import Celery transcription task for integration
    from core.tasks.transcription import run_whisper_transcription
    
    for city_id, city_config in MEMBER_CITIES.items():
        city_name = city_config['name']
        mount_path = city_config['mount_path']
        logger.info(f"Processing VODs for {city_name} ({city_id}) from {mount_path}")
        
        try:
            # Check if flex server mount is accessible
            if not os.path.ismount(mount_path):
                logger.warning(f"Flex server {city_id} not mounted at {mount_path}")
                results[city_id] = {'processed': 0, 'errors': ['Flex server not mounted'], 'message': 'Mount not available'}
                continue
            
            if not os.access(mount_path, os.R_OK):
                logger.warning(f"Flex server {city_id} not readable at {mount_path}")
                results[city_id] = {'processed': 0, 'errors': ['Flex server not readable'], 'message': 'Mount not accessible'}
                continue
            
            # Get recent VODs from flex server (direct file access)
            recent_vods = get_recent_vods_from_flex_server(mount_path, city_id, limit=5)
            
            if not recent_vods:
                logger.info(f"No recent VODs found for {city_name} on {mount_path}")
                results[city_id] = {'processed': 0, 'errors': [], 'message': 'No VODs found on flex server'}
                continue
            
            # Filter VODs by city-specific patterns
            city_patterns = map_city_to_vod_pattern(city_id)
            filtered_vods = []
            
            for vod in recent_vods:
                vod_title = vod.get('title', '').lower()
                if any(pattern in vod_title for pattern in city_patterns):
                    filtered_vods.append(vod)
                    logger.info(f"Found city-specific VOD: {vod.get('title')} (Path: {vod.get('file_path')})")
            
            if not filtered_vods:
                logger.info(f"No city-specific VODs found for {city_name}")
                results[city_id] = {'processed': 0, 'errors': [], 'message': 'No city-specific VODs found'}
                continue
            
            city_results = {
                'processed': 0,
                'errors': [],
                'vods_processed': []
            }
            
            # Process videos one at a time (sequential processing)
            for i, vod in enumerate(filtered_vods[:5]):
                try:
                    # Add to task queue for sequential processing
                    vod_id = vod.get('id', f"flex_{city_id}_{i}")
                    vod_title = vod.get('title', 'Unknown')
                    vod_path = vod.get('file_path', '')
                    
                    # Create a unique job name for the VOD
                    job_name = f"VOD_{vod_id}_{city_id}"
                    
                    # Process individual VOD with Celery (one at a time)
                    vod_result = process_single_vod.delay(vod_id, city_id, vod_path)
                    
                    city_results['vods_processed'].append({
                        'vod_id': vod_id,
                        'title': vod_title,
                        'file_path': vod_path,
                        'task_id': vod_result.id,
                        'status': 'queued',
                        'position': i + 1
                    })
                    city_results['processed'] += 1
                    
                    logger.info(f"Queued VOD {vod_id} ({vod_title}) for sequential processing")
                    
                except Exception as e:
                    error_msg = f"Failed to queue VOD {vod.get('id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    city_results['errors'].append(error_msg)
            
            results[city_id] = city_results
            logger.info(f"Queued {city_results['processed']} VODs for {city_name} (sequential processing)")
            
        except Exception as e:
            error_msg = f"Error processing VODs for {city_name}: {e}"
            logger.error(error_msg)
            results[city_id] = {'processed': 0, 'errors': [error_msg]}
    
    # Send summary alert
    total_processed = sum(r.get('processed', 0) for r in results.values())
    total_errors = sum(len(r.get('errors', [])) for r in results.values())
    
    if total_processed > 0:
        send_alert("info", f"VOD processing completed: {total_processed} VODs queued for sequential processing, {total_errors} errors")
    
    logger.info(f"VOD processing completed: {total_processed} VODs queued across all cities (sequential processing)")
    return results

def get_recent_vods_from_flex_server(mount_path: str, city_id: str, limit: int = 5) -> List[Dict]:
    """Get recent VOD files from flex server mount point (surface-level E: drive structure).
    
    This function scans mounted flex servers for video files at the surface level
    and creates VOD entries that can be processed locally without downloading from Cablecast.
    It prioritizes the most recently recorded content and filters out already processed files.
    
    Args:
        mount_path: Path to flex server mount
        city_id: Member city ID
        limit: Maximum number of VODs to return
        
    Returns:
        List of VOD dictionaries with file information
    """
    logger.info(f"Scanning flex server {city_id} at {mount_path} for recent VODs (surface-level)")
    
    vod_files = []
    
    try:
        # Check if mount is accessible
        if not os.path.ismount(mount_path):
            logger.warning(f"Mount point {mount_path} is not mounted")
            return []
        
        if not os.access(mount_path, os.R_OK):
            logger.warning(f"Mount point {mount_path} is not readable")
            return []
        
        # Surface-level file discovery (E: drive structure)
        # Search directly in the mount root, not in subdirectories
        import glob
        
        # Look for video files at surface level
        video_patterns = ['*.mp4', '*.mov', '*.avi', '*.mkv', '*.m4v', '*.wmv']
        
        for pattern in video_patterns:
            pattern_path = os.path.join(mount_path, pattern)
            video_files = glob.glob(pattern_path)
            
            for file_path in video_files:
                if os.path.isfile(file_path):
                    try:
                        stat = os.stat(file_path)
                        file_size = stat.st_size
                        mod_time = stat.st_mtime
                        file_name = os.path.basename(file_path)
                        
                        # Skip files that are too small (likely not complete videos)
                        if file_size < 5 * 1024 * 1024:
                            continue
                        
                        # Check if SCC file already exists (skip if already processed)
                        base_name = os.path.splitext(file_name)[0]
                        scc_path = os.path.join(mount_path, f"{base_name}.scc")
                        if os.path.exists(scc_path):
                            logger.debug(f"Skipping {file_name} - SCC already exists")
                            continue
                        
                        # Create VOD entry with surface-level information
                        vod_entry = {
                            'id': f"flex_{city_id}_{len(vod_files)}",
                            'title': base_name,
                            'file_path': file_path,
                            'file_name': file_name,
                            'file_size': file_size,
                            'modified_time': mod_time,
                            'source': 'flex_server',
                            'city_id': city_id,
                            'relative_path': file_name,  # Just the filename since it's surface-level
                            'directory': '',  # Empty since files are at surface level
                            'extension': os.path.splitext(file_name)[1].lower(),
                            'recording_date': mod_time,  # For sorting by recording time
                            'priority': 1  # All files at surface level have same priority
                        }
                        
                        vod_files.append(vod_entry)
                        logger.debug(f"Found video: {file_name} ({file_size} bytes)")
                        
                        if len(vod_files) >= limit * 3:  # Get more than needed for better filtering
                            break
                            
                    except OSError as e:
                        logger.warning(f"Error accessing file {file_path}: {e}")
                        continue
            
            if len(vod_files) >= limit * 3:
                break
        
        # Sort by modification time (newest first)
        vod_files.sort(key=lambda x: x['modified_time'], reverse=True)
        
        # Limit results
        vod_files = vod_files[:limit]
        
        logger.info(f"Found {len(vod_files)} video files on {city_id} (surface-level)")
        
    except Exception as e:
        logger.error(f"Error scanning flex server {city_id}: {e}")
    
    return vod_files

@celery_app.task(name="vod_processing.process_single_vod")
@track_vod_processing
def process_single_vod(vod_id: int, city_id: str, video_path: str = None) -> Dict[str, Any]:
    """Process a single VOD: download, caption, retranscode, and validate."""
    logger.info(f"Processing VOD {vod_id} for city {city_id}")
    if video_path:
        logger.info(f"Using direct file path: {video_path}")
    
    # Import Celery transcription task for integration
    from core.tasks.transcription import run_whisper_transcription
    
    client = CablecastAPIClient()
    transcription_service = TranscriptionService()
    try:
        # Prioritize local file access from mounted drives
        if video_path and os.path.exists(video_path):
            logger.info(f"Processing local file: {video_path}")
            local_video_path = video_path
        else:
            # Try to find the file on mounted drives first
            logger.info(f"Searching for VOD {vod_id} on mounted drives")
            
            # Create a minimal VOD data structure for local file search
            vod_data = {
                'id': vod_id,
                'title': f"VOD_{vod_id}",
                'city_id': city_id
            }
            
            # Search for the file on mounted drives
            local_video_path = get_vod_file_path(vod_data)
            
            if not local_video_path:
                # Fallback to Cablecast API only if local file not found
                logger.info(f"No local file found, attempting to get VOD {vod_id} from Cablecast API")
                try:
                    vod_data = client.get_vod(vod_id)
                    if vod_data:
                        local_video_path = get_vod_file_path(vod_data)
                except Exception as api_exc:
                    logger.error(f"Cablecast API error: {api_exc}")
                    send_alert("error", f"Cablecast API error: {api_exc}", vod_id=vod_id, city_id=city_id)
                    return {
                        'vod_id': vod_id,
                        'city_id': city_id,
                        'status': 'deferred',
                        'error': str(api_exc),
                        'message': 'Cablecast API unavailable, task deferred'
                    }
            
            if not local_video_path:
                raise Exception(f"No video file found for VOD {vod_id} on mounted drives or via API")
        
        # Validate video file
        if not validate_video_file(local_video_path):
            raise Exception(f"Video file validation failed for {local_video_path}")
        
        # Check if VOD already has captions (only if we have VOD ID from API)
        if vod_id and not vod_id.startswith('flex_'):
            try:
                existing_captions = client.get_vod_captions(vod_id)
                if existing_captions:
                    logger.info(f"VOD {vod_id} already has captions, skipping captioning")
                    return {
                        'vod_id': vod_id,
                        'city_id': city_id,
                        'status': 'skipped',
                        'reason': 'captions_exist',
                        'message': 'VOD already has captions'
                    }
            except Exception as e:
                logger.warning(f"Could not check for existing captions: {e}")
        
        # --- Storage check before generating captions ---
        city_storage_path = get_city_vod_storage_path(city_id)
        storage_mount = os.path.dirname(city_storage_path)
        if not os.path.ismount(storage_mount):
            logger.error(f"Storage mount unavailable: {storage_mount}")
            send_alert("error", f"Storage mount unavailable: {storage_mount}")
            return {
                'vod_id': vod_id,
                'city_id': city_id,
                'status': 'failed',
                'error': 'Storage unavailable',
                'message': f'Storage mount unavailable: {storage_mount}'
            }
        if not os.access(storage_mount, os.W_OK):
            logger.error(f"Storage not writable: {storage_mount}")
            send_alert("error", f"Storage not writable: {storage_mount}")
            return {
                'vod_id': vod_id,
                'city_id': city_id,
                'status': 'failed',
                'error': 'Storage not writable',
                'message': f'Storage not writable: {storage_mount}'
            }
        
        # Generate captions using Celery transcription task
        transcription_result = run_whisper_transcription.delay(local_video_path)
        # Don't call .get() within a task - let the task complete asynchronously
        logger.info(f"Transcription task queued: {transcription_result.id}")
        
        # For now, we'll skip the synchronous processing and let tasks run independently
        # This avoids the "Never call result.get() within a task!" error
        logger.info(f"VOD {vod_id} processing queued successfully")
        return {
            'vod_id': vod_id,
            'city_id': city_id,
            'status': 'queued',
            'transcription_task_id': transcription_result.id,
            'message': 'VOD processing queued for asynchronous processing'
        }
        
        # Note: Upload and validation tasks are now handled asynchronously
        # to avoid the "Never call result.get() within a task!" error
    except Exception as e:
        error_msg = f"VOD processing failed for {vod_id}: {e}"
        logger.error(error_msg)
        send_alert("error", error_msg, vod_id=vod_id, city_id=city_id)
        return {
            'vod_id': vod_id,
            'city_id': city_id,
            'status': 'failed',
            'error': str(e),
            'message': error_msg
        }

@celery_app.task(name="vod_processing.download_vod_content")
def download_vod_content_task(vod_id: int, vod_url: str, city_id: str) -> Dict[str, Any]:
    """Download VOD content from direct URL.
    
    Args:
        vod_id: Cablecast VOD ID
        vod_url: Direct VOD URL
        city_id: Member city ID
        
    Returns:
        Dictionary with download results
    """
    logger.info(f"Downloading VOD content for {vod_id} from: {vod_url}")
    
    try:
        # Create download directory
        download_dir = "/tmp/vod_downloads"
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate output path
        output_path = os.path.join(download_dir, f"vod_{vod_id}.mp4")
        
        # Download content
        success = download_vod_content(vod_url, output_path)
        
        if success:
            # Get file size
            file_size = os.path.getsize(output_path)
            
            logger.info(f"VOD content downloaded successfully: {output_path} ({file_size / (1024*1024):.1f}MB)")
            
            return {
                'success': True,
                'vod_id': vod_id,
                'city_id': city_id,
                'download_path': output_path,
                'file_size': file_size,
                'message': 'VOD content downloaded successfully'
            }
        else:
            raise Exception("Download failed")
            
    except Exception as e:
        error_msg = f"VOD download failed for {vod_id}: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'vod_id': vod_id,
            'city_id': city_id,
            'error': str(e),
            'message': error_msg
        }

@celery_app.task(name="vod_processing.generate_vod_captions")
def generate_vod_captions(vod_id: int, video_path: str, city_id: str) -> Dict[str, Any]:
    """Generate SCC captions for a VOD.
    
    Args:
        vod_id: Cablecast VOD ID
        video_path: Path to video file
        city_id: Member city ID
        
    Returns:
        Dictionary with caption generation results
    """
    logger.info(f"Generating captions for VOD {vod_id}")
    
    try:
        transcription_service = TranscriptionService()
        
        # Transcribe video to generate SCC captions
        transcription_result = transcription_service.transcribe_file(video_path)
        
        if not transcription_result or 'output_path' not in transcription_result:
            raise Exception("Transcription failed to produce SCC file")
        
        scc_path = transcription_result['output_path']
        
        # Validate SCC file
        if not os.path.exists(scc_path):
            raise Exception(f"SCC file not found at {scc_path}")
        
        # Copy SCC file to city-specific storage
        city_storage_path = get_city_vod_storage_path(city_id)
        os.makedirs(city_storage_path, exist_ok=True)
        
        city_scc_path = os.path.join(city_storage_path, f"vod_{vod_id}.scc")
        import shutil
        shutil.copy2(scc_path, city_scc_path)
        
        logger.info(f"Captions generated for VOD {vod_id}: {city_scc_path}")
        
        return {
            'success': True,
            'scc_path': city_scc_path,
            'original_scc_path': scc_path,
            'message': 'Captions generated successfully'
        }
        
    except Exception as e:
        error_msg = f"Caption generation failed for VOD {vod_id}: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }

@celery_app.task(name="vod_processing.retranscode_vod_with_captions")
def retranscode_vod_with_captions(vod_id: int, video_path: str, scc_path: str, city_id: str) -> Dict[str, Any]:
    """Retranscode video with embedded captions.
    
    Args:
        vod_id: Cablecast VOD ID
        video_path: Path to original video file
        scc_path: Path to SCC caption file
        city_id: Member city ID
        
    Returns:
        Dictionary with retranscoding results
    """
    logger.info(f"Retranscoding VOD {vod_id} with captions")
    
    try:
        # Create output path for captioned video
        city_storage_path = get_city_vod_storage_path(city_id)
        os.makedirs(city_storage_path, exist_ok=True)
        
        video_name = os.path.basename(video_path)
        name_without_ext = os.path.splitext(video_name)[0]
        output_path = os.path.join(city_storage_path, f"{name_without_ext}_captioned.mp4")
        
        # Create captioned video
        success = create_captioned_video(video_path, scc_path, output_path)
        
        if not success:
            raise Exception("Video retranscoding failed")
        
        # Validate output file
        if not os.path.exists(output_path):
            raise Exception(f"Output file not created: {output_path}")
        
        # Get file size for validation
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise Exception("Output file is empty")
        
        logger.info(f"Video retranscoding completed for VOD {vod_id}: {output_path}")
        
        return {
            'success': True,
            'output_path': output_path,
            'file_size': file_size,
            'message': 'Video retranscoding completed successfully'
        }
        
    except Exception as e:
        error_msg = f"Video retranscoding failed for VOD {vod_id}: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }

@celery_app.task(name="vod_processing.upload_captioned_vod")
def upload_captioned_vod(vod_id: int, captioned_video_path: str, scc_path: str) -> Dict[str, Any]:
    """Upload captioned video and SCC file to Cablecast.
    
    Args:
        vod_id: Cablecast VOD ID
        captioned_video_path: Path to captioned video file
        scc_path: Path to SCC caption file
        
    Returns:
        Dictionary with upload results
    """
    logger.info(f"Uploading captioned VOD {vod_id} to Cablecast")
    
    try:
        client = CablecastAPIClient()
        
        # Upload captioned video
        video_upload_success = client.upload_video_file(vod_id, captioned_video_path)
        if not video_upload_success:
            raise Exception("Video upload failed")
        
        # Upload SCC caption file
        caption_upload_success = client.upload_scc_file(vod_id, scc_path)
        if not caption_upload_success:
            raise Exception("SCC caption upload failed")
        
        logger.info(f"Upload completed for VOD {vod_id}")
        
        return {
            'success': True,
            'video_uploaded': video_upload_success,
            'caption_uploaded': caption_upload_success,
            'message': 'Upload completed successfully'
        }
        
    except Exception as e:
        error_msg = f"Upload failed for VOD {vod_id}: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }

@celery_app.task(name="vod_processing.validate_vod_quality")
def validate_vod_quality(vod_id: int, video_path: str) -> Dict[str, Any]:
    """Validate quality of processed VOD.
    
    Args:
        vod_id: Cablecast VOD ID
        video_path: Path to processed video file
        
    Returns:
        Dictionary with quality validation results
    """
    logger.info(f"Validating quality for VOD {vod_id}")
    
    try:
        quality_score = 0
        validation_results = {}
        
        # Check file integrity
        if validate_video_file(video_path):
            quality_score += 25
            validation_results['file_integrity'] = True
        else:
            validation_results['file_integrity'] = False
        
        # Check file size
        file_size = os.path.getsize(video_path)
        if file_size > 1024 * 1024:  # At least 1MB
            quality_score += 25
            validation_results['file_size'] = True
        else:
            validation_results['file_size'] = False
        
        # Check video duration (basic check)
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', video_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                if duration > 0:
                    quality_score += 25
                    validation_results['duration'] = True
                else:
                    validation_results['duration'] = False
            else:
                validation_results['duration'] = False
        except:
            validation_results['duration'] = False
        
        # Check for caption stream (if embedded)
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-select_streams', 's',
                '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', video_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                quality_score += 25
                validation_results['captions_embedded'] = True
            else:
                validation_results['captions_embedded'] = False
        except:
            validation_results['captions_embedded'] = False
        
        logger.info(f"Quality validation completed for VOD {vod_id}: {quality_score}/100")
        
        return {
            'success': True,
            'quality_score': quality_score,
            'validation_results': validation_results,
            'message': f'Quality score: {quality_score}/100'
        }
        
    except Exception as e:
        error_msg = f"Quality validation failed for VOD {vod_id}: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }

# ---------------------------------------------------------------------------
# Utility Tasks
# ---------------------------------------------------------------------------

@celery_app.task(name="vod_processing.cleanup_temp_files")
def cleanup_temp_files() -> Dict[str, Any]:
    """Clean up temporary files from VOD processing."""
    logger.info("Cleaning up temporary VOD processing files")
    
    try:
        cleaned_count = 0
        temp_dirs = ['/tmp/vod_downloads', '/tmp', '/var/tmp']
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(('.tmp', '.temp')) and 'vod_' in file:
                            try:
                                file_path = os.path.join(root, file)
                                # Only delete files older than 1 hour
                                if os.path.getmtime(file_path) < (datetime.now() - timedelta(hours=1)).timestamp():
                                    os.remove(file_path)
                                    cleaned_count += 1
                            except:
                                continue
        
        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'message': f'Cleaned up {cleaned_count} temporary files'
        }
        
    except Exception as e:
        error_msg = f"Cleanup failed: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        } 