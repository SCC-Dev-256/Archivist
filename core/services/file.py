"""File service for Archivist application.

This service provides a clean interface for all file-related operations,
including file management, mount checking, and storage operations.

Key Features:
- File system operations
- Mount point management
- File metadata extraction
- Storage validation
- Error handling and validation

Example:
    >>> from core.services import FileService
    >>> service = FileService()
    >>> files = service.browse_directory("/path/to/directory")
"""

import os
from typing import Dict, Optional, List
from loguru import logger
from core.exceptions import FileError, handle_file_error
from core.file_manager import file_manager
from core.check_mounts import verify_critical_mounts, list_mount_contents
from core.config import MOUNT_POINTS, NAS_PATH
from datetime import datetime

class FileService:
    """Service for handling file operations."""
    
    def __init__(self):
        self.mount_points = MOUNT_POINTS
        self.nas_path = NAS_PATH
    
    @handle_file_error
    def browse_directory(self, path: str, user: str = "default", location: str = "default") -> Dict:
        """Browse a directory and return its contents."""
        try:
            # Use the existing file manager for context
            file_manager.user = user
            file_manager.location = location

            # Directory listing logic (since file_manager has no browse_directory)
            if not os.path.exists(path):
                raise FileError(f"Directory not found: {path}")
            if not os.path.isdir(path):
                raise FileError(f"Not a directory: {path}")

            items = []
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                try:
                    # Get basic file info without blocking operations
                    is_dir = os.path.isdir(full_path)
                    modified_time = os.path.getmtime(full_path)
                    
                    # Only get file size for regular files, and only if it's fast
                    file_size = None
                    if not is_dir:
                        try:
                            # Use a quick stat call instead of getsize for better performance
                            stat_info = os.stat(full_path)
                            file_size = stat_info.st_size
                        except (OSError, IOError) as e:
                            # If we can't get size (e.g., network issues), skip it
                            logger.debug(f"Could not get size for {full_path}: {e}")
                            file_size = None
                    
                    items.append({
                        'name': entry,
                        'is_dir': is_dir,
                        'size': file_size,
                        'modified_at': datetime.fromtimestamp(modified_time).isoformat(),
                        'path': os.path.relpath(full_path, file_manager.base_path)
                    })
                except (OSError, IOError) as e:
                    # Skip files we can't access
                    logger.debug(f"Could not access {full_path}: {e}")
                    continue
                    
            logger.info(f"Browsed directory: {path} (found {len(items)} items)")
            return {'path': path, 'items': items}
        except Exception as e:
            logger.error(f"Failed to browse directory {path}: {e}")
            raise FileError(f"Directory browse failed: {str(e)}")
    
    @handle_file_error
    def get_file_details(self, file_path: str) -> Dict:
        """Get detailed information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file details
        """
        try:
            if not os.path.exists(file_path):
                raise FileError(f"File not found: {file_path}")
            
            details = file_manager.get_file_details(file_path)
            logger.info(f"Retrieved file details: {file_path}")
            return details
            
        except Exception as e:
            logger.error(f"Failed to get file details for {file_path}: {e}")
            raise FileError(f"File details retrieval failed: {str(e)}")
    
    @handle_file_error
    def check_mounts(self) -> Dict:
        """Check the status of all mount points.
        
        Returns:
            Dictionary containing mount status information
        """
        try:
            mount_status = {}
            
            for mount_name, mount_path in self.mount_points.items():
                try:
                    is_mounted = os.path.ismount(mount_path)
                    contents = list_mount_contents(mount_path) if is_mounted else []
                    
                    mount_status[mount_name] = {
                        'path': mount_path,
                        'mounted': is_mounted,
                        'accessible': os.access(mount_path, os.R_OK) if is_mounted else False,
                        'contents_count': len(contents),
                        'contents': contents[:10]  # Limit to first 10 items
                    }
                    
                except Exception as e:
                    mount_status[mount_name] = {
                        'path': mount_path,
                        'mounted': False,
                        'accessible': False,
                        'error': str(e)
                    }
            
            logger.info(f"Checked {len(mount_status)} mount points")
            return mount_status
            
        except Exception as e:
            logger.error(f"Failed to check mounts: {e}")
            raise FileError(f"Mount check failed: {str(e)}")
    
    @handle_file_error
    def verify_critical_mounts(self) -> bool:
        """Verify that all critical mount points are available.
        
        Returns:
            True if all critical mounts are available
        """
        try:
            result = verify_critical_mounts()
            logger.info(f"Critical mounts verification: {'PASSED' if result else 'FAILED'}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to verify critical mounts: {e}")
            raise FileError(f"Critical mount verification failed: {str(e)}")
    
    @handle_file_error
    def list_mount_contents(self, mount_path: str) -> List[str]:
        """List contents of a specific mount point.
        
        Args:
            mount_path: Path to the mount point
            
        Returns:
            List of file/directory names in the mount
        """
        try:
            contents = list_mount_contents(mount_path)
            logger.info(f"Listed contents of mount {mount_path}: {len(contents)} items")
            return contents
            
        except Exception as e:
            logger.error(f"Failed to list mount contents for {mount_path}: {e}")
            raise FileError(f"Mount contents listing failed: {str(e)}")
    
    @handle_file_error
    def validate_path(self, path: str, base_path: Optional[str] = None) -> bool:
        """Validate that a path is safe and accessible.
        
        Args:
            path: Path to validate
            base_path: Base path to validate against (defaults to NAS_PATH)
            
        Returns:
            True if path is valid and safe
        """
        try:
            base = base_path or self.nas_path
            
            # Check for path traversal attempts
            if '..' in path or path.startswith('/'):
                return False
            
            # Ensure path is within base directory
            full_path = os.path.abspath(os.path.join(base, path))
            if not full_path.startswith(os.path.abspath(base)):
                return False
            
            # Check if path exists and is accessible
            return os.path.exists(full_path) and os.access(full_path, os.R_OK)
            
        except Exception as e:
            logger.error(f"Path validation failed for {path}: {e}")
            return False
    
    @handle_file_error
    def get_storage_info(self) -> Dict:
        """Get information about storage usage and availability.
        
        Returns:
            Dictionary containing storage information
        """
        try:
            storage_info = {}
            
            for mount_name, mount_path in self.mount_points.items():
                try:
                    if os.path.exists(mount_path):
                        stat = os.statvfs(mount_path)
                        
                        total_bytes = stat.f_blocks * stat.f_frsize
                        free_bytes = stat.f_bavail * stat.f_frsize
                        used_bytes = total_bytes - free_bytes
                        
                        storage_info[mount_name] = {
                            'path': mount_path,
                            'total_gb': round(total_bytes / (1024**3), 2),
                            'used_gb': round(used_bytes / (1024**3), 2),
                            'free_gb': round(free_bytes / (1024**3), 2),
                            'usage_percent': round((used_bytes / total_bytes) * 100, 2),
                            'accessible': True
                        }
                    else:
                        storage_info[mount_name] = {
                            'path': mount_path,
                            'accessible': False,
                            'error': 'Mount point not found'
                        }
                        
                except Exception as e:
                    storage_info[mount_name] = {
                        'path': mount_path,
                        'accessible': False,
                        'error': str(e)
                    }
            
            logger.info(f"Retrieved storage info for {len(storage_info)} mount points")
            return storage_info
            
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            raise FileError(f"Storage info retrieval failed: {str(e)}")
    
    @handle_file_error
    def find_files(self, directory: str, pattern: str = "*", recursive: bool = False) -> List[str]:
        """Find files matching a pattern in a directory.
        
        Args:
            directory: Directory to search in
            pattern: File pattern to match (e.g., "*.mp4")
            recursive: Whether to search recursively
            
        Returns:
            List of matching file paths
        """
        try:
            if not os.path.exists(directory):
                raise FileError(f"Directory not found: {directory}")
            
            import glob
            
            if recursive:
                search_pattern = os.path.join(directory, "**", pattern)
                files = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(directory, pattern)
                files = glob.glob(search_pattern)
            
            # Filter out directories
            files = [f for f in files if os.path.isfile(f)]
            
            logger.info(f"Found {len(files)} files matching '{pattern}' in {directory}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to find files in {directory}: {e}")
            raise FileError(f"File search failed: {str(e)}")
    
    @handle_file_error
    def get_file_size(self, file_path: str) -> int:
        """Get the size of a file in bytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes
        """
        try:
            if not os.path.exists(file_path):
                raise FileError(f"File not found: {file_path}")
            
            size = os.path.getsize(file_path)
            logger.debug(f"File size for {file_path}: {size} bytes")
            return size
            
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {e}")
            raise FileError(f"File size retrieval failed: {str(e)}") 