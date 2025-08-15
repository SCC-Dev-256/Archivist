# Cablecast VOD Integration Documentation

## Overview

The Archivist system integrates with Cablecast VOD (Video on Demand) systems to provide automated content processing, transcription, and publishing workflows. This integration enables seamless content management between Archivist's transcription capabilities and Cablecast's VOD platform.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Archivist │    │   Cablecast  │    │     VOD     │
│  (Source)   │───▶│     API      │───▶│   System    │
└─────────────┘    └──────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│Transcription│    │   Content    │    │   Streaming │
│   Results   │    │  Management  │    │   & Embed   │
└─────────────┘    └──────────────┘    └─────────────┘
```

## Key Components

### 1. Cablecast API Client (`core/cablecast_client.py`)

Handles all communication with the Cablecast API system.

**Key Features:**
- Authentication and session management
- Show and VOD creation
- File upload and processing
- Status monitoring
- Metadata management

**Example Usage:**
```python
from core.cablecast_client import CablecastAPIClient

client = CablecastAPIClient()
shows = client.get_shows()
vods = client.get_vods(show_id=123)
```

### 2. VOD Content Manager (`core/vod_content_manager.py`)

Orchestrates the content flow from Archivist to the VOD system.

**Key Features:**
- Automatic content processing
- Transcription integration
- Metadata extraction
- Error handling and retry logic

**Example Usage:**
```python
from core.vod_content_manager import VODContentManager

manager = VODContentManager()
result = manager.process_archivist_content_for_vod("transcription_id_123")
```

### 3. VOD Automation (`core/vod_automation.py`)

Provides automated workflows for content publishing.

**Key Features:**
- Automatic publishing on transcription completion
- Queue-based processing
- Configurable automation triggers

### 4. Database Models

#### CablecastShowORM
```python
class CablecastShowORM(db.Model):
    __tablename__ = 'cablecast_shows'
    
    id = db.Column(db.Integer, primary_key=True)
    cablecast_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.Integer, nullable=True)
    transcription_id = db.Column(db.String(36), db.ForeignKey('transcription_results.id'))
```

#### CablecastVODORM
```python
class CablecastVODORM(db.Model):
    __tablename__ = 'cablecast_vods'
    
    id = db.Column(db.Integer, primary_key=True)
    show_id = db.Column(db.Integer, db.ForeignKey('cablecast_shows.id'))
    quality = db.Column(db.Integer, nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=True)
    vod_state = db.Column(db.String(50), nullable=False, default='processing')
