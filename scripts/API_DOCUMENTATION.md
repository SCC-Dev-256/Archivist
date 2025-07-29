# Archivist API Documentation

## Overview
This document provides comprehensive documentation for the Archivist system API endpoints.

## Base URL
```
http://localhost:5050
```

## Authentication
The API uses CSRF token authentication for POST/PUT/DELETE requests.

### Getting CSRF Token
```bash
GET /api/csrf-token
```

**Response:**
```json
{
  "csrf_token": "ImM2ZDE3YWY5ZDc4OTljY2Y0M2U0OGJkMzY3Nzg2NWFkNGJkY2JiMjYi.aIgcWQ.h84N1eaQzNApmX_gAHK7IWjuVOo"
}
```

**Usage:**
```bash
# Get CSRF token
curl -s http://localhost:5050/api/csrf-token

# Use token in subsequent requests
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"video_path": "/path/to/video.mp4"}' \
  http://localhost:5050/api/transcribe
```

## Rate Limiting
- **Daily Limit**: 200 requests per day
- **Hourly Limit**: 50 requests per hour
- **Queue Operations**: 10 requests per minute

## Endpoints

### 1. File Browser API

#### **Browse Files**
```bash
GET /api/browse?path={directory_path}
```

**Parameters:**
- `path` (optional): Directory path to browse. If empty, shows NAS root.

**Response:**
```json
{
  "items": [
    {
      "is_dir": true,
      "modified_at": "2025-07-24T10:50:11.957045",
      "name": "flex-5",
      "path": "flex-5",
      "size": null
    },
    {
      "is_dir": false,
      "modified_at": "2024-12-31T11:34:06.410305",
      "name": "video.mp4",
      "path": "flex-5/video.mp4",
      "size": 1024000
    }
  ],
  "path": "/mnt"
}
```

**Example:**
```bash
# Browse root directory
curl -s http://localhost:5050/api/browse

# Browse specific directory
curl -s "http://localhost:5050/api/browse?path=flex-5"
```

#### **Get Transcriptions**
```bash
GET /api/transcriptions
```

**Response:**
```json
[
  {
    "id": 1,
    "video_path": "/mnt/flex-5/video.mp4",
    "completed_at": "2025-07-28T20:00:00",
    "status": "completed",
    "output_path": "/opt/Archivist/output/video.srt"
  }
]
```

#### **Get Member Cities**
```bash
GET /api/member-cities
```

**Response:**
```json
{
  "success": true,
  "data": {
    "member_cities": {
      "flex-1": {"name": "City 1", "path": "/mnt/flex-1"},
      "flex-2": {"name": "City 2", "path": "/mnt/flex-2"}
    },
    "total_cities": 2
  }
}
```

### 2. Queue Management API

#### **Get Queue Status**
```bash
GET /api/queue
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "task-uuid-123",
      "name": "run_whisper_transcription",
      "status": "processing",
      "progress": 45,
      "status_message": "Transcribing video...",
      "video_path": "/mnt/flex-5/video.mp4",
      "worker": "transcription-worker@hostname",
      "created_at": 1640995200,
      "started_at": 1640995200
    }
  ],
  "queue_status": {
    "active_workers": 1,
    "completed_jobs": 0,
    "queue_length": 1,
    "status": "operational",
    "total_workers": 1,
    "worker_status": "healthy"
  }
}
```

#### **Queue Job for Transcription**
```bash
POST /api/transcribe
```

**Request Body:**
```json
{
  "video_path": "/mnt/flex-5/video.mp4"
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "task-uuid-123",
  "message": "Job queued successfully"
}
```

#### **Batch Queue Jobs**
```bash
POST /api/transcribe/batch
```

**Request Body:**
```json
{
  "video_paths": [
    "/mnt/flex-5/video1.mp4",
    "/mnt/flex-5/video2.mp4"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "job_ids": ["task-uuid-123", "task-uuid-456"],
  "message": "2 jobs queued successfully"
}
```

#### **Reorder Queue**
```bash
POST /api/queue/reorder
```

**Request Body:**
```json
{
  "job_id": "task-uuid-123",
  "position": 0
}
```

**Response:**
```json
{
  "message": "Job reordered successfully"
}
```

#### **Stop Job**
```bash
POST /api/queue/stop/{job_id}
```

**Response:**
```json
{
  "message": "Job stopped successfully"
}
```

#### **Pause Job**
```bash
POST /api/queue/pause/{job_id}
```

**Response:**
```json
{
  "message": "Job paused successfully"
}
```

#### **Resume Job**
```bash
POST /api/queue/resume/{job_id}
```

**Response:**
```json
{
  "message": "Job resumed successfully"
}
```

#### **Remove Job**
```bash
POST /api/queue/remove/{job_id}
```

**Response:**
```json
{
  "message": "Job removed successfully"
}
```

#### **Get Job Status**
```bash
GET /api/status/{job_id}
```

**Response:**
```json
{
  "id": "task-uuid-123",
  "status": "processing",
  "progress": 45,
  "status_message": "Transcribing video...",
  "video_path": "/mnt/flex-5/video.mp4",
  "created_at": 1640995200,
  "started_at": 1640995200
}
```

### 3. VOD Management API

#### **Get VOD Content**
```bash
GET /api/vod/content
```

**Response:**
```json
{
  "success": true,
  "data": {
    "vods": [
      {
        "id": 1,
        "title": "City Council Meeting",
        "show_id": 12345,
        "status": "published",
        "created_at": "2025-07-28T20:00:00"
      }
    ]
  }
}
```

#### **Publish VOD**
```bash
POST /api/vod/publish
```

**Request Body:**
```json
{
  "show_id": 12345,
  "title": "City Council Meeting",
  "description": "Monthly city council meeting"
}
```

**Response:**
```json
{
  "success": true,
  "message": "VOD published successfully",
  "vod_id": 1
}
```

### 4. System Status API

#### **Health Check**
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-28T20:00:00",
  "services": {
    "redis": "healthy",
    "database": "healthy",
    "celery": "healthy"
  }
}
```

## Error Responses

### **400 Bad Request**
```json
{
  "error": "Invalid request data",
  "details": "Missing required field: video_path"
}
```

### **403 Forbidden**
```json
{
  "error": "CSRF token missing or invalid"
}
```

### **404 Not Found**
```json
{
  "error": "Resource not found",
  "details": "Job with ID task-uuid-123 not found"
}
```

### **429 Too Many Requests**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

### **500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "details": "Database connection failed"
}
```

## WebSocket Events

### **Connection**
```javascript
// Connect to Socket.IO
const socket = io('http://localhost:5050');

socket.on('connect', () => {
  console.log('Connected to server');
});
```

### **System Metrics**
```javascript
socket.on('system_metrics', (data) => {
  console.log('CPU:', data.cpu_percent);
  console.log('Memory:', data.memory_percent);
  console.log('Disk:', data.disk_usage);
});
```

### **Queue Updates**
```javascript
socket.on('queue_update', (data) => {
  console.log('Queue status:', data.queue_status);
  console.log('Active jobs:', data.jobs);
});
```

### **Job Progress**
```javascript
socket.on('job_progress', (data) => {
  console.log('Job ID:', data.job_id);
  console.log('Progress:', data.progress);
  console.log('Status:', data.status);
});
```

## Testing API Endpoints

### **Using curl**

#### **Test Basic Connectivity**
```bash
# Test CSRF token
curl -s http://localhost:5050/api/csrf-token

# Test queue status
curl -s http://localhost:5050/api/queue

# Test file browser
curl -s http://localhost:5050/api/browse
```

#### **Test Transcription**
```bash
# Get CSRF token
TOKEN=$(curl -s http://localhost:5050/api/csrf-token | jq -r '.csrf_token')

# Queue transcription job
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $TOKEN" \
  -d '{"video_path": "/mnt/flex-5/test.mp4"}' \
  http://localhost:5050/api/transcribe
```

### **Using Python**

#### **Basic API Client**
```python
import requests
import json

class ArchivistAPI:
    def __init__(self, base_url="http://localhost:5050"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
    
    def get_csrf_token(self):
        response = self.session.get(f"{self.base_url}/api/csrf-token")
        self.csrf_token = response.json()['csrf_token']
        return self.csrf_token
    
    def get_queue_status(self):
        response = self.session.get(f"{self.base_url}/api/queue")
        return response.json()
    
    def queue_transcription(self, video_path):
        if not self.csrf_token:
            self.get_csrf_token()
        
        headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': self.csrf_token
        }
        
        data = {'video_path': video_path}
        response = self.session.post(
            f"{self.base_url}/api/transcribe",
            headers=headers,
            json=data
        )
        return response.json()

# Usage
api = ArchivistAPI()
print(api.get_queue_status())
result = api.queue_transcription("/mnt/flex-5/test.mp4")
print(result)
```

## Monitoring and Logging

### **Log Files**
- **Application Logs**: `/opt/Archivist/logs/archivist.log`
- **Access Logs**: `/opt/Archivist/logs/access.log`
- **Error Logs**: `/opt/Archivist/logs/error.log`
- **Worker Logs**: `/opt/Archivist/logs/celery-worker.log`

### **Monitoring Commands**
```bash
# Monitor system health
python3 scripts/monitoring/unified_monitor.py --type all

# Monitor continuously
python3 scripts/monitoring/unified_monitor.py --continuous --interval 30

# Check specific components
python3 scripts/monitoring/unified_monitor.py --type api
python3 scripts/monitoring/unified_monitor.py --type system
```

## Security Considerations

### **CSRF Protection**
- All POST/PUT/DELETE requests require valid CSRF token
- Tokens expire after 1 hour
- Tokens are tied to user session

### **Rate Limiting**
- Prevents abuse and ensures fair usage
- Limits are configurable via environment variables
- Rate limit headers included in responses

### **Input Validation**
- All input is validated using Pydantic models
- Path traversal protection in file browser
- SQL injection protection via SQLAlchemy ORM

### **Error Handling**
- Sensitive information not exposed in error messages
- Proper HTTP status codes returned
- Detailed logging for debugging

## Performance Optimization

### **Caching**
- Redis-based caching for frequently accessed data
- Cache invalidation on data updates
- Configurable cache timeouts

### **Database Optimization**
- Connection pooling for database connections
- Query optimization and indexing
- Regular database maintenance

### **API Optimization**
- Pagination for large result sets
- Compression for large responses
- Efficient JSON serialization