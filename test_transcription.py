from core.transcription import run_whisperx
from loguru import logger
import sys
import os
import subprocess
from typing import List, Dict

def check_flex_mounts() -> Dict[str, List[str]]:
    """Check all Flex mount points and their duplicates"""
    mount_map = {}
    try:
        # Check all flex-N mount points
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
    # Video filename - updated to use the new file
    video_filename = "10845-1-Birchwood City Council (20160614).mpeg"
    
    # Since we know the exact location, we can bypass the mount check
    video_path = "/mnt/flex-1/" + video_filename
    
    if not os.path.exists(video_path):
        logger.error(f"Could not find video file at: {video_path}")
        logger.info("Please verify the correct path and mount point")
        return
    
    logger.info(f"Starting transcription for video: {video_path}")
    success, result = run_whisperx(video_path)
    
    if success:
        logger.info(f"Transcription completed successfully. SRT file saved at: {result}")
    else:
        logger.error(f"Transcription failed: {result}")

if __name__ == "__main__":
    main()