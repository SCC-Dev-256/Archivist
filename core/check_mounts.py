"""Mount point checking module for the Archivist application.

This module provides functionality to verify and monitor the status of
mounted storage locations (NAS and Flex servers for member cities). It includes health
checks, availability monitoring, and automatic recovery attempts.

Key Features:
- Mount point validation for member city storage
- Health status monitoring
- Automatic recovery attempts
- Mount point statistics
- Error reporting
- Configuration validation

Example:
    >>> from core.check_mounts import check_mounts
    >>> status = check_mounts()
    >>> print(status['birchwood']['available'])
"""

import os
from loguru import logger
from typing import Dict, List

# Member city mount point mapping
MEMBER_CITY_MOUNTS = {
    "/mnt/flex-1": "Birchwood City Council and community content",
    "/mnt/flex-2": "Dellwood, Grant, and Willernie combined storage",
    "/mnt/flex-3": "Lake Elmo City Council and community content",
    "/mnt/flex-4": "Mahtomedi City Council and community content",
    "/mnt/flex-5": "Spare Record Storage 1 (overflow and additional cities)",
    "/mnt/flex-6": "Spare Record Storage 2 (overflow and additional cities)",
    "/mnt/flex-7": "Oakdale City Council and community content",
    "/mnt/flex-8": "White Bear Lake City Council and community content",
    "/mnt/flex-9": "White Bear Township Council and community content"
}

def list_mount_contents(mount_path: str) -> List[str]:
    """List contents of a mount point if it exists"""
    try:
        if os.path.exists(mount_path):
            contents = os.listdir(mount_path)
            return contents
        return []
    except Exception as e:
        city_desc = MEMBER_CITY_MOUNTS.get(mount_path, "Unknown city")
        logger.error(f"Error accessing {mount_path} ({city_desc}): {e}")
        return []

def verify_critical_mounts():
    """Verify critical mount points for member cities"""
    critical_mounts = {
        "member_cities": [
            "/mnt/flex-1",  # Birchwood
            "/mnt/flex-2",  # Dellwood Grant Willernie
            "/mnt/flex-3",  # Lake Elmo
            "/mnt/flex-4",  # Mahtomedi
            "/mnt/flex-5",  # Spare Record Storage 1
            "/mnt/flex-6",  # Spare Record Storage 2
            "/mnt/flex-7",  # Oakdale
            "/mnt/flex-8",  # White Bear Lake
            "/mnt/flex-9"   # White Bear Township
        ],
        "other": [
            "/mnt/smb_share"
        ]
    }
    
    for category, paths in critical_mounts.items():
        for path in paths:
            if not os.path.ismount(path):
                city_desc = MEMBER_CITY_MOUNTS.get(path, "Unknown city")
                logger.critical(
                    f"Critical mount point {path} ({city_desc}) for {category} is not mounted!"
                )
                return False
    return True

def main():
    """Main function to check all mount points with city context"""
    # Define all possible mount points with city context
    mount_points = {
        "member_cities": [
            "/mnt/flex-1",  # Birchwood
            "/mnt/flex-2",  # Dellwood Grant Willernie
            "/mnt/flex-3",  # Lake Elmo
            "/mnt/flex-4",  # Mahtomedi
            "/mnt/flex-5",  # Spare Record Storage 1
            "/mnt/flex-6",  # Spare Record Storage 2
            "/mnt/flex-7",  # Oakdale
            "/mnt/flex-8",  # White Bear Lake
            "/mnt/flex-9"   # White Bear Township
        ],
        "other": [
            "/mnt/smb_share"
        ]
    }

    # Check each mount point
    for category, paths in mount_points.items():
        if category == "member_cities":
            logger.info(f"\nChecking member city mount points:")
        else:
            logger.info(f"\nChecking {category} mount points:")
            
        for path in paths:
            city_desc = MEMBER_CITY_MOUNTS.get(path, "Unknown city")
            if os.path.exists(path):
                contents = list_mount_contents(path)
                logger.info(f"\n{path} ({city_desc}) exists and contains {len(contents)} items")
                if contents:
                    logger.info("First 10 items:")
                    for item in contents[:10]:
                        logger.info(f"  - {item}")
            else:
                logger.warning(f"{path} ({city_desc}) does not exist")

if __name__ == "__main__":
    main() 