"""VOD Automation for automatic content publishing.

This module provides automated workflows for content publishing to VOD systems,
including automatic publishing on transcription completion and queue-based processing.

Key Features:
- Automatic publishing on transcription completion
- Queue-based processing
- Configurable automation triggers
"""

from loguru import logger
import os
from core.task_queue import queue_manager
from core.vod_content_manager import VODContentManager

logger = logger.getLogger(__name__)

def auto_publish_to_vod(transcription_id: str):
    """Automatically publish transcription to VOD when completed"""
    try:
        vod_manager = VODContentManager()
        result = vod_manager.process_archivist_content_for_vod(transcription_id)
        
        if result:
            logger.info(f"Auto-published transcription {transcription_id} to VOD")
        else:
            logger.error(f"Failed to auto-publish transcription {transcription_id} to VOD")
            
    except Exception as e:
        logger.error(f"Error in auto-publish to VOD: {e}")

# Modify transcription completion to trigger VOD publishing
def on_transcription_complete(transcription_id: str):
    """Called when transcription is completed"""
    # Existing transcription completion logic...
    
    # Auto-publish to VOD if enabled
    if os.getenv('AUTO_PUBLISH_TO_VOD', 'false').lower() == 'true':
        queue_manager.enqueue_task(auto_publish_to_vod, transcription_id)
