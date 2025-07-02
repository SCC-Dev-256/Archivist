from core.services import TranscriptionService
from core.config import BATCH_SIZE, NUM_WORKERS, NAS_PATH
from loguru import logger
import sys
import os
import subprocess
from typing import List, Dict

# Configure logger to show more details
logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("transcription.log", rotation="1 MB")

def check_flex_mounts() -> Dict[str, List[str]]:
    """Check all Flex mount points and their duplicates"""
    mount_map = {}
    try:
        # Check all Flex-N mount points
        for i in range(1, 10):
            flex_path = f"/mnt/flex-{i}"
            if os.path.exists(flex_path):
                try:
                    contents = os.listdir(flex_path)
                    mount_map[flex_path] = contents
                    logger.info(f"Mount point {flex_path} exists and contains {len(contents)} items")
                    if contents:
                        logger.info(f"Sample contents: {', '.join(contents[:5])}")
                except PermissionError:
                    logger.error(f"Permission denied accessing {flex_path}")
                except Exception as e:
                    logger.error(f"Error accessing {flex_path}: {e}")
            else:
                logger.warning(f"Mount point {flex_path} does not exist")
                
    except Exception as e:
        logger.error(f"Error checking mount points: {e}")
    
    return mount_map

def find_video_file(filename: str, mount_map: Dict[str, List[str]]) -> str:
    """Try to find the video file in available mount points"""
    for mount_point, contents in mount_map.items():
        potential_path = os.path.join(mount_point, filename)
        if os.path.exists(potential_path):
            logger.info(f"Found video at: {potential_path}")
            return potential_path
    return ""

def main():
    try:
        # Video filename - updated to use the new file
        video_filename = "10845-1-Birchwood City Council (20160614).mpeg"
        
        # Since we know the exact location, we can bypass the mount check
        video_path = os.path.join(NAS_PATH, video_filename)
        
        if not os.path.exists(video_path):
            logger.error(f"Could not find video file at: {video_path}")
            logger.info("Please verify the correct path and mount point")
            return
        
        logger.info(f"Starting transcription for video: {video_path}")
        logger.info(f"Video size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
        logger.info(f"Using batch size: {BATCH_SIZE}")
        logger.info(f"Using {NUM_WORKERS} CPU workers")
        
        # Check available system resources
        import psutil
        logger.info(f"Available memory: {psutil.virtual_memory().available / (1024*1024):.2f} MB")
        logger.info(f"CPU usage: {psutil.cpu_percent()}%")
        
        import time
        start_time = time.time()
        
        # Use the new service layer
        transcription_service = TranscriptionService()
        result = transcription_service.transcribe_file(video_path)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result and result.get('output_path'):
            logger.info(f"Transcription completed successfully in {duration/60:.2f} minutes")
            logger.info(f"SRT file saved at: {result['output_path']}")
            
            # Verify the SRT file exists and has content
            srt_path = result['output_path']
            if os.path.exists(srt_path):
                srt_size = os.path.getsize(srt_path)
                logger.info(f"SRT file size: {srt_size} bytes")
                if srt_size == 0:
                    logger.error("SRT file is empty!")
            else:
                logger.error("SRT file was not created!")
        else:
            logger.error(f"Transcription failed after {duration/60:.2f} minutes")
            logger.error(f"Error details: {result}")
            
    except Exception as e:
        logger.exception("Unexpected error during transcription:")
        raise

if __name__ == "__main__":
    main()