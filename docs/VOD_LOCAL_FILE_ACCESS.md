# VOD Local File Access Implementation

## Overview

The VOD processing system has been enhanced to prioritize local file access from mounted flex servers over downloading from Cablecast API URLs. This resolves the previous limitation where VOD files were not directly accessible via API endpoints.

**Status:** ✅ **FULLY IMPLEMENTED**  
**Date:** 2025-07-17  
**Implementation:** Enhanced VOD processing with local file prioritization

## Problem Solved

### ❌ **Previous Limitation: VOD File Access from Cablecast**
- **Issue:** VOD files were not directly accessible via API endpoints
- **Root Cause:** Cablecast system stores VODs in a format that doesn't expose direct download URLs
- **Impact:** Could not download actual video files for processing
- **Scope:** All VODs in the system (50+ VODs checked)

### ✅ **Solution: Local File Access from Mounted Drives**
- **Approach:** Prioritize local file access from mounted flex servers
- **Benefits:** Direct access to video files without API limitations
- **Performance:** Faster processing without download overhead
- **Reliability:** No dependency on external API availability

## Implementation Details

### 1. Enhanced File Path Resolution

The `get_vod_file_path()` function now prioritizes local file access:

```python
def get_vod_file_path(vod_data: Dict) -> Optional[str]:
    """Get VOD file path from local mounted drives or download if necessary.
    
    This function prioritizes local file access from mounted flex servers
    over downloading from Cablecast API URLs.
    """
```

#### Search Strategy:
1. **Mounted Drive Search:** Scan all flex server mounts for video files
2. **Pattern Matching:** Look for files by VOD ID, title, or common naming patterns
3. **Recursive Search:** Search through common video directories
4. **Fallback Download:** Only attempt API download if local file not found

### 2. Flex Server Integration

The system now integrates directly with mounted flex servers:

#### Mount Point Detection:
```python
for city_id, city_config in MEMBER_CITIES.items():
    mount_path = city_config.get('mount_path', f'/mnt/{city_id}')
    if mount_path and os.path.ismount(mount_path):
        # Search for VOD files
```

#### Common Directory Search:
- `/mnt/flex-*/videos/`
- `/mnt/flex-*/vod_content/`
- `/mnt/flex-*/city_council/`
- `/mnt/flex-*/meetings/`
- `/mnt/flex-*/content/`
- `/mnt/flex-*/recordings/`
- `/mnt/flex-*/broadcasts/`

### 3. File Discovery and Matching

#### File Pattern Matching:
```python
possible_files = [
    f"{vod_id}.mp4",
    f"{vod_id}.mov",
    f"{vod_id}.avi",
    f"{vod_id}.mkv",
    f"vod_{vod_id}.mp4",
    f"VOD_{vod_id}.mp4"
]

# Also check for files with title-based names
title = vod_data.get('title', '').replace(' ', '_').replace('/', '_')
if title:
    possible_files.extend([
        f"{title}.mp4",
        f"{title}.mov",
        f"{title}.avi",
        f"{title}.mkv"
    ])
```

#### Recursive Search:
- Searches through all subdirectories
- Matches files by VOD ID, title, or content
- Filters by video file extensions
- Validates file accessibility and size

### 4. Enhanced VOD Discovery

The `get_recent_vods_from_flex_server()` function provides comprehensive file discovery:

#### Features:
- **Mount Validation:** Checks if mount points are accessible
- **File Filtering:** Skips files smaller than 1MB (likely not videos)
- **Detailed Metadata:** Includes file size, modification time, relative path
- **Multiple Formats:** Supports .mp4, .mov, .avi, .mkv, .m4v, .wmv
- **Recursive Search:** Finds files in nested directories

#### Output Format:
```python
vod_entry = {
    'id': f"flex_{city_id}_{len(vod_files)}",
    'title': os.path.splitext(file)[0],
    'file_path': file_path,
    'file_size': file_size,
    'modified_time': mod_time,
    'source': 'flex_server',
    'city_id': city_id,
    'relative_path': os.path.relpath(file_path, mount_path),
    'directory': os.path.basename(os.path.dirname(file_path)),
    'extension': os.path.splitext(file)[1].lower()
}
```

## Processing Workflow

### 1. Local File Priority

```python
# Prioritize local file access from mounted drives
if video_path and os.path.exists(video_path):
    logger.info(f"Processing local file: {video_path}")
    local_video_path = video_path
else:
    # Try to find the file on mounted drives first
    logger.info(f"Searching for VOD {vod_id} on mounted drives")
    
    # Create a minimal VOD data structure for local file search
    vod_data = {
        'id': vod_id,
        'title': f"VOD_{vod_id}",
        'city_id': city_id
    }
    
    # Search for the file on mounted drives
    local_video_path = get_vod_file_path(vod_data)
```

### 2. Fallback Strategy

If local file not found:
1. **API Fallback:** Attempt to get VOD details from Cablecast API
2. **Download Fallback:** Only download if local file and API both fail
3. **Error Handling:** Graceful degradation with detailed error reporting

### 3. Processing Pipeline

Once a file is found:
1. **Validation:** Check file integrity and format
2. **Transcription:** Generate captions using WhisperX
3. **Retranscoding:** Embed captions into video
4. **Upload:** Upload processed content back to Cablecast (if applicable)

## Configuration

### Member Cities Configuration

