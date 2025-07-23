"""File management module for the Archivist application.

This module handles file system operations with support for multiple mount points
and location-based access control. It provides functionality for managing files
across different storage locations (NAS and Flex servers) with proper access
validation and metadata extraction.

Key Features:
- Multi-location file management (NAS and Flex servers)
- Location-based access control
- File metadata extraction
- Video file metadata support
- Mount point management
- File type detection

Example:
    >>> from core.file_manager import FileManager
    >>> manager = FileManager(user='admin', location='default')
    >>> file_details = manager.get_file_details('/path/to/file.mp4')
    >>> print(file_details['metadata'])
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List

import magic
from loguru import logger

from .config import FLEX_PATHS, LOCATIONS, MOUNT_POINTS, NAS_PATH


class FileManager:
    def __init__(self, base_path=None, user=None, location=None):
        """
        Initialize FileManager with a base path and optional user/location context.

        Args:
            base_path: Optional base path override
            user: Current user identifier
            location: Current location identifier
        """
        self.base_path = base_path or NAS_PATH
        self.mount_points = MOUNT_POINTS
        self.flex_paths = FLEX_PATHS
        self.user = user
        self.location = location or "default"
        self._validate_location_access()

    def _validate_location_access(self):
        """Validate that the current user has access to the specified location."""
        if not self.user:
            return  # No user context, no validation needed

        location_config = LOCATIONS.get(self.location)
        if not location_config:
            raise ValueError(f"Invalid location: {self.location}")

        allowed_users = location_config.get("allowed_users", ["*"])
        if "*" not in allowed_users and self.user not in allowed_users:
            raise PermissionError(
                f"User {self.user} does not have access to location {self.location}"
            )

    def get_accessible_mounts(self):
        """Get list of mount points accessible to the current user/location."""
        if not self.location:
            return self.mount_points

        location_config = LOCATIONS.get(self.location, {})
        allowed_cities = location_config.get("member_cities", [])

        accessible_mounts = {"nas": self.mount_points["nas"]}
        for city in allowed_cities:
            if city in self.mount_points:
                accessible_mounts[city] = self.mount_points[city]

        return accessible_mounts

    def get_city_info(self, city_id):
        """Get information about a specific member city."""
        from core.config import MEMBER_CITIES

        return MEMBER_CITIES.get(city_id, {})

    def get_all_cities(self):
        """Get information about all member cities."""
        from core.config import MEMBER_CITIES

        return MEMBER_CITIES

    def browse_directory(self, path: str) -> Dict[str, Any]:
        """Browse a directory and return file and directory listings.

        This implementation uses os.scandir with stat() to avoid expensive
        getsize() calls on network mounts.
        """
        full_path = path if os.path.isabs(path) else os.path.join(self.base_path, path)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Path not found: {path}")

        files: List[Dict[str, Any]] = []
        directories: List[Dict[str, Any]] = []

        with os.scandir(full_path) as it:
            for entry in it:
                try:
                    stat = entry.stat(follow_symlinks=False)
                    item = {
                        "name": entry.name,
                        "path": (
                            os.path.join(path, entry.name)
                            if not os.path.isabs(path)
                            else os.path.join(path, entry.name)
                        ),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:],
                    }
                    if entry.is_dir(follow_symlinks=False):
                        item["type"] = "directory"
                        directories.append(item)
                    else:
                        item["type"] = "file"
                        item["size"] = stat.st_size
                        files.append(item)
                except Exception as e:
                    logger.warning(f"Could not access {entry.path}: {e}")

        return {"path": path, "files": files, "directories": directories}

    def get_file_details(self, path):
        """Get detailed information about a file."""
        # Check if path starts with any accessible mount point
        full_path = None
        accessible_mounts = self.get_accessible_mounts()

        for mount_name, mount_path in accessible_mounts.items():
            if path.startswith(mount_path):
                full_path = path
                break

        # If no mount point found, join with base path
        if not full_path:
            full_path = os.path.join(self.base_path, path.lstrip("/"))

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        if not os.path.isfile(full_path):
            raise ValueError(f"Not a file: {path}")

        # Get basic file stats
        stats = os.stat(full_path)

        # Get file type using python-magic
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(full_path)

        # Try to get video metadata if it's a video file
        metadata = None
        if file_type.startswith("video/"):
            try:
                metadata = self._get_video_metadata(full_path)
            except Exception as e:
                logger.error(f"Error getting video metadata: {e}")

        # Determine which mount point this file belongs to
        mount_info = None
        for mount_name, mount_path in accessible_mounts.items():
            if full_path.startswith(mount_path):
                mount_info = {
                    "name": mount_name,
                    "path": mount_path,
                    "location": self.location,
                }
                break

        return {
            "name": os.path.basename(full_path),
            "path": path,
            "size": stats.st_size,
            "type": file_type,
            "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "metadata": metadata,
            "mount_info": mount_info,
            "location": self.location,
        }

    def list_mount_points(self):
        """Return information about all available mount points."""
        mount_info = {}
        accessible_mounts = self.get_accessible_mounts()

        for mount_name, mount_path in accessible_mounts.items():
            exists = os.path.exists(mount_path)
            mount_info[mount_name] = {
                "path": mount_path,
                "exists": exists,
                "type": "flex" if mount_name.startswith("flex") else "nas",
                "location": self.location,
            }
        return mount_info

    def list_locations(self):
        """Return information about available locations and their configurations."""
        if not self.user:
            return LOCATIONS

        accessible_locations = {}
        for loc_id, config in LOCATIONS.items():
            allowed_users = config.get("allowed_users", ["*"])
            if "*" in allowed_users or self.user in allowed_users:
                accessible_locations[loc_id] = config

        return accessible_locations

    def _get_video_metadata(self, file_path):
        """Get video metadata using ffprobe."""
        try:
            import subprocess

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Error getting video metadata: {e}")
        return None


# Create a singleton instance using NAS_PATH from config
file_manager = FileManager()
