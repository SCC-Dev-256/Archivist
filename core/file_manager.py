import os
from datetime import datetime
import magic
import json
from .config import MOUNT_POINTS, NAS_PATH, FLEX_PATHS, LOCATIONS

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
        self.location = location or 'default'
        self._validate_location_access()

    def _validate_location_access(self):
        """Validate that the current user has access to the specified location."""
        if not self.user:
            return  # No user context, no validation needed
            
        location_config = LOCATIONS.get(self.location)
        if not location_config:
            raise ValueError(f"Invalid location: {self.location}")
            
        allowed_users = location_config.get('allowed_users', ['*'])
        if '*' not in allowed_users and self.user not in allowed_users:
            raise PermissionError(f"User {self.user} does not have access to location {self.location}")

    def get_accessible_mounts(self):
        """Get list of mount points accessible to the current user/location."""
        if not self.location:
            return self.mount_points
            
        location_config = LOCATIONS.get(self.location, {})
        allowed_servers = location_config.get('flex_servers', list(self.flex_paths.keys()))
        
        accessible_mounts = {'nas': self.mount_points['nas']}
        for server in allowed_servers:
            if server in self.mount_points:
                accessible_mounts[server] = self.mount_points[server]
                
        return accessible_mounts

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
            full_path = os.path.join(self.base_path, path.lstrip('/'))
        
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
        if file_type.startswith('video/'):
            try:
                metadata = self._get_video_metadata(full_path)
            except Exception as e:
                print(f"Error getting video metadata: {e}")
        
        # Determine which mount point this file belongs to
        mount_info = None
        for mount_name, mount_path in accessible_mounts.items():
            if full_path.startswith(mount_path):
                mount_info = {
                    'name': mount_name,
                    'path': mount_path,
                    'location': self.location
                }
                break
        
        return {
            'name': os.path.basename(full_path),
            'path': path,
            'size': stats.st_size,
            'type': file_type,
            'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'metadata': metadata,
            'mount_info': mount_info,
            'location': self.location
        }

    def list_mount_points(self):
        """Return information about all available mount points."""
        mount_info = {}
        accessible_mounts = self.get_accessible_mounts()
        
        for mount_name, mount_path in accessible_mounts.items():
            exists = os.path.exists(mount_path)
            mount_info[mount_name] = {
                'path': mount_path,
                'exists': exists,
                'type': 'flex' if mount_name.startswith('flex') else 'nas',
                'location': self.location
            }
        return mount_info

    def list_locations(self):
        """Return information about available locations and their configurations."""
        if not self.user:
            return LOCATIONS
            
        accessible_locations = {}
        for loc_id, config in LOCATIONS.items():
            allowed_users = config.get('allowed_users', ['*'])
            if '*' in allowed_users or self.user in allowed_users:
                accessible_locations[loc_id] = config
                
        return accessible_locations

    def _get_video_metadata(self, file_path):
        """Get video metadata using ffprobe."""
        try:
            import subprocess
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"Error getting video metadata: {e}")
        return None

# Create a singleton instance using NAS_PATH from config
file_manager = FileManager() 