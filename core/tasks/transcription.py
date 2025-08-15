"""Celery transcription tasks for Archivist application.

This module provides Celery tasks for transcription operations, migrating
from the RQ system to a unified Celery-based architecture.

Key Features:
- WhisperX transcription via Celery
- Progress tracking and status updates
- Error handling and retry mechanisms
- Integration with VOD processing pipeline
"""

from celery import current_task
from loguru import logger
from typing import Dict, Optional, List, Set
import os
import time
import glob
import redis

from core.tasks import celery_app
from core.config import MEMBER_CITIES, REDIS_URL, OUTPUT_DIR
from core.services.transcription import TranscriptionService
from core.monitoring.autopriority_metrics import increment_counters
from core.transcription import _transcribe_with_faster_whisper as sync_transcribe


@celery_app.task(name="transcription.run_whisper", bind=True)
def run_whisper_transcription(self, video_path: str) -> Dict:
    """
    Transcribe a video file using WhisperX via Celery.
    
    This task replaces the RQ transcription job with a Celery-based implementation
    that provides better progress tracking, error handling, and integration with
    the VOD processing pipeline.
    
    Args:
        video_path: Path to the video file to transcribe
        
    Returns:
        Dictionary containing transcription results:
        {
            'output_path': str,      # Path to generated SCC file
            'status': str,           # 'completed', 'failed', etc.
            'segments': int,         # Number of transcription segments
            'duration': float,       # Video duration in seconds
            'error': str,            # Error message if failed
            'task_id': str           # Celery task ID
        }
        
    Raises:
        Exception: If transcription fails
    """
    task_id = self.request.id
    logger.info(f"Starting Celery transcription task {task_id} for {video_path}")
    
    try:
        # Validate input file
        if not os.path.exists(video_path):
            error_msg = f"Video file not found: {video_path}"
            logger.error(f"Task {task_id}: {error_msg}")
            self.update_state(
                state='FAILURE',
                meta={'error': error_msg, 'video_path': video_path}
            )
            raise FileNotFoundError(error_msg)
        
        # Update task state to processing
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 0,
                'status_message': 'Initializing transcription...',
                'video_path': video_path
            }
        )
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 10,
                'status_message': 'Loading WhisperX model...',
                'video_path': video_path
            }
        )
        
        # Perform transcription using synchronous helper
        logger.info(f"Task {task_id}: Starting transcription of {video_path}")
        result = sync_transcribe(video_path=video_path)
        
        # Update progress to completion
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'processing',
                'progress': 90,
                'status_message': 'Finalizing transcription...',
                'video_path': video_path
            }
        )
        
        # Prepare final result
        final_result = {
            'output_path': result.get('output_path', ''),
            'status': 'completed',
            'segments': result.get('segments', 0),
            'duration': result.get('duration', 0),
            'video_path': video_path,
            'task_id': task_id,
            'progress': 100,
            'status_message': 'Transcription completed successfully'
        }
        
        logger.info(f"Task {task_id}: Transcription completed successfully")
        logger.info(f"Task {task_id}: Output saved to {final_result['output_path']}")
        
        return final_result
        
    except Exception as e:
        error_msg = f"Transcription failed for {video_path}: {str(e)}"
        logger.error(f"Task {task_id}: {error_msg}")
        
        # Update task state to failure
        self.update_state(
            state='FAILURE',
            meta={
                'error': error_msg,
                'video_path': video_path,
                'task_id': task_id,
                'status': 'failed'
            }
        )
        
        # Re-raise the exception for Celery to handle
        raise


@celery_app.task(name="transcription.batch_process")
def batch_transcription(video_paths: list, priority: Optional[int] = None) -> Dict:
    """
    Process multiple video files for transcription and captioning.
    
    This task allows for batch processing of multiple videos, which is useful
    for VOD processing pipelines that need to transcribe multiple files.
    It integrates with the captioning workflow to generate SCC captions.
    
    Args:
        video_paths: List of video file paths to transcribe
        priority: Optional priority level for the batch
        
    Returns:
        Dictionary containing batch processing results
    """
    logger.info(f"Starting batch transcription for {len(video_paths)} videos")
    
    results = {
        'total_videos': len(video_paths),
        'completed': 0,
        'failed': 0,
        'results': [],
        'errors': [],
        'captioning_results': []
    }
    
    # Process videos sequentially to avoid overwhelming the system
    for i, video_path in enumerate(video_paths):
        try:
            logger.info(f"Processing video {i+1}/{len(video_paths)}: {video_path}")
            
            # Submit individual transcription task
            task = run_whisper_transcription.delay(video_path)
            
            # Wait for completion (with timeout)
            result = task.get(timeout=3600)  # 1 hour timeout
            
            if result and result.get('status') == 'completed':
                # Transcription successful, now integrate with captioning workflow
                scc_path = result.get('output_path')
                if scc_path and os.path.exists(scc_path):
                    # Generate captioned video using VOD processing workflow
                    captioning_result = generate_captioned_video(video_path, scc_path)
                    results['captioning_results'].append({
                        'video_path': video_path,
                        'scc_path': scc_path,
                        'captioning_success': captioning_result.get('success', False),
                        'captioned_video_path': captioning_result.get('output_path')
                    })
                
                results['results'].append({
                    'video_path': video_path,
                    'task_id': task.id,
                    'status': 'completed',
                    'result': result
                })
                results['completed'] += 1
                
                logger.info(f"Completed transcription and captioning for {video_path}")
            else:
                # Transcription failed
                error_msg = f"Transcription failed for {video_path}"
                results['errors'].append({
                    'video_path': video_path,
                    'error': error_msg,
                    'task_id': task.id
                })
                results['failed'] += 1
                
        except Exception as e:
            error_msg = f"Failed to transcribe {video_path}: {str(e)}"
            logger.error(error_msg)
            
            results['errors'].append({
                'video_path': video_path,
                'error': error_msg
            })
            results['failed'] += 1
    
    logger.info(f"Batch transcription completed: {results['completed']} successful, {results['failed']} failed")
    return results


def generate_captioned_video(video_path: str, scc_path: str) -> Dict:
    """
    Generate captioned video using the VOD processing workflow.
    
    Args:
        video_path: Path to the original video file
        scc_path: Path to the SCC caption file
        
    Returns:
        Dictionary with captioning results
    """
    try:
        from core.tasks.vod_processing import create_captioned_video
        
        # Create output path for captioned video
        video_dir = os.path.dirname(video_path)
        video_name = os.path.basename(video_path)
        name_without_ext = os.path.splitext(video_name)[0]
        output_path = os.path.join(video_dir, f"{name_without_ext}_captioned.mp4")
        
        # Generate captioned video
        success = create_captioned_video(video_path, scc_path, output_path)
        
        if success and os.path.exists(output_path):
            logger.info(f"Captioned video generated: {output_path}")
            return {
                'success': True,
                'output_path': output_path,
                'message': 'Captioned video generated successfully'
            }
        else:
            logger.error(f"Failed to generate captioned video for {video_path}")
            return {
                'success': False,
                'error': 'Captioning failed',
                'message': 'Failed to generate captioned video'
            }
            
    except Exception as e:
        error_msg = f"Captioning error for {video_path}: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': str(e),
            'message': error_msg
        }


@celery_app.task(name="transcription.cleanup_temp_files")
def cleanup_transcription_temp_files(temp_dir: Optional[str] = None) -> Dict:
    """
    Clean up temporary files from transcription processes.
    
    Args:
        temp_dir: Optional directory to clean (defaults to system temp)
        
    Returns:
        Dictionary with cleanup results
    """
    import tempfile
    import shutil
    from datetime import datetime, timedelta
    
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
    
    logger.info(f"Cleaning up temporary transcription files in {temp_dir}")
    
    results = {
        'directory': temp_dir,
        'files_removed': 0,
        'bytes_freed': 0,
        'errors': []
    }
    
    try:
        # Find temporary files older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                # Look for transcription-related temp files
                if any(pattern in file.lower() for pattern in ['whisper', 'transcription', 'audio', 'temp']):
                    file_path = os.path.join(root, file)
                    
                    try:
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            
                            results['files_removed'] += 1
                            results['bytes_freed'] += file_size
                            
                            logger.debug(f"Removed temp file: {file_path}")
                            
                    except Exception as e:
                        error_msg = f"Failed to remove {file_path}: {str(e)}"
                        results['errors'].append(error_msg)
                        logger.warning(error_msg)
        
        logger.info(f"Cleanup completed: {results['files_removed']} files removed, {results['bytes_freed']} bytes freed")
        return results
        
    except Exception as e:
        error_msg = f"Cleanup failed: {str(e)}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
        return results


# Helper function for backward compatibility
def enqueue_transcription(video_path: str, position: Optional[int] = None) -> str:
    """
    Enqueue a transcription job (backward compatibility with RQ system).
    
    This function provides a drop-in replacement for the RQ enqueue_transcription
    function, allowing for seamless migration from RQ to Celery.
    
    Args:
        video_path: Path to the video file
        position: Ignored (Celery doesn't support position-based queuing)
        
    Returns:
        Celery task ID
    """
    logger.info(f"Enqueueing transcription for {video_path} via Celery")
    
    # Submit Celery task
    task = run_whisper_transcription.delay(video_path)
    
    logger.info(f"Transcription task submitted: {task.id}")
    return task.id


# ---------------------------------------------------------------------------
# Auto-prioritization of newest videos (run morning and night)
# ---------------------------------------------------------------------------

def _list_recent_videos_for_city(mount_path: str, max_scan: int = 100) -> List[str]:
    """Return newest-to-oldest video paths from mount root and common subdirs (one level deep).

    Scans the mount root plus typical content directories used by VOD ingestion to better
    prioritize truly recent content. Only surface-level files within those directories
    are considered to keep performance predictable.
    """
    if not os.path.isdir(mount_path):
        return []

    # Common subfolders aligned with VOD discovery
    candidate_dirs: List[str] = [
        mount_path,
        os.path.join(mount_path, 'videos'),
        os.path.join(mount_path, 'vod_content'),
        os.path.join(mount_path, 'city_council'),
        os.path.join(mount_path, 'meetings'),
        os.path.join(mount_path, 'content'),
        os.path.join(mount_path, 'incoming'),
        os.path.join(mount_path, 'recordings'),
    ]

    video_exts = ('.mp4', '.mkv', '.mov', '.ts', '.m4v', '.avi')
    entries: List[tuple[float, str]] = []

    try:
        for folder in candidate_dirs:
            if not os.path.isdir(folder):
                continue
            try:
                with os.scandir(folder) as it:
                    for entry in it:
                        if not entry.is_file():
                            continue
                        name_lower = entry.name.lower()
                        if not name_lower.endswith(video_exts):
                            continue
                        try:
                            st = entry.stat()
                            entries.append((st.st_mtime, entry.path))
                        except OSError:
                            continue
            except PermissionError:
                # Skip folders without read permission
                continue
    except Exception:
        # Fail-safe: return what we have gathered so far
        pass

    # Sort newest first and cap scan size for performance
    entries.sort(reverse=True)
    return [p for _, p in entries[:max_scan]]


def _is_already_captioned(video_path: str) -> bool:
    """Return True if there is a matching SCC for the given video.

    Checks adjacent file, common sibling caption folders, and the global OUTPUT_DIR.
    """
    try:
        base_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        candidates: List[str] = []

        # Adjacent SCC
        candidates.append(os.path.join(base_dir, f"{base_name}.scc"))

        # Common sibling caption folders
        for sibling in ('transcriptions', 'scc_files', 'captions'):
            candidates.append(os.path.join(base_dir, sibling, f"{base_name}.scc"))

        # Global output directory (if configured)
        if OUTPUT_DIR:
            candidates.append(os.path.join(OUTPUT_DIR, f"{base_name}.scc"))

        for p in candidates:
            if os.path.exists(p):
                return True
    except Exception:
        pass
    return False


def _gather_queued_video_args() -> Set[str]:
    """Collect video paths currently active/reserved/scheduled in Celery to avoid duplicates."""
    queued: Set[str] = set()
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        scheduled = inspect.scheduled() or {}
        for coll in (active, reserved, scheduled):
            for _worker, tasks in (coll or {}).items():
                for task in tasks:
                    args = task.get('argsrepr') or ''
                    # argsrepr looks like "('path',)"; do a best-effort parse
                    if isinstance(args, str) and args.startswith("('"):
                        try:
                            path = args.split("'", 2)[1]
                            if path:
                                queued.add(path)
                        except Exception:
                            pass
                    # Also check kwargs repr
                    kwargs = task.get('kwargsrepr') or ''
                    if isinstance(kwargs, str) and 'video_path' in kwargs:
                        try:
                            # crude parse video_path='...'
                            marker = "video_path='"
                            if marker in kwargs:
                                part = kwargs.split(marker, 1)[1]
                                path = part.split("'", 1)[0]
                                if path:
                                    queued.add(path)
                        except Exception:
                            pass
    except Exception:
        # If inspect fails, return empty set
        return queued
    return queued


@celery_app.task(name="transcription.autoprioritize_newest")
def autoprioritize_newest(max_per_city: int = 1, scan_limit_per_city: int = 50) -> Dict:
    """
    Discover the newest uncaptioned videos on each flex server and enqueue them
    onto a priority queue so they execute immediately after the currently running task.

    Notes:
    - Celery with Redis does not support per-task numeric priority; we emulate
      "second from top" by routing to a dedicated queue consumed first by workers.
    - Ensure workers run with: celery -Q caption_priority,celery -Ofair -c 1
      so the next task after the current one comes from the priority queue.
    """
    results: Dict[str, Dict] = {}

    # Track already enqueued paths in Redis for a short window to prevent dupes
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    seen_key = 'caption_autopriority:seen_paths'
    try:
        # Ensure key has an expiry; refresh at each run (default 24h, configurable)
        ttl_hours = int(os.getenv('CAPTION_AUTOPRIORITY_SEEN_TTL_HOURS', '24'))
        r.expire(seen_key, max(1, ttl_hours) * 3600)
    except Exception:
        pass

    queued_now: Set[str] = _gather_queued_video_args()

    # Use service-layer selection to avoid duplication
    svc = TranscriptionService()
    city_to_picks = svc.pick_newest_uncaptioned(max_per_city=max_per_city, scan_limit=scan_limit_per_city)

    for city_id, picks in city_to_picks.items():
        city_name = MEMBER_CITIES.get(city_id, {}).get('name', city_id)
        # De-duplicate against queue and seen set
        filtered: List[str] = []
        skipped_alreadyqueued_count = 0
        for video_path in picks:
            if video_path in queued_now:
                skipped_alreadyqueued_count += 1
                continue
            try:
                if r.sismember(seen_key, video_path):
                    skipped_alreadyqueued_count += 1
                    continue
            except Exception:
                pass
            filtered.append(video_path)

        enqueued: List[str] = []
        for path in filtered:
            try:
                # Route to priority queue so it runs next
                async_res = run_whisper_transcription.apply_async(args=[path], queue='caption_priority')
                enqueued.append(path)
                try:
                    r.sadd(seen_key, path)
                    ttl_hours = int(os.getenv('CAPTION_AUTOPRIORITY_SEEN_TTL_HOURS', '24'))
                    r.expire(seen_key, max(1, ttl_hours) * 3600)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to enqueue priority transcription for {path}: {e}")

        # Emit counters via shared helper
        increment_counters(
            scanned=len(picks),
            enqueued=len(enqueued),
            skipped_captioned=0,  # already filtered in service
            skipped_seen=skipped_alreadyqueued_count,
            city_enqueued={city_id: len(enqueued)},
        )

        results[city_id] = {
            'city_name': city_name,
            'scanned': len(picks),
            'enqueued': enqueued,
            'skipped_captioned': 0,
            'skipped_alreadyqueued': skipped_alreadyqueued_count,
        }

    return results

# Export for backward compatibility
__all__ = [
    'run_whisper_transcription',
    'batch_transcription', 
    'cleanup_transcription_temp_files',
    'enqueue_transcription'
] 