The system uses the existing `MEMBER_CITIES` configuration:

```python
MEMBER_CITIES = {
    'flex1': {
        'name': 'Birchwood',
        'mount_path': '/mnt/flex-1',
        'patterns': ['birchwood', 'birch wood', 'birchwood city']
    },
    'flex2': {
        'name': 'Dellwood/Grant/Willernie',
        'mount_path': '/mnt/flex-2',
        'patterns': ['dellwood', 'grant', 'willernie']
    },
    # ... other cities
}
```

### Mount Point Requirements

Each flex server mount must be:
- **Mounted:** Available as a mount point
- **Readable:** Accessible for file reading
- **Stable:** Consistently available during processing

## Benefits Achieved

### 1. **Performance Improvements**
- **No Download Overhead:** Direct file access eliminates download time
- **Faster Processing:** Immediate access to video files
- **Reduced Bandwidth:** No need to download large video files
- **Parallel Processing:** Multiple files can be processed simultaneously

### 2. **Reliability Enhancements**
- **No API Dependency:** Works independently of Cablecast API availability
- **Offline Capability:** Can process files even when API is unavailable
- **Error Resilience:** Graceful handling of file access issues
- **Consistent Access:** Direct file system access is more reliable

### 3. **Operational Benefits**
- **Reduced Complexity:** Simpler file access without API integration
- **Better Monitoring:** Direct file system monitoring capabilities
- **Easier Debugging:** File access issues are easier to diagnose
- **Cost Reduction:** No bandwidth costs for file downloads

### 4. **Scalability Improvements**
- **Local Processing:** All processing happens on local infrastructure
- **No External Dependencies:** Reduced external service dependencies
- **Flexible Storage:** Can work with any mounted storage system
- **Extensible Architecture:** Easy to add new mount points

## Usage Examples

### 1. Processing a Local VOD File

```python
from core.tasks.vod_processing import process_single_vod

# Process a file directly from mounted drive
result = process_single_vod.delay(
    vod_id="flex_flex1_001",
    city_id="flex1",
    video_path="/mnt/flex-1/videos/city_council_meeting.mp4"
)
```

### 2. Discovering VODs on Flex Servers

```python
from core.tasks.vod_processing import get_recent_vods_from_flex_server

# Get recent VODs from a specific flex server
vods = get_recent_vods_from_flex_server(
    mount_path="/mnt/flex-1",
    city_id="flex1",
    limit=10
)

for vod in vods:
    print(f"Found VOD: {vod['title']} at {vod['file_path']}")
```

### 3. Batch Processing All Cities

```python
from core.tasks.vod_processing import process_recent_vods

# Process VODs for all member cities
result = process_recent_vods.delay()
```

## Monitoring and Logging

### Enhanced Logging

The system provides detailed logging for file discovery:

```python
logger.info(f"Found VOD file on mounted drive: {file_path}")
logger.info(f"Using local VOD file: {path}")
logger.warning(f"No VOD file found for VOD {vod_id} on any mounted drive")
```

### File Access Metrics

The system tracks:
- **Files Found:** Number of VOD files discovered on each mount
- **Access Success Rate:** Percentage of successful file accesses
- **Processing Time:** Time to find and access files
- **Error Rates:** File access failure rates

## Troubleshooting

### Common Issues

#### 1. Mount Point Not Accessible
```bash
# Check if mount point is mounted
mount | grep flex

# Check mount point permissions
ls -la /mnt/flex-1
```

#### 2. Files Not Found
```bash
# Check if video files exist
find /mnt/flex-1 -name "*.mp4" -type f

# Check file permissions
ls -la /mnt/flex-1/videos/
```

#### 3. Processing Failures
```python
# Check file accessibility
import os
file_path = "/mnt/flex-1/videos/example.mp4"
print(f"File exists: {os.path.exists(file_path)}")
print(f"File readable: {os.access(file_path, os.R_OK)}")
```

### Debug Mode

Enable debug logging for detailed file discovery:

```python
import logging
logging.getLogger('core.tasks.vod_processing').setLevel(logging.DEBUG)
```

## Future Enhancements

### Planned Improvements

1. **Intelligent File Matching:** AI-based file matching by content
2. **Automatic Mount Detection:** Dynamic mount point discovery
3. **File Deduplication:** Detect and handle duplicate files
4. **Content Fingerprinting:** Use video fingerprints for matching
5. **Distributed Processing:** Process files across multiple workers

### Integration Opportunities

1. **File System Monitoring:** Real-time file system change detection
2. **Content Management:** Integration with content management systems
3. **Metadata Extraction:** Enhanced metadata extraction from video files
4. **Quality Assessment:** Automatic video quality assessment
5. **Storage Optimization:** Intelligent storage management

## Conclusion

The enhanced VOD local file access implementation provides:

- ✅ **Direct File Access:** Immediate access to video files on mounted drives
- ✅ **No API Dependency:** Works independently of external API availability
- ✅ **Improved Performance:** Faster processing without download overhead
- ✅ **Enhanced Reliability:** More reliable file access through direct filesystem access
- ✅ **Better Scalability:** Can handle multiple mount points and file formats
- ✅ **Comprehensive Discovery:** Intelligent file discovery and matching

This implementation transforms the VOD processing system from API-dependent to locally-driven, providing a more robust and efficient solution for video processing workflows. 