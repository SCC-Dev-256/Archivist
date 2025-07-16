# VOD Processing System Documentation

## Overview

The VOD Processing System is a comprehensive solution for automatically processing Video on Demand (VOD) content from Cablecast systems. It provides direct access to VOD URLs, automatic captioning, video retranscoding with embedded captions, and quality validation.

## Key Features

### 🎯 Direct VOD URL Access
- **Automatic URL Extraction**: Extracts direct VOD URLs from Cablecast API responses
- **URL Pattern Recognition**: Constructs VOD URLs based on known patterns (e.g., `https://reflect-vod-scctv.cablecast.tv/store-12/21438-WBT-Board-Meeting-42125-v1/vod.mp4`)
- **Content Downloading**: Downloads VOD content directly from URLs for processing
- **Progress Tracking**: Monitors download progress with detailed logging

### 🏙️ City-Specific Processing
- **Member City Filtering**: Filters VODs by city-specific title patterns
- **Dedicated Storage**: Creates city-specific storage paths for processed content
- **Pattern Matching**: Maps city IDs to VOD title patterns for accurate filtering

### 📺 Automated Processing Pipeline
- **VOD Discovery**: Automatically finds recent VODs for each member city
- **Caption Generation**: Creates SCC caption files using WhisperX transcription
- **Video Retranscoding**: Embeds captions into video files using FFmpeg
- **Quality Validation**: Validates processed videos for integrity and quality
- **Upload Integration**: Uploads processed content back to Cablecast

### 🔄 Celery Task Management
- **Distributed Processing**: Uses Celery for scalable, distributed task processing
- **Task Scheduling**: Automated daily processing with configurable schedules
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **Progress Monitoring**: Real-time task progress tracking and logging

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cablecast     │    │   VOD Processing │    │   Archivist     │
│      API        │───▶│      System      │───▶│   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Direct VOD     │    │   Celery Tasks   │    │   Processed     │
│     URLs        │    │   & Workers      │    │   Content       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## VOD URL Access

### URL Pattern Recognition

The system automatically extracts VOD URLs using multiple strategies:

1. **Direct API Response**: Checks for direct URLs in Cablecast API responses
2. **Pattern Construction**: Builds URLs based on VOD ID and title patterns
3. **URL Validation**: Verifies URL accessibility before processing

**Example URL Pattern:**
```
https://reflect-vod-scctv.cablecast.tv/store-12/{vod_id}-{title}/vod.mp4
```

### City-Specific VOD Filtering

Each member city has specific title patterns for filtering relevant VODs:

| City ID | City Name | VOD Title Patterns |
|---------|-----------|-------------------|
| flex1 | Birchwood | birchwood, birch wood, birchwood city |
| flex2 | Dellwood/Grant/Willernie | dellwood, grant, willernie |
| flex3 | Lake Elmo | lake elmo, lakeelmo |
| flex4 | Mahtomedi | mahtomedi |
| flex7 | Oakdale | oakdale |
| flex8 | White Bear Lake | white bear lake, whitebearlake, wbl |
| flex9 | White Bear Township | white bear township, whitebeartownship, wbt |

## Celery Tasks

### Core Processing Tasks

#### `process_recent_vods`
- **Purpose**: Process most recent VODs for all member cities
- **Schedule**: Daily at 2:00 AM
- **Actions**:
  1. Discovers recent VODs for each city
  2. Filters by city-specific patterns
  3. Queues individual VOD processing tasks
  4. Sends summary alerts

#### `process_single_vod`
- **Purpose**: Process a single VOD through the complete pipeline
- **Actions**:
  1. Downloads VOD content from direct URL
  2. Generates SCC captions
  3. Retranscodes video with embedded captions
  4. Uploads processed content
  5. Validates quality

#### `download_vod_content`
- **Purpose**: Download VOD content from direct URLs
- **Features**:
  - Progress tracking
  - Timeout handling
  - File validation
  - Temporary storage management

#### `generate_vod_captions`
- **Purpose**: Generate SCC caption files for VODs
- **Features**:
  - WhisperX transcription
  - SCC format conversion
  - City-specific storage

#### `retranscode_vod_with_captions`
- **Purpose**: Create videos with embedded captions
- **Features**:
  - FFmpeg processing
  - H.264 encoding
  - Caption embedding
  - Quality optimization

#### `upload_captioned_vod`
- **Purpose**: Upload processed content to Cablecast
- **Features**:
  - Video file upload
  - SCC caption upload
  - Metadata updates

#### `validate_vod_quality`
- **Purpose**: Validate processed video quality
- **Checks**:
  - File integrity
  - File size validation
  - Duration verification
  - Caption stream detection

#### `cleanup_temp_files`
- **Purpose**: Clean up temporary processing files
- **Features**:
  - Age-based cleanup
  - Multiple directory support
  - Safe deletion

## Configuration

### Environment Variables

```bash
# VOD Processing Configuration
VOD_PROCESSING_ENABLED=true
VOD_DOWNLOAD_TIMEOUT=1800
VOD_MAX_RETRIES=3
VOD_BATCH_SIZE=5

# Storage Configuration
VOD_TEMP_DIR=/tmp/vod_downloads
VOD_PROCESSED_DIR=/mnt/vod_processed

# Quality Settings
VOD_QUALITY_CRF=23
VOD_QUALITY_PRESET=medium
VOD_ENABLE_CAPTIONS=true

# City-Specific Settings
VOD_CITY_PATTERNS_ENABLED=true
VOD_AUTO_FILTERING=true
```

### Storage Structure

```
/mnt/
├── flex1/
│   └── vod_processed/
│       ├── vod_123_captioned.mp4
│       └── vod_123.scc
├── flex2/
│   └── vod_processed/
├── flex3/
│   └── vod_processed/
└── ...
```

## Usage Examples

### Manual VOD Processing

```python
from core.tasks.vod_processing import process_single_vod

# Process a specific VOD
result = process_single_vod.delay(vod_id=21438, city_id='flex9')
print(f"Task ID: {result.id}")
```

### Batch Processing

```python
from core.tasks.vod_processing import process_recent_vods

# Process all recent VODs
result = process_recent_vods.delay()
print(f"Batch processing started: {result.id}")
```

### Direct URL Download

```python
from core.tasks.vod_processing import download_vod_content_task

# Download specific VOD content
vod_url = "https://reflect-vod-scctv.cablecast.tv/store-12/21438-WBT-Board-Meeting-42125-v1/vod.mp4"
result = download_vod_content_task.delay(vod_id=21438, vod_url=vod_url, city_id='flex9')
```

## Monitoring and Alerts

### Task Monitoring

```bash
# Monitor Celery workers
celery -A core.tasks worker --loglevel=info

# Monitor scheduled tasks
celery -A core.tasks beat --loglevel=info

# Check task status
celery -A core.tasks inspect active
```

### Alert Types

- **Info**: Processing completed successfully
- **Warning**: Processing issues (retries, timeouts)
- **Error**: Processing failures requiring attention

### Log Files

- **Application Logs**: `/var/log/archivist/vod_processing.log`
- **Celery Logs**: `/var/log/archivist/celery.log`
- **Error Logs**: `/var/log/archivist/errors.log`

## Troubleshooting

### Common Issues

#### VOD URL Access Issues
```bash
# Test URL accessibility
curl -I "https://reflect-vod-scctv.cablecast.tv/store-12/21438-WBT-Board-Meeting-42125-v1/vod.mp4"

# Check network connectivity
ping reflect-vod-scctv.cablecast.tv
```

#### Download Failures
```bash
# Check disk space
df -h /tmp/vod_downloads

# Check file permissions
ls -la /tmp/vod_downloads
```

#### Processing Failures
```bash
# Check Celery worker status
celery -A core.tasks inspect stats

# Check task results
celery -A core.tasks inspect reserved
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export VOD_DEBUG_MODE=true

# Run with verbose output
celery -A core.tasks worker --loglevel=debug
```

## Integration with Existing Systems

### Cablecast Integration
- **API Compatibility**: Works with existing Cablecast API endpoints
- **Authentication**: Uses HTTP Basic Authentication
- **Data Sync**: Maintains synchronization with Cablecast database

### Transcription Service
- **WhisperX Integration**: Uses existing WhisperX transcription service
- **SCC Generation**: Converts transcriptions to SCC format
- **Quality Assurance**: Validates transcription quality

### File Management
- **Storage Integration**: Uses existing file management system
- **Path Management**: Integrates with member city storage paths
- **Cleanup Integration**: Coordinates with existing cleanup processes

## Performance Optimization

### Processing Optimization
- **Parallel Processing**: Multiple VODs processed simultaneously
- **Resource Management**: Efficient memory and CPU usage
- **Timeout Handling**: Prevents hanging processes

### Storage Optimization
- **Temporary Cleanup**: Automatic cleanup of temporary files
- **Compression**: Optimized video compression settings
- **Deduplication**: Avoids reprocessing existing content

### Network Optimization
- **Connection Pooling**: Efficient HTTP connection management
- **Retry Logic**: Intelligent retry mechanisms for network issues
- **Progress Tracking**: Real-time download progress monitoring

## Security Considerations

### Data Protection
- **Secure Downloads**: HTTPS-only VOD URL access
- **Temporary Storage**: Secure handling of temporary files
- **Access Control**: Proper file permissions and access controls

### API Security
- **Authentication**: Secure Cablecast API authentication
- **Rate Limiting**: Respects API rate limits
- **Error Handling**: Secure error message handling

## Future Enhancements

### Planned Features
- **Advanced Filtering**: Machine learning-based VOD filtering
- **Quality Metrics**: Enhanced quality assessment algorithms
- **Batch Optimization**: Improved batch processing efficiency
- **Real-time Monitoring**: Web-based monitoring dashboard

### Scalability Improvements
- **Horizontal Scaling**: Multiple worker support
- **Load Balancing**: Intelligent task distribution
- **Resource Optimization**: Dynamic resource allocation

## Support and Maintenance

### Regular Maintenance
- **Log Rotation**: Automatic log file rotation
- **Storage Cleanup**: Regular temporary file cleanup
- **Performance Monitoring**: Regular performance assessment

### Backup and Recovery
- **Configuration Backup**: Regular configuration backups
- **Data Recovery**: Recovery procedures for processing failures
- **Disaster Recovery**: Complete system recovery procedures

## Conclusion

The VOD Processing System provides a robust, scalable solution for automated VOD content processing. With direct URL access, city-specific filtering, and comprehensive processing capabilities, it enables efficient management of VOD content across all member cities.

For additional support or questions, refer to the troubleshooting section or contact the development team. 