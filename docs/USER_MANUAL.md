# Archivist User Manual

A comprehensive guide for operators to use the Archivist transcription and VOD management system.

## 📚 Table of Contents

1. [Getting Started](#getting-started)
2. [Web Interface Guide](#web-interface-guide)
3. [File Management](#file-management)
4. [Transcription Operations](#transcription-operations)
5. [VOD Management](#vod-management)
6. [Queue Management](#queue-management)
7. [System Administration](#system-administration)
8. [Troubleshooting](#troubleshooting)
9. [Command Reference](#command-reference)

## 🚀 Getting Started

### System Overview

The Archivist system provides:
- **Transcription Services**: Convert audio/video to text with SCC captions
- **VOD Integration**: Publish content to Cablecast and other VOD platforms
- **File Management**: Browse and manage content across multiple flex servers
- **Queue Management**: Monitor and control transcription jobs
- **Analytics**: Track performance and usage statistics

### Accessing the System

1. **Web Interface**: Navigate to `http://your-server-ip:8000`
2. **API Access**: Use REST API endpoints for automation
3. **Command Line**: SSH access for administrative tasks

### User Roles

- **Admin**: Full system access, configuration management
- **Operator**: Transcription and VOD operations
- **Viewer**: Read-only access to results and status

## 🖥️ Web Interface Guide

### Dashboard Overview

The main dashboard provides:
- **System Status**: Health indicators and alerts
- **Active Jobs**: Currently running transcriptions
- **Queue Summary**: Pending and completed jobs
- **Storage Usage**: Flex server utilization
- **Recent Activity**: Latest operations and results

### Navigation Menu

- **Home**: Dashboard and system overview
- **Browse**: File system navigation and management
- **Transcribe**: Start new transcription jobs
- **VOD**: Video-on-demand content management
- **Queue**: Job queue monitoring and control
- **Settings**: System configuration and preferences
- **Help**: Documentation and support resources

## 📁 File Management

### Accessing Flex Servers

The system provides access to multiple flex servers:

```
/mnt/flex-1/    # Primary content storage
/mnt/flex-2/    # Secondary/backup storage
/mnt/flex-3/    # Archive storage
/mnt/flex-4/    # Special projects
/mnt/flex-5/    # Test/development content
```

### Browsing Files

1. **Navigate to Browse Section**
   - Click "Browse" in the main menu
   - Select desired flex server from dropdown
   - Use breadcrumb navigation to navigate directories

2. **File Information**
   - File size and format details
   - Creation and modification dates
   - Transcription status indicators
   - VOD publishing status

3. **File Operations**
   - Preview media files
   - Download transcription files
   - View metadata and properties
   - Access related VOD content

### File Types and Formats

**Supported Input Formats:**
- **Video**: MP4, AVI, MOV, MKV, WMV
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Containers**: Most common container formats

**Generated Output Formats:**
- **SCC**: Scenarist Closed Caption files
- **TXT**: Plain text transcriptions
- **JSON**: Structured transcription data with timestamps
- **Summary**: AI-generated content summaries

## 🎯 Transcription Operations

### Starting a Transcription Job

#### Method 1: Web Interface

1. **Navigate to Transcribe Section**
   - Click "Transcribe" in main menu
   - Select "Start New Transcription"

2. **Select Source File**
   - Choose flex server location
   - Browse to target file
   - Verify file compatibility

3. **Configure Transcription Settings**
   ```
   Language: Auto-detect / English / Spanish / French
   Model: large-v2 (recommended)
   Quality: High / Medium / Fast
   Include Summary: Yes / No
   Output Format: SCC (default)
   ```

4. **Set Queue Options**
   - Priority: High / Normal / Low
   - Schedule: Now / Scheduled time
   - Notifications: Email / None

5. **Start Transcription**
   - Review settings summary
   - Click "Start Transcription"
   - Note job ID for tracking

#### Method 2: API Command

```bash
# Start transcription via API
curl -X POST "http://localhost:8000/api/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/mnt/flex-1/video.mp4",
    "language": "en",
    "model": "large-v2",
    "include_summary": true,
    "priority": "normal"
  }'
```

#### Method 3: Batch Processing

```bash
# Batch process multiple files
curl -X POST "http://localhost:8000/api/transcribe/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      "/mnt/flex-1/video1.mp4",
      "/mnt/flex-1/video2.mp4",
      "/mnt/flex-1/video3.mp4"
    ],
    "settings": {
      "language": "en",
      "model": "large-v2",
      "include_summary": true
    }
  }'
```

### Monitoring Transcription Progress

#### Web Interface Monitoring

1. **Queue Status Page**
   - View all active jobs
   - Real-time progress updates
   - Estimated completion times
   - Error status and details

2. **Job Detail View**
   - Click on job ID for details
   - Progress percentage and stage
   - Processing logs and messages
   - Resource usage statistics

#### API Status Checking

```bash
# Check specific job status
curl -X GET "http://localhost:8000/api/status/JOB_ID"

# Get all active jobs
curl -X GET "http://localhost:8000/api/queue/status"

# View job logs
curl -X GET "http://localhost:8000/api/logs/JOB_ID"
```

### Transcription Results

#### Accessing Results

1. **Web Interface**
   - Navigate to "Results" section
   - Search by filename or job ID
   - Filter by date range or status

2. **File Locations**
   ```
   /mnt/flex-N/transcriptions/
   ├── scc_files/           # SCC caption files
   ├── summaries/           # AI summaries
   ├── raw_transcripts/     # Raw transcription data
   └── metadata/            # Job metadata
   ```

3. **Download Options**
   - Individual files
   - Batch downloads
   - ZIP packages with all outputs

## 📺 VOD Management

### VOD Publishing Workflow

#### Single File Publishing

1. **Select Completed Transcription**
   - Navigate to transcription results
   - Click "Publish to VOD" button
   - Choose target VOD platform

2. **Configure VOD Settings**
   ```
   Platform: Cablecast
   Channel: Select from dropdown
   Title: Auto-generated or custom
   Description: From summary or custom
   Tags: Auto-tags or manual
   Quality: 1080p / 720p / 480p
   ```

3. **Publishing Options**
   - **Immediate**: Publish right away
   - **Scheduled**: Set publish date/time
   - **Draft**: Save as draft for review

#### Batch Publishing

1. **Select Multiple Transcriptions**
   - Use checkboxes to select items
   - Click "Batch Publish" button
   - Choose common settings

2. **Batch Configuration**
   ```
   Apply to All:
   - Platform settings
   - Quality settings
   - Tag templates
   - Scheduling options
   ```

3. **Review and Confirm**
   - Preview all selected items
   - Verify settings accuracy
   - Start batch processing

### Cablecast Integration

#### Connecting to Cablecast

1. **Configure API Connection**
   - Go to Settings → Integrations
   - Enter Cablecast server URL
   - Provide API credentials
   - Test connection

2. **Sync Cablecast Data**
   ```bash
   # Sync shows from Cablecast
   curl -X POST "http://localhost:8000/api/cablecast/sync/shows"
   
   # Sync VODs from Cablecast
   curl -X POST "http://localhost:8000/api/cablecast/sync/vods"
   ```

#### Show Management

1. **View Cablecast Shows**
   - Navigate to VOD → Shows
   - Browse imported shows
   - Filter by date or category

2. **Link Transcriptions to Shows**
   - Select transcription
   - Choose "Link to Show"
   - Select target show from list
   - Confirm linkage

3. **VOD Creation**
   - Linked transcriptions automatically create VODs
   - Monitor creation progress
   - Verify successful publishing

### VOD Content Management

#### Content Organization

```
VOD Content Structure:
├── Live Events/
│   ├── City Council Meetings
│   ├── Public Hearings
│   └── Community Events
├── Educational Content/
│   ├── Training Sessions
│   ├── Workshops
│   └── Presentations
└── Archives/
    ├── Historical Content
    ├── Seasonal Programs
    └── Special Collections
```

#### Metadata Management

1. **Auto-Generated Metadata**
   - Title from filename
   - Description from summary
   - Tags from content analysis
   - Timestamps from transcription

2. **Manual Metadata Enhancement**
   - Edit titles and descriptions
   - Add custom tags
   - Set categories and topics
   - Include speaker information

## 🔄 Queue Management

### Queue Overview

The transcription queue manages all processing jobs:

- **Pending**: Jobs waiting to start
- **Processing**: Currently running jobs
- **Completed**: Successfully finished jobs
- **Failed**: Jobs with errors
- **Cancelled**: User-cancelled jobs

### Queue Operations

#### Viewing Queue Status

1. **Web Interface**
   - Navigate to Queue section
   - View all job categories
   - Filter by status or date

2. **Queue Statistics**
   - Total jobs in queue
   - Average processing time
   - Success/failure rates
   - Resource utilization

#### Managing Queue Jobs

1. **Reorder Queue**
   - Drag and drop jobs
   - Set priority levels
   - Move urgent jobs to front

2. **Job Control**
   ```bash
   # Pause job
   curl -X POST "http://localhost:8000/api/queue/pause/JOB_ID"
   
   # Resume job
   curl -X POST "http://localhost:8000/api/queue/resume/JOB_ID"
   
   # Cancel job
   curl -X DELETE "http://localhost:8000/api/queue/cancel/JOB_ID"
   ```

3. **Batch Operations**
   - Pause all jobs
   - Resume processing
   - Clear completed jobs
   - Retry failed jobs

### Queue Optimization

#### Performance Tuning

1. **Adjust Worker Threads**
   ```bash
   # Increase worker threads for faster processing
   export NUM_WORKERS=8
   export BATCH_SIZE=32
   ```

2. **Queue Priorities**
   - High: Urgent/live content
   - Normal: Regular processing
   - Low: Archive/bulk processing

3. **Scheduling Options**
   - Off-peak processing
   - Resource-aware scheduling
   - Automatic retry policies

## ⚙️ System Administration

### User Management

#### Creating User Accounts

1. **Admin Interface**
   - Navigate to Settings → Users
   - Click "Add New User"
   - Enter user details
   - Assign roles and permissions

2. **User Roles Configuration**
   ```
   Administrator:
   - Full system access
   - Configuration management
   - User management
   
   Operator:
   - Transcription operations
   - VOD management
   - Queue management
   
   Viewer:
   - Read-only access
   - View results
   - Download files
   ```

#### API Key Management

1. **Generate API Keys**
   ```bash
   # Create API key
   curl -X POST "http://localhost:8000/api/auth/apikey" \
     -H "Content-Type: application/json" \
     -d '{"name": "Automation Key", "permissions": ["transcribe", "vod"]}'
   ```

2. **Manage API Keys**
   - View all active keys
   - Set expiration dates
   - Revoke compromised keys
   - Monitor key usage

### System Configuration

#### Basic Settings

1. **Transcription Settings**
   ```
   Default Language: English
   Default Model: large-v2
   Max Concurrent Jobs: 4
   Output Format: SCC
   Include Summaries: Yes
   ```

2. **VOD Settings**
   ```
   Auto-publish: Enabled
   Default Quality: 1080p
   Cablecast Integration: Enabled
   Batch Size: 10
   ```

3. **Storage Settings**
   ```
   Default Output Location: /mnt/flex-1/transcriptions
   Archive Location: /mnt/flex-3/archives
   Temp Directory: /tmp/archivist
   Max File Size: 10GB
   ```

#### Advanced Configuration

1. **Performance Tuning**
   - CPU core allocation
   - Memory limits
   - Disk I/O optimization
   - Network bandwidth management

2. **Security Settings**
   - Authentication methods
   - API rate limiting
   - Access control lists
   - Audit logging

### Monitoring and Alerts

#### System Health Monitoring

1. **Health Checks**
   ```bash
   # Check system health
   curl -X GET "http://localhost:8000/health"
   
   # Check mount points
   curl -X GET "http://localhost:8000/api/storage/health"
   
   # Check VOD integration
   curl -X GET "http://localhost:8000/api/vod/health"
   ```

2. **Resource Monitoring**
   - CPU usage by process
   - Memory consumption
   - Disk space utilization
   - Network activity

#### Alert Configuration

1. **Alert Types**
   - System resource warnings
   - Job failure notifications
   - VOD publishing errors
   - Storage capacity alerts

2. **Notification Methods**
   - Email notifications
   - Webhook integrations
   - Slack/Teams messaging
   - Dashboard alerts

### Backup and Recovery

#### Backup Procedures

1. **Database Backup**
   ```bash
   # Create database backup
   pg_dump archivist_db > backup_$(date +%Y%m%d).sql
   
   # Automated backup script
   0 2 * * * /opt/Archivist/scripts/backup_database.sh
   ```

2. **File System Backup**
   ```bash
   # Backup transcription files
   rsync -av /mnt/flex-*/transcriptions/ /backup/transcriptions/
   
   # Backup configuration files
   tar -czf config_backup.tar.gz /opt/Archivist/.env /opt/Archivist/config/
   ```

#### Recovery Procedures

1. **Database Recovery**
   ```bash
   # Restore from backup
   psql archivist_db < backup_20240115.sql
   
   # Verify restoration
   psql archivist_db -c "SELECT COUNT(*) FROM transcriptions;"
   ```

2. **File System Recovery**
   ```bash
   # Restore transcription files
   rsync -av /backup/transcriptions/ /mnt/flex-1/transcriptions/
   
   # Fix permissions
   chown -R archivist:transcription_users /mnt/flex-*/transcriptions/
   ```

## 🔧 Troubleshooting

### Common Issues

#### Transcription Failures

**Problem**: Transcription jobs fail with "File not found" error

**Solution**:
1. Check file path and permissions
2. Verify flex server mount status
3. Ensure file format compatibility

```bash
# Check file permissions
ls -la /mnt/flex-1/video.mp4

# Verify mount points
mount | grep flex

# Test file accessibility
python -c "import os; print(os.path.exists('/mnt/flex-1/video.mp4'))"
```

**Problem**: Transcription runs but produces no output

**Solution**:
1. Check audio track availability
2. Verify language settings
3. Review processing logs

```bash
# Check audio streams
ffprobe -v error -select_streams a -show_entries stream=index,codec_name /mnt/flex-1/video.mp4

# Review logs
tail -f /opt/Archivist/logs/transcription.log
```

#### VOD Publishing Issues

**Problem**: VOD publishing fails with authentication errors

**Solution**:
1. Verify Cablecast credentials
2. Check API endpoint URLs
3. Test connection manually

```bash
# Test Cablecast connection
curl -X GET "http://localhost:8000/api/cablecast/health"

# Check API credentials
python -c "from core.cablecast_client import CablecastAPIClient; print(CablecastAPIClient().test_connection())"
```

**Problem**: VOD content doesn't appear in Cablecast

**Solution**:
1. Check VOD processing status
2. Verify content metadata
3. Review publishing logs

```bash
# Check VOD status
curl -X GET "http://localhost:8000/api/vod/sync-status"

# Review publishing logs
tail -f /opt/Archivist/logs/vod.log
```

#### Performance Issues

**Problem**: System running slowly or unresponsive

**Solution**:
1. Check system resources
2. Review active jobs
3. Optimize queue settings

```bash
# Check system resources
htop
free -h
df -h

# Review queue status
curl -X GET "http://localhost:8000/api/queue/status"

# Adjust worker settings
export NUM_WORKERS=2  # Reduce for lower resource usage
```

**Problem**: High memory usage

**Solution**:
1. Adjust batch sizes
2. Review model settings
3. Restart services if needed

```bash
# Reduce batch size
export BATCH_SIZE=8

# Check memory usage by process
ps aux --sort=-%mem | head -10

# Restart service
sudo systemctl restart archivist
```

### Log Analysis

#### Log Locations

```
/opt/Archivist/logs/
├── archivist.log           # Main application log
├── transcription.log       # Transcription processing
├── vod.log                # VOD integration
├── api.log                # API requests
└── error.log              # Error messages
```

#### Log Commands

```bash
# View recent logs
tail -f /opt/Archivist/logs/archivist.log

# Search for errors
grep -i error /opt/Archivist/logs/*.log

# Filter by date
grep "2024-01-15" /opt/Archivist/logs/archivist.log

# View specific job logs
grep "JOB_ID" /opt/Archivist/logs/transcription.log
```

### Getting Help

#### Built-in Help

1. **Web Interface Help**
   - Click "Help" in navigation menu
   - Context-sensitive help buttons
   - Integrated documentation

2. **API Documentation**
   - Swagger UI: `http://localhost:8000/api/docs`
   - ReDoc: `http://localhost:8000/api/redoc`

#### External Resources

1. **Documentation**
   - User manual (this document)
   - API reference
   - Configuration guide
   - Troubleshooting guide

2. **Support Channels**
   - System administrator
   - Technical support team
   - Community forums
   - GitHub issues

## 📋 Command Reference

### File Management Commands

```bash
# Browse files
curl -X GET "http://localhost:8000/api/browse?path=/mnt/flex-1"

# Get file details
curl -X GET "http://localhost:8000/api/file-details?path=/mnt/flex-1/video.mp4"

# Check mount points
curl -X GET "http://localhost:8000/api/mount-points"

# Storage information
curl -X GET "http://localhost:8000/api/storage/info"
```

### Transcription Commands

```bash
# Start transcription
curl -X POST "http://localhost:8000/api/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"path": "/mnt/flex-1/video.mp4", "language": "en"}'

# Check status
curl -X GET "http://localhost:8000/api/status/JOB_ID"

# Get results
curl -X GET "http://localhost:8000/api/results/JOB_ID"

# List transcriptions
curl -X GET "http://localhost:8000/api/transcriptions"
```

### Queue Management Commands

```bash
# Get queue status
curl -X GET "http://localhost:8000/api/queue/status"

# Pause job
curl -X POST "http://localhost:8000/api/queue/pause/JOB_ID"

# Resume job
curl -X POST "http://localhost:8000/api/queue/resume/JOB_ID"

# Cancel job
curl -X DELETE "http://localhost:8000/api/queue/cancel/JOB_ID"

# Clear completed
curl -X DELETE "http://localhost:8000/api/queue/clear-completed"
```

### VOD Management Commands

```bash
# Publish to VOD
curl -X POST "http://localhost:8000/api/vod/publish/TRANSCRIPTION_ID"

# Batch publish
curl -X POST "http://localhost:8000/api/vod/batch-publish" \
  -H "Content-Type: application/json" \
  -d '{"transcription_ids": ["id1", "id2"]}'

# Sync status
curl -X GET "http://localhost:8000/api/vod/sync-status"

# List shows
curl -X GET "http://localhost:8000/api/cablecast/shows"
```

### System Administration Commands

```bash
# System health
curl -X GET "http://localhost:8000/health"

# Generate API key
curl -X POST "http://localhost:8000/api/auth/apikey" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}'

# View metrics
curl -X GET "http://localhost:8000/metrics"

# Check logs
tail -f /opt/Archivist/logs/archivist.log
```

---

**This user manual provides comprehensive guidance for operating the Archivist system. For technical support, consult your system administrator or refer to the technical documentation.** 