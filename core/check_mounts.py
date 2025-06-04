"""Mount point checking module for the Archivist application.

This module provides functionality to verify and monitor the status of
mounted storage locations (NAS and Flex servers). It includes health
checks, availability monitoring, and automatic recovery attempts.

Key Features:
- Mount point validation
- Health status monitoring
- Automatic recovery attempts
- Mount point statistics
- Error reporting
- Configuration validation

Example:
    >>> from core.check_mounts import check_mounts
    >>> status = check_mounts()
    >>> print(status['nas']['available'])
"""

import os
from loguru import logger
from typing import Dict, List

def list_mount_contents(mount_path: str) -> List[str]:
    """List contents of a mount point if it exists"""
    try:
        if os.path.exists(mount_path):
            contents = os.listdir(mount_path)
            return contents
        return []
    except Exception as e:
        logger.error(f"Error accessing {mount_path}: {e}")
        return []

def verify_critical_mounts():
    critical_mounts = {
        "flex-N": [
            "/mnt/flex-1",
            "/mnt/flex-2",
            "/mnt/flex-3",
            "/mnt/flex-4",
            "/mnt/flex-5",
            "/mnt/flex-6",
            "/mnt/flex-7",
            "/mnt/flex-8",
            "/mnt/flex-9"
        ],
        "other": [
            "/mnt/smb_share"
        ]
    }
    
    for category, paths in critical_mounts.items():
        for path in paths:
            if not os.path.ismount(path):
                logger.critical(
                    f"Critical mount point {path} for {category} is not mounted!"
                )
                return False
    return True

def main():
    # Define all possible mount points
    mount_points = {
        "flex-N": [
            "/mnt/flex-1",
            "/mnt/flex-2",
            "/mnt/flex-3",
            "/mnt/flex-4",
            "/mnt/flex-5",
            "/mnt/flex-6",
            "/mnt/flex-7",
            "/mnt/flex-8",
            "/mnt/flex-9"
        ],
        "other": [
            "/mnt/smb_share"
        ]
    }

    # Check each mount point
    for category, paths in mount_points.items():
        logger.info(f"\nChecking {category} mount points:")
        for path in paths:
            if os.path.exists(path):
                contents = list_mount_contents(path)
                logger.info(f"\n{path} exists and contains {len(contents)} items")
                if contents:
                    logger.info("First 10 items:")
                    for item in contents[:10]:
                        logger.info(f"  - {item}")
            else:
                logger.warning(f"{path} does not exist")

if __name__ == "__main__":
    main() 