# API Reference Guide

Complete reference documentation for the Archivist REST API, covering all endpoints, authentication methods, and usage examples.

## 🔐 Authentication

### API Key Authentication

Generate and use API keys for programmatic access:

```bash
# Generate API key
curl -X POST "http://localhost:8000/api/auth/apikey" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key", "description": "Automation access"}'

# Use API key in requests
curl -X GET "http://localhost:8000/api/transcriptions" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Session Authentication

For web-based applications using session cookies:

```bash
# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Subsequent requests use session cookie
curl -X GET "http://localhost:8000/api/transcriptions" \
  -H "Cookie: session=SESSION_ID"
```

## 📁 File Management API

### Browse Files

Get directory contents and file listings:

```bash
# Browse directory
GET /api/browse?path=/mnt/flex-1&user=admin&location=default

# Response
{
  "success": true,
  "data": {
    "path": "/mnt/flex-1",
    "files": [
      {
        "name": "video.mp4",
        "size": 1048576000,
        "type": "file",
        "modified": "2024-01-15T10:30:00Z",
        "permissions": "rw-r--r--"
      }
    ],
    "directories": [
      {
        "name": "transcriptions",
        "type": "directory",
        "modified": "2024-01-15T09:00:00Z",
        "permissions": "rwxr-xr-x"
      }
    ]
  }
}
```

### File Details

Get detailed information about a specific file:

```bash
# Get file details
GET /api/file-details?path=/mnt/flex-1/video.mp4

# Response
{
  "success": true,
  "data": {
    "path": "/mnt/flex-1/video.mp4",
    "size": 1048576000,
    "duration": 3600,
    "format": "mp4",
    "video_codec": "h264",
    "audio_codec": "aac",
    "resolution": "1920x1080",
    "bitrate": 2000000,
    "created": "2024-01-15T08:00:00Z",
    "modified": "2024-01-15T10:30:00Z",
    "transcription_status": "completed",
    "vod_status": "published"
  }
}
```

### Mount Points

List available mount points:

```bash
# List mount points
GET /api/mount-points

# Response
{
  "success": true,
  "data": {
    "mount_points": [
      {
        "path": "/mnt/flex-1",
        "name": "FLEX-1",
        "type": "nfs",
        "status": "mounted",
        "usage": {
          "total": 1099511627776,
          "used": 549755813888,
          "available": 549755813888,
          "percent": 50
        }
      }
    ]
  }
}
```

## 🎯 Transcription API

### Start Transcription

Initiate a new transcription job:

```bash
# Start transcription
POST /api/transcribe
Content-Type: application/json

{
  "path": "/mnt/flex-1/video.mp4",
  "language": "en",
  "model": "large-v2",
  "include_summary": true,
  "priority": "normal",
  "output_format": "scc"
}

# Response
{
  "success": true,
  "data": {
    "job_id": "uuid-123-456-789",
    "status": "queued",
    "position": 3,
    "estimated_duration": 1800,
    "created": "2024-01-15T10:30:00Z"
  }
}
```

### Batch Transcription

Process multiple files simultaneously:

```bash
# Batch transcription
POST /api/transcribe/batch
Content-Type: application/json

{
  "files": [
    "/mnt/flex-1/video1.mp4",
    "/mnt/flex-1/video2.mp4",
    "/mnt/flex-1/video3.mp4"
  ],
  "settings": {
    "language": "en",
    "model": "large-v2",
    "include_summary": true,
    "priority": "normal"
  }
}

# Response
{
  "success": true,
  "data": {
    "batch_id": "batch-uuid-123",
    "job_ids": [
      "uuid-123-456-789",
      "uuid-123-456-790",
      "uuid-123-456-791"
    ],
    "total_files": 3,
    "estimated_duration": 5400
  }
}
```

### Check Status

Monitor transcription job progress:

```bash
# Check job status
GET /api/status/{job_id}

# Response
{
  "success": true,
  "data": {
    "job_id": "uuid-123-456-789",
    "status": "processing",
    "progress": 45,
    "stage": "transcription",
    "estimated_remaining": 900,
    "started": "2024-01-15T10:35:00Z",
    "error": null
  }
}
```

### Get Results

Retrieve completed transcription results:

```bash
# Get transcription results
GET /api/results/{job_id}

# Response
{
  "success": true,
  "data": {
    "job_id": "uuid-123-456-789",
    "status": "completed",
    "input_file": "/mnt/flex-1/video.mp4",
    "output_files": {
      "scc": "/mnt/flex-1/transcriptions/video.scc",
      "summary": "/mnt/flex-1/transcriptions/video_summary.txt",
      "metadata": "/mnt/flex-1/transcriptions/video_metadata.json"
    },
    "duration": 3600,
    "processing_time": 1800,
    "completed": "2024-01-15T11:00:00Z"
  }
}
```

### List Transcriptions

Get list of transcription jobs:

```bash
# List transcriptions
GET /api/transcriptions?status=completed&limit=10&offset=0

# Response
{
  "success": true,
  "data": {
    "transcriptions": [
      {
        "id": "uuid-123-456-789",
        "filename": "video.mp4",
        "status": "completed",
        "created": "2024-01-15T10:30:00Z",
        "completed": "2024-01-15T11:00:00Z",
        "duration": 3600,
        "file_size": 1048576000
      }
    ],
    "pagination": {
      "total": 100,
      "limit": 10,
      "offset": 0,
      "has_next": true
    }
  }
}
```

## 🔄 Queue Management API

### Queue Status

Get current queue status:

```bash
# Get queue status
GET /api/queue/status

# Response
{
  "success": true,
  "data": {
    "queue_length": 5,
    "processing": 2,
    "completed": 15,
    "failed": 1,
    "active_jobs": [
      {
        "job_id": "uuid-123-456-789",
        "filename": "video.mp4",
        "status": "processing",
        "progress": 45,
        "started": "2024-01-15T10:35:00Z"
      }
    ]
  }
}
```

### Queue Control

Manage queue operations:

```bash
# Pause job
POST /api/queue/pause/{job_id}

# Resume job
POST /api/queue/resume/{job_id}

# Cancel job
DELETE /api/queue/cancel/{job_id}

# Reorder queue
POST /api/queue/reorder
Content-Type: application/json

{
  "job_id": "uuid-123-456-789",
  "position": 1
}
```

### Clear Queue

Remove completed or failed jobs:

```bash
# Clear completed jobs
DELETE /api/queue/clear-completed

# Clear failed jobs
DELETE /api/queue/clear-failed

# Clear all jobs
DELETE /api/queue/clear-all
```

## 📺 VOD Management API

### Publish to VOD

Publish transcription to VOD platform:

```bash
# Publish single transcription
POST /api/vod/publish/{transcription_id}
Content-Type: application/json

{
  "title": "City Council Meeting - Jan 15, 2024",
  "description": "Regular city council meeting",
  "tags": ["city council", "meeting", "public"],
  "quality": 1080,
  "enable_captions": true,
  "auto_transcribe": true
}

# Response
{
  "success": true,
  "data": {
    "vod_id": "vod-123-456",
    "url": "https://vod.example.com/watch/vod-123-456",
    "status": "published",
    "published_date": "2024-01-15T12:00:00Z"
  }
}
```

### Batch Publishing

Publish multiple transcriptions:

```bash
# Batch publish
POST /api/vod/batch-publish
Content-Type: application/json

{
  "transcription_ids": [
    "uuid-123-456-789",
    "uuid-123-456-790",
    "uuid-123-456-791"
  ],
  "settings": {
    "quality": 720,
    "enable_captions": true,
    "auto_generate_title": true,
    "auto_generate_description": true
  }
}

# Response
{
  "success": true,
  "data": {
    "batch_id": "vod-batch-123",
    "results": [
      {
        "transcription_id": "uuid-123-456-789",
        "status": "success",
        "vod_id": "vod-123-456"
      },
      {
        "transcription_id": "uuid-123-456-790",
        "status": "failed",
        "error": "File not found"
      }
    ]
  }
}
```

### VOD Status

Check VOD publishing status:

```bash
# Get VOD sync status
GET /api/vod/sync-status

# Response
{
  "success": true,
  "data": {
    "last_sync": "2024-01-15T11:00:00Z",
    "pending_publications": 3,
    "published_today": 8,
    "failed_publications": 1,
    "vod_platform_status": "online"
  }
}
```

## 🎬 Cablecast Integration API

### Show Management

Manage Cablecast shows:

```bash
# List shows
GET /api/cablecast/shows?limit=10&offset=0

# Response
{
  "success": true,
  "data": {
    "shows": [
      {
        "id": 123,
        "title": "City Council Meeting",
        "description": "Regular meeting",
        "category": "Government",
        "producer": "City of Example",
        "runtime": 3600,
        "created_date": "2024-01-15T08:00:00Z"
      }
    ],
    "pagination": {
      "total": 50,
      "limit": 10,
      "offset": 0
    }
  }
}
```

### Sync Operations

Synchronize data with Cablecast:

```bash
# Sync shows from Cablecast
POST /api/cablecast/sync/shows

# Sync VODs from Cablecast
POST /api/cablecast/sync/vods

# Response
{
  "success": true,
  "data": {
    "synced_count": 25,
    "new_items": 5,
    "updated_items": 20,
    "sync_time": "2024-01-15T12:00:00Z"
  }
}
```

### Link Transcriptions

Link transcriptions to Cablecast shows:

```bash
# Link transcription to show
POST /api/cablecast/link/{transcription_id}
Content-Type: application/json

{
  "show_id": 123,
  "auto_link": true,
  "create_vod": true
}

# Response
{
  "success": true,
  "data": {
    "transcription_id": "uuid-123-456-789",
    "show_id": 123,
    "vod_id": "vod-123-456",
    "linked_date": "2024-01-15T12:00:00Z"
  }
}
```

## 📊 System Information API

### Health Check

Check system health:

```bash
# System health
GET /api/health

# Response
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T12:00:00Z",
    "services": {
      "database": "healthy",
      "redis": "healthy",
      "storage": "healthy",
      "cablecast": "healthy",
      "vod": "healthy"
    },
    "version": "1.0.0"
  }
}
```

### System Statistics

Get system performance metrics:

```bash
# System stats
GET /api/stats

# Response
{
  "success": true,
  "data": {
    "uptime": 86400,
    "transcriptions": {
      "total": 1000,
      "completed": 950,
      "failed": 25,
      "processing": 5
    },
    "storage": {
      "total_space": 1099511627776,
      "used_space": 549755813888,
      "available_space": 549755813888
    },
    "performance": {
      "avg_transcription_time": 1800,
      "cpu_usage": 45.2,
      "memory_usage": 68.7,
      "disk_io": 12.5
    }
  }
}
```

### Storage Information

Get storage usage details:

```bash
# Storage info
GET /api/storage/info

# Response
{
  "success": true,
  "data": {
    "mount_points": [
      {
        "path": "/mnt/flex-1",
        "name": "FLEX-1",
        "total": 1099511627776,
        "used": 549755813888,
        "available": 549755813888,
        "percent": 50,
        "status": "healthy"
      }
    ],
    "total_storage": 5497558138880,
    "total_used": 2748779069440,
    "total_available": 2748779069440
  }
}
```

## 🔍 Search and Filter API

### Search Transcriptions

Search through transcription content:

```bash
# Search transcriptions
GET /api/search/transcriptions?q=budget&fields=content,title&limit=10

# Response
{
  "success": true,
  "data": {
    "results": [
      {
        "transcription_id": "uuid-123-456-789",
        "title": "City Council Meeting - Budget Discussion",
        "matches": [
          {
            "field": "content",
            "snippet": "...discussing the 2024 budget proposals...",
            "timestamp": "00:15:30"
          }
        ],
        "relevance_score": 0.85
      }
    ],
    "total_results": 15,
    "search_time": 0.045
  }
}
```

### Filter Content

Filter transcriptions by criteria:

```bash
# Filter transcriptions
GET /api/transcriptions?date_from=2024-01-01&date_to=2024-01-31&status=completed&tags=city-council

# Response
{
  "success": true,
  "data": {
    "transcriptions": [
      {
        "id": "uuid-123-456-789",
        "filename": "council_meeting.mp4",
        "status": "completed",
        "created": "2024-01-15T10:30:00Z",
        "tags": ["city-council", "meeting", "public"]
      }
    ],
    "filters_applied": {
      "date_from": "2024-01-01",
      "date_to": "2024-01-31",
      "status": "completed",
      "tags": ["city-council"]
    }
  }
}
```

## 📋 Admin API

### User Management

Manage user accounts and permissions:

```bash
# Create user
POST /api/admin/users
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "securepassword",
  "role": "operator"
}

# List users
GET /api/admin/users

# Update user
PUT /api/admin/users/{user_id}
Content-Type: application/json

{
  "role": "admin",
  "active": true
}

# Delete user
DELETE /api/admin/users/{user_id}
```

### Configuration Management

Manage system configuration:

```bash
# Get configuration
GET /api/admin/config

# Update configuration
PUT /api/admin/config
Content-Type: application/json

{
  "transcription": {
    "default_language": "en",
    "default_model": "large-v2",
    "max_concurrent_jobs": 4
  },
  "vod": {
    "auto_publish": true,
    "default_quality": 1080
  }
}
```

## 🔒 Error Handling

### Standard Error Response

All API endpoints return errors in a consistent format:

```json
{
  "success": false,
  "error": "File not found",
  "error_code": "FILE_NOT_FOUND",
  "details": {
    "path": "/mnt/flex-1/missing.mp4",
    "suggestion": "Check file path and permissions"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource conflict
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Codes

Common error codes and their meanings:

| Code | Description |
|------|-------------|
| `AUTH_REQUIRED` | Authentication required |
| `INVALID_API_KEY` | Invalid API key provided |
| `PERMISSION_DENIED` | Insufficient permissions |
| `FILE_NOT_FOUND` | Requested file not found |
| `INVALID_FILE_FORMAT` | Unsupported file format |
| `TRANSCRIPTION_FAILED` | Transcription processing failed |
| `STORAGE_FULL` | Storage space exceeded |
| `QUEUE_FULL` | Queue capacity exceeded |
| `VOD_PUBLISH_FAILED` | VOD publishing failed |
| `CABLECAST_ERROR` | Cablecast integration error |

## 📝 Usage Examples

### Complete Workflow Example

```bash
#!/bin/bash
# Complete workflow example

API_BASE="http://localhost:8000/api"
API_KEY="your-api-key-here"

# 1. Browse for files
echo "Browsing files..."
curl -X GET "$API_BASE/browse?path=/mnt/flex-1" \
  -H "Authorization: Bearer $API_KEY"

# 2. Start transcription
echo "Starting transcription..."
JOB_RESPONSE=$(curl -X POST "$API_BASE/transcribe" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/mnt/flex-1/video.mp4",
    "language": "en",
    "include_summary": true
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.data.job_id')
echo "Job ID: $JOB_ID"

# 3. Monitor progress
echo "Monitoring progress..."
while true; do
  STATUS=$(curl -X GET "$API_BASE/status/$JOB_ID" \
    -H "Authorization: Bearer $API_KEY" | jq -r '.data.status')
  
  if [ "$STATUS" = "completed" ]; then
    echo "Transcription completed!"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "Transcription failed!"
    exit 1
  fi
  
  sleep 30
done

# 4. Publish to VOD
echo "Publishing to VOD..."
curl -X POST "$API_BASE/vod/publish/$JOB_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "City Council Meeting",
    "quality": 1080,
    "enable_captions": true
  }'

echo "Workflow completed!"
```

### Batch Processing Example

```python
import requests
import json
import time

class ArchivistAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def batch_transcribe(self, file_paths, settings=None):
        """Start batch transcription"""
        data = {
            'files': file_paths,
            'settings': settings or {}
        }
        
        response = requests.post(
            f'{self.base_url}/transcribe/batch',
            headers=self.headers,
            json=data
        )
        
        return response.json()
    
    def monitor_jobs(self, job_ids):
        """Monitor multiple jobs"""
        completed = []
        failed = []
        
        while job_ids:
            for job_id in job_ids[:]:
                response = requests.get(
                    f'{self.base_url}/status/{job_id}',
                    headers=self.headers
                )
                
                status_data = response.json()
                status = status_data['data']['status']
                
                if status == 'completed':
                    completed.append(job_id)
                    job_ids.remove(job_id)
                elif status == 'failed':
                    failed.append(job_id)
                    job_ids.remove(job_id)
            
            if job_ids:
                time.sleep(30)
        
        return completed, failed

# Usage
api = ArchivistAPI('http://localhost:8000/api', 'your-api-key')

# Start batch transcription
files = [
    '/mnt/flex-1/meeting1.mp4',
    '/mnt/flex-1/meeting2.mp4',
    '/mnt/flex-1/meeting3.mp4'
]

batch_result = api.batch_transcribe(files, {
    'language': 'en',
    'include_summary': True
})

job_ids = batch_result['data']['job_ids']
completed, failed = api.monitor_jobs(job_ids)

print(f"Completed: {len(completed)}")
print(f"Failed: {len(failed)}")
```

## 📚 Rate Limiting

### Rate Limit Headers

All API responses include rate limiting headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642262400
```

### Rate Limit Policies

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| General API | 200 requests | 1 hour |
| Browse/File Info | 30 requests | 1 minute |
| Transcription | 10 requests | 1 minute |
| VOD Publishing | 5 requests | 1 minute |
| Admin Operations | 50 requests | 1 hour |

### Rate Limit Exceeded

When rate limits are exceeded, the API returns:

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 100,
    "reset_time": "2024-01-15T11:00:00Z"
  }
}
```

---

**This API reference provides complete documentation for all Archivist REST endpoints. For implementation examples and integration patterns, refer to the Integration Guide and User Manual.** 