```

## API Endpoints

### Content Publishing

#### POST `/api/vod/publish/<transcription_id>`
Publishes a transcription to the VOD system.

**Request:**
```json
{
  "quality": 1,
  "auto_transcribe": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Content published to VOD system",
  "data": {
    "show_id": 123,
    "vod_id": 456,
    "title": "Video Title",
    "transcription_id": "uuid-123"
  }
}
```

#### POST `/api/vod/batch-publish`
Batch publishes multiple transcriptions to the VOD system.

**Request:**
```json
{
  "transcription_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response:**
```json
{
  "status": "success",
  "published_count": 2,
  "error_count": 1,
  "results": [...],
  "errors": ["Failed to process uuid-3"]
}
```

### Content Management

#### GET `/api/cablecast/shows`
Retrieves all synced Cablecast shows.

**Response:**
```json
[
  {
    "id": 123,
    "title": "Show Title",
    "description": "Show Description",
    "duration": 3600,
    "transcription_available": true,
    "vod_count": 2
  }
]
```

#### POST `/api/cablecast/sync/shows`
Syncs shows from Cablecast to Archivist.

#### POST `/api/cablecast/sync/vods`
Syncs VODs from Cablecast to Archivist.

### Status and Monitoring

#### GET `/api/vod/sync-status`
Provides sync status between Archivist and VOD system.

**Response:**
```json
{
  "total_transcriptions": 100,
  "synced_transcriptions": 85,
  "sync_percentage": 85.0,
  "recent_syncs": [...]
}
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Cablecast API Configuration
CABLECAST_API_URL=https://your-cablecast-instance.com/api
CABLECAST_API_KEY=your_api_key_here
CABLECAST_LOCATION_ID=1

# VOD Integration Settings
AUTO_PUBLISH_TO_VOD=true
VOD_DEFAULT_QUALITY=1
VOD_UPLOAD_TIMEOUT=300
```

### Database Migration

Run the following migration to create the necessary tables:

```bash
flask db migrate -m "Add Cablecast VOD integration tables"
flask db upgrade
```

## Workflow Examples

### 1. Manual Content Publishing

```python
# Publish a single transcription to VOD
from core.vod_content_manager import VODContentManager

manager = VODContentManager()
result = manager.process_archivist_content_for_vod("transcription_uuid")
```

### 2. Automated Publishing

Enable automatic publishing by setting:
```bash
AUTO_PUBLISH_TO_VOD=true
```

This will automatically publish content to VOD when transcriptions are completed.

### 3. Batch Processing

```python
# Process multiple files
transcription_ids = ["uuid1", "uuid2", "uuid3"]
manager = VODContentManager()

for transcription_id in transcription_ids:
    result = manager.process_archivist_content_for_vod(transcription_id)
    print(f"Processed {transcription_id}: {result}")
```

## Error Handling

The integration includes comprehensive error handling:

### Common Errors and Solutions

1. **API Authentication Error**
   - Verify `CABLECAST_API_KEY` is correct
   - Check API key permissions

2. **File Upload Failures**
   - Verify file paths are accessible
   - Check network connectivity
   - Ensure file formats are supported

3. **VOD Processing Failures**
   - Monitor VOD status via API
   - Check Cablecast server logs
   - Verify transcoding settings

### Logging

All VOD operations are logged with appropriate levels:

```python
logger.info("Content published to VOD successfully")
logger.error("Failed to publish content to VOD")
logger.warning("VOD processing taking longer than expected")
```

## Monitoring and Metrics

### Key Metrics to Monitor

1. **Sync Status**
   - Total transcriptions vs synced count
   - Sync success rate
   - Processing time

2. **VOD Processing**
   - VOD creation success rate
   - Processing duration
   - Error rates

3. **API Performance**
   - Response times
   - Rate limiting
   - Connection errors

### Grafana Dashboards

The integration provides metrics for:
- VOD publishing success rate
- Content sync status
- API performance
- Error tracking

## Troubleshooting

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

### API Testing

Test Cablecast API connectivity:
```python
from core.cablecast_client import CablecastAPIClient

client = CablecastAPIClient()
shows = client.get_shows()
print(f"Found {len(shows)} shows")
```

### Common Issues

1. **Content not appearing in VOD**
   - Check VOD processing status
   - Verify file upload success
   - Review Cablecast logs

2. **Transcription sync failures**
   - Verify transcription exists in Archivist
   - Check database relationships
   - Review error logs

3. **API rate limiting**
   - Implement exponential backoff
   - Reduce batch sizes
   - Monitor API quotas

## Security Considerations

1. **API Key Management**
   - Store API keys securely
   - Rotate keys regularly
   - Use environment variables

2. **File Access**
   - Validate file paths
   - Implement access controls
   - Monitor file operations

3. **Data Privacy**
   - Encrypt sensitive data
   - Implement audit logging
   - Follow data retention policies

## Future Enhancements

1. **Advanced Metadata**
   - Automatic tagging
   - Content categorization
   - Search optimization

2. **Multi-Platform Support**
   - Additional VOD platforms
   - Cloud storage integration
   - CDN optimization

3. **Analytics Integration**
   - View tracking
   - Performance metrics
   - User engagement data

## Support

For issues related to the Cablecast VOD integration:

1. Check the logs for error messages
2. Verify configuration settings
3. Test API connectivity
4. Review Cablecast documentation
5. Contact system administrator

## Related Documentation

- [Cablecast API Documentation](Cablecast API not completed - Copy.pdf)
- [Archivist API Documentation](core/api_docs.py)
- [Database Schema](core/models.py)
- [Configuration Guide](core/config.py) 