# PURPOSE: Celery tasks for automatic transcription linking to Cablecast shows
# DEPENDENCIES: core.vod_automation, core.tasks.celery_app
# MODIFICATION NOTES: v1.0 - Initial implementation for automatic transcription linking

"""Celery tasks for automatic transcription linking.

This module provides Celery tasks for automatically linking completed transcriptions
to existing Cablecast shows, including scheduled processing and manual triggers.
"""

from celery import current_task
from loguru import logger
from typing import Dict, List
import time

from core.tasks import celery_app
from core.vod_automation import (
    process_transcription_queue,
    auto_link_transcription_to_show,
    get_transcription_link_status
)
from core.models import TranscriptionResultORM, CablecastShowORM
from core.app import db


@celery_app.task(name="transcription_linking.process_queue", bind=True)
def process_transcription_linking_queue(self) -> Dict:
    """
    Process the transcription linking queue - automatically link completed transcriptions to shows.
    
    This task scans for completed transcriptions that haven't been linked to Cablecast shows
    and attempts to automatically link them based on filename matching and metadata.
    
    Returns:
        Dictionary containing processing results:
        {
            'success': bool,
            'processed': int,        # Number of transcriptions successfully linked
            'total_unlinked': int,   # Total number of unlinked transcriptions found
            'errors': List[str],     # List of error messages
            'message': str,          # Summary message
            'task_id': str           # Celery task ID
        }
    """
    task_id = self.request.id
    logger.info(f"Starting transcription linking queue processing task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Processing transcription linking queue...'}
        )
        
        # Process the queue
        result = process_transcription_queue()
        result['task_id'] = task_id
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"Transcription linking queue processing completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f"Error processing transcription linking queue: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="transcription_linking.link_single", bind=True)
def link_single_transcription(self, transcription_id: str) -> Dict:
    """
    Link a single transcription to a Cablecast show.
    
    Args:
        transcription_id: ID of the transcription to link
        
    Returns:
        Dictionary containing linking results:
        {
            'success': bool,
            'linked': bool,          # Whether transcription was successfully linked
            'show_id': int,          # ID of the show it was linked to (if successful)
            'message': str,          # Result message
            'task_id': str           # Celery task ID
        }
    """
    task_id = self.request.id
    logger.info(f"Starting single transcription linking task {task_id} for {transcription_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': f'Linking transcription {transcription_id}...'}
        )
        
        # Attempt to link the transcription
        result = auto_link_transcription_to_show(transcription_id)
        result['task_id'] = task_id
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"Single transcription linking completed: {result.get('message', 'Unknown result')}")
        return result
        
    except Exception as e:
        error_msg = f"Error linking transcription {transcription_id}: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="transcription_linking.get_status", bind=True)
def get_linking_status(self, transcription_id: str = None) -> Dict:
    """
    Get the status of transcription linking for a specific transcription or overall system.
    
    Args:
        transcription_id: Optional ID of specific transcription to check
        
    Returns:
        Dictionary containing status information:
        {
            'success': bool,
            'transcription_id': str,  # If checking specific transcription
            'linked': bool,           # Whether transcription is linked
            'show_id': int,          # ID of linked show (if linked)
            'total_completed': int,   # Total completed transcriptions
            'total_linked': int,      # Total linked transcriptions
            'total_unlinked': int,    # Total unlinked transcriptions
            'task_id': str           # Celery task ID
        }
    """
    task_id = self.request.id
    logger.info(f"Starting transcription linking status check task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking transcription linking status...'}
        )
        
        if transcription_id:
            # Check specific transcription
            status = get_transcription_link_status(transcription_id)
            status['transcription_id'] = transcription_id
            status['task_id'] = task_id
        else:
            # Get overall system status
            completed_transcriptions = TranscriptionResultORM.query.filter_by(
                status='completed'
            ).all()
            
            linked_count = 0
            unlinked_count = 0
            
            for transcription in completed_transcriptions:
                existing_link = CablecastShowORM.query.filter_by(
                    transcription_id=transcription.id
                ).first()
                
                if existing_link:
                    linked_count += 1
                else:
                    unlinked_count += 1
            
            status = {
                'success': True,
                'total_completed': len(completed_transcriptions),
                'total_linked': linked_count,
                'total_unlinked': unlinked_count,
                'task_id': task_id
            }
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': status
            }
        )
        
        logger.info(f"Transcription linking status check completed")
        return status
        
    except Exception as e:
        error_msg = f"Error checking transcription linking status: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="transcription_linking.cleanup_orphaned", bind=True)
def cleanup_orphaned_links(self) -> Dict:
    """
    Clean up orphaned transcription links (transcriptions that no longer exist).
    
    Returns:
        Dictionary containing cleanup results:
        {
            'success': bool,
            'cleaned': int,          # Number of orphaned links cleaned up
            'total_links': int,      # Total number of links before cleanup
            'message': str,          # Summary message
            'task_id': str           # Celery task ID
        }
    """
    task_id = self.request.id
    logger.info(f"Starting orphaned transcription links cleanup task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Cleaning up orphaned transcription links...'}
        )
        
        # Get all transcription links
        all_links = CablecastShowORM.query.filter(
            CablecastShowORM.transcription_id.isnot(None)
        ).all()
        
        cleaned_count = 0
        total_links = len(all_links)
        
        for link in all_links:
            # Check if the transcription still exists
            transcription = TranscriptionResultORM.query.get(link.transcription_id)
            if not transcription:
                # Transcription no longer exists, remove the link
                logger.warning(f"Removing orphaned link for non-existent transcription {link.transcription_id}")
                db.session.delete(link)
                cleaned_count += 1
        
        # Commit changes
        if cleaned_count > 0:
            db.session.commit()
            logger.info(f"Cleaned up {cleaned_count} orphaned transcription links")
        
        result = {
            'success': True,
            'cleaned': cleaned_count,
            'total_links': total_links,
            'message': f'Cleaned up {cleaned_count} orphaned links out of {total_links} total links',
            'task_id': task_id
        }
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"Orphaned transcription links cleanup completed: {result['message']}")
        return result
        
    except Exception as e:
        error_msg = f"Error cleaning up orphaned transcription links: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        } 