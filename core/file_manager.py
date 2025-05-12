import os
from datetime import datetime
import magic
import json

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path

    def get_file_details(self, path):
        """Get detailed information about a file."""
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
        
        return {
            'name': os.path.basename(full_path),
            'path': path,
            'size': stats.st_size,
            'type': file_type,
            'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
            'modified_at': datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'metadata': metadata
        }
    
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

# Create a singleton instance
file_manager = FileManager(os.getenv('NAS_PATH', '/mnt/nas')) 