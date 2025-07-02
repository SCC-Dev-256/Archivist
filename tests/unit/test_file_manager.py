import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from core.file_manager import FileManager, file_manager

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing"""
    return tmp_path

@pytest.fixture
def mock_mount_points(temp_dir):
    """Mock mount points configuration"""
    return {
        'nas': str(temp_dir),
        'flex1': str(temp_dir / 'flex1'),
        'flex2': str(temp_dir / 'flex2')
    }

@pytest.fixture
def mock_flex_paths(temp_dir):
    """Mock flex paths configuration"""
    return {
        'flex1': str(temp_dir / 'flex1'),
        'flex2': str(temp_dir / 'flex2')
    }

@pytest.fixture
def mock_locations():
    """Mock locations configuration"""
    return {
        'default': {
            'name': 'Default Location',
            'allowed_users': ['*'],
            'flex_servers': ['flex1', 'flex2']
        },
        'restricted': {
            'name': 'Restricted Location',
            'allowed_users': ['admin'],
            'flex_servers': ['flex1']
        }
    }

@pytest.fixture
def file_manager_instance(temp_dir, mock_mount_points, mock_flex_paths, mock_locations):
    """Create a FileManager instance with mocked configurations"""
    with patch('core.file_manager.MOUNT_POINTS', mock_mount_points), \
         patch('core.file_manager.FLEX_PATHS', mock_flex_paths), \
         patch('core.file_manager.LOCATIONS', mock_locations), \
         patch('core.file_manager.NAS_PATH', str(temp_dir)):
        manager = FileManager()
        manager.location = 'default'  # Set default location
        return manager

def test_init_file_manager(file_manager_instance, temp_dir):
    """Test FileManager initialization"""
    assert file_manager_instance.base_path == str(temp_dir)
    assert file_manager_instance.location == 'default'
    assert file_manager_instance.user is None

def test_validate_location_access(file_manager_instance, mock_locations):
    """Test location access validation"""
    # Test with no user (should pass)
    file_manager_instance._validate_location_access()
    
    # Test with user having access
    file_manager_instance.user = 'admin'
    file_manager_instance.location = 'restricted'
    file_manager_instance._validate_location_access()
    
    # Test with user without access
    file_manager_instance.user = 'regular_user'
    with pytest.raises(PermissionError):
        file_manager_instance._validate_location_access()

def test_get_accessible_mounts(file_manager_instance, mock_mount_points):
    """Test getting accessible mount points"""
    # Test with default location
    mounts = file_manager_instance.get_accessible_mounts()
    assert 'nas' in mounts
    assert 'flex1' in mounts
    assert 'flex2' in mounts
    
    # Test with restricted location
    file_manager_instance.location = 'restricted'
    file_manager_instance.user = 'admin'  # Set admin user for restricted access
    mounts = file_manager_instance.get_accessible_mounts()
    assert 'nas' in mounts
    assert 'flex1' in mounts
    assert 'flex2' not in mounts

def test_get_file_details(file_manager_instance, temp_dir):
    """Test getting file details"""
    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    
    # Mock magic.Magic
    with patch('magic.Magic') as mock_magic:
        mock_magic_instance = MagicMock()
        mock_magic.return_value = mock_magic_instance
        mock_magic_instance.from_file.return_value = 'text/plain'
        
        # Test getting file details
        details = file_manager_instance.get_file_details(str(test_file))
        assert details['name'] == 'test.txt'
        assert details['type'] == 'text/plain'
        assert details['size'] == len("test content")
        assert isinstance(details['created_at'], str)
        assert isinstance(details['modified_at'], str)

def test_get_file_details_video(file_manager_instance, temp_dir):
    """Test getting video file details"""
    # Create a test video file
    test_video = temp_dir / "test.mp4"
    test_video.write_text("fake video content")
    
    # Mock magic.Magic
    with patch('magic.Magic') as mock_magic, \
         patch('subprocess.run') as mock_subprocess:
        mock_magic_instance = MagicMock()
        mock_magic.return_value = mock_magic_instance
        mock_magic_instance.from_file.return_value = 'video/mp4'
        
        # Mock ffprobe output
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                'format': {'duration': '120'},
                'streams': [{'codec_type': 'video'}]
            })
        )
        
        # Test getting video details
        details = file_manager_instance.get_file_details(str(test_video))
        assert details['name'] == 'test.mp4'
        assert details['type'] == 'video/mp4'
        assert 'metadata' in details
        assert details['metadata']['format']['duration'] == '120'

def test_list_mount_points(file_manager_instance, mock_mount_points):
    """Test listing mount points"""
    mount_info = file_manager_instance.list_mount_points()
    assert 'nas' in mount_info
    assert 'flex1' in mount_info
    assert 'flex2' in mount_info
    
    for mount_name, info in mount_info.items():
        assert 'path' in info
        assert 'exists' in info
        assert 'type' in info
        assert 'location' in info

def test_list_locations(file_manager_instance, mock_locations):
    """Test listing locations"""
    # Test with no user (should get all locations)
    locations = file_manager_instance.list_locations()
    assert locations == mock_locations
    
    # Test with admin user
    file_manager_instance.user = 'admin'
    locations = file_manager_instance.list_locations()
    assert 'default' in locations
    assert 'restricted' in locations
    
    # Test with regular user
    file_manager_instance.user = 'regular_user'
    locations = file_manager_instance.list_locations()
    assert 'default' in locations
    assert 'restricted' not in locations

def test_file_not_found(file_manager_instance):
    """Test handling of non-existent files"""
    with pytest.raises(FileNotFoundError):
        file_manager_instance.get_file_details("nonexistent.txt")

def test_not_a_file(file_manager_instance, temp_dir):
    """Test handling of directories"""
    # Create a test directory
    test_dir = temp_dir / "test_dir"
    test_dir.mkdir()
    
    with pytest.raises(ValueError):
        file_manager_instance.get_file_details(str(test_dir)) 