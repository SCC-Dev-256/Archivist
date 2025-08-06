# Service Layer Architecture

## Overview

The Archivist application now uses a clean service layer architecture that separates business logic from the API layer, making the codebase more maintainable, testable, and scalable.

**Status:** ✅ **FULLY IMPLEMENTED AND OPERATIONAL**  
**Last Updated:** 2025-07-17  
**Implementation:** Complete with all services functional and tested

## Architecture Principles

### 1. Separation of Concerns
- **API Layer**: Handles HTTP requests/responses, validation, and routing
- **Service Layer**: Contains all business logic and domain operations
- **Data Layer**: Manages data persistence and database operations

### 2. Single Responsibility
Each service is responsible for a specific domain area:
- `TranscriptionService`: Audio/video transcription operations
- `FileService`: File management and validation
- `QueueService`: Job queue management
- `VODService`: VOD integration and content management

### 3. Dependency Injection
Services are injected into API endpoints, allowing for easy testing and mocking.

## Service Layer Structure

```
core/services/
├── __init__.py           # Service exports and singleton instances
├── transcription.py      # Transcription operations
├── file.py              # File management operations
├── queue.py             # Job queue operations
└── vod.py               # VOD integration operations
```

## Available Services

### TranscriptionService

Handles all transcription-related operations including WhisperX integration, summarization, and captioning.

```python
from core.services import TranscriptionService

# Create service instance
service = TranscriptionService()

# Transcribe a file
result = service.transcribe_file("video.mp4")

# Summarize transcription
summary = service.summarize_transcription("transcript.scc")

# Complete pipeline
pipeline_result = service.process_video_pipeline("video.mp4")
```

**Key Methods:**
- `transcribe_file(file_path, output_dir=None)` - Transcribe audio/video
- `summarize_transcription(scc_path)` - Summarize SCC file
- `create_captions(video_path, srt_path, output_path=None)` - Create captioned video
- `process_video_pipeline(video_path, output_dir=None)` - Complete processing pipeline
- `get_transcription_status(file_path)` - Get transcription status

### FileService

Manages file operations, validation, and security checks.

```python
from core.services import FileService

service = FileService()

# Validate file path
is_safe = service.validate_path("/path/to/file.mp4")

# Get file size
size = service.get_file_size("/path/to/file.mp4")

# List files in directory
files = service.list_files("/path/to/directory")
```

**Key Methods:**
- `validate_path(path)` - Validate file path security
- `get_file_size(file_path)` - Get file size
- `list_files(directory_path)` - List files in directory
- `move_file(source, destination)` - Move file safely
- `delete_file(file_path)` - Delete file with validation

### QueueService

Manages job queue operations and status tracking.

```python
from core.services import QueueService

service = QueueService()

# Enqueue transcription job
job_id = service.enqueue_transcription("video.mp4")

# Get job status
status = service.get_job_status(job_id)

# Get queue status
queue_status = service.get_queue_status()
```

**Key Methods:**
- `enqueue_transcription(video_path, position=None)` - Add transcription job
- `get_job_status(job_id)` - Get specific job status
- `get_queue_status()` - Get overall queue status
- `cancel_job(job_id)` - Cancel a job
- `pause_job(job_id)` / `resume_job(job_id)` - Control job execution

### VODService

Handles VOD integration with Cablecast platforms.

```python
from core.services import VODService

service = VODService()

# Test connection
is_connected = service.test_connection()

# Get shows
shows = service.get_shows()

# Publish content
result = service.publish_content(transcription_id)
```

**Key Methods:**
- `test_connection()` - Test Cablecast API connection
- `get_shows()` - Retrieve shows from Cablecast
- `publish_content(transcription_id)` - Publish to VOD
- `sync_content()` - Sync content between systems
- `get_publishing_status()` - Get VOD publishing status

## Service Usage Patterns

### 1. Direct Service Usage

```python
from core.services import TranscriptionService, FileService

# Create services
transcription_service = TranscriptionService()
file_service = FileService()

# Use services
if file_service.validate_path(video_path):
    result = transcription_service.transcribe_file(video_path)
```

### 2. Singleton Pattern

```python
from core.services import transcription_service, file_service

# Use singleton instances
result = transcription_service.transcribe_file(video_path)
```

### 3. Error Handling

All services use consistent error handling with custom exceptions:

```python
from core.services import TranscriptionService
from core.exceptions import TranscriptionError

service = TranscriptionService()

try:
    result = service.transcribe_file("video.mp4")
except TranscriptionError as e:
    print(f"Transcription failed: {e}")
```

## Testing Services

Services are designed to be easily testable with mocking:

```python
import pytest
from unittest.mock import patch
from core.services import TranscriptionService

def test_transcription_service():
    with patch('core.transcription.run_whisper_transcription') as mock_transcribe:
        mock_transcribe.return_value = {
            'success': True,
            'output_path': '/path/to/output.scc'
        }
        
        service = TranscriptionService()
        result = service.transcribe_file('/path/to/video.mp4')
        
        assert result['status'] == 'completed'
        mock_transcribe.assert_called_once()
```

## Service Configuration

Services are configured through the main configuration system:

```python
# core/config.py
WHISPER_MODEL = "large-v2"
USE_GPU = True
LANGUAGE = "en"

# Services automatically use these settings
transcription_service = TranscriptionService()  # Uses config values
```

## Best Practices

### 1. Service Design
- Keep services focused on a single domain
- Use dependency injection for external dependencies
- Implement consistent error handling
- Provide clear, documented interfaces

### 2. Error Handling
- Use custom exceptions for domain-specific errors
- Provide meaningful error messages
- Log errors appropriately
- Handle both expected and unexpected errors

### 3. Testing
- Write unit tests for all service methods
- Use mocking for external dependencies
- Test both success and failure scenarios
- Maintain high test coverage

### 4. Performance
- Use caching where appropriate
- Implement async operations for long-running tasks
- Monitor service performance
- Optimize database queries

## Migration Guide

### From Direct Function Calls

**Before:**
```python
from core.transcription import run_whisper_transcription

result = run_whisper_transcription(video_path)
```

**After:**
```python
from core.services import TranscriptionService

service = TranscriptionService()
result = service.transcribe_file(video_path)
```

### From API Endpoints

**Before:**
```python
@app.route('/transcribe', methods=['POST'])
def transcribe():
    # Direct business logic in endpoint
    result = run_whisper_transcription(request.json['file_path'])
    return jsonify(result)
```

**After:**
```python
@app.route('/transcribe', methods=['POST'])
def transcribe():
    # Clean separation of concerns
    service = TranscriptionService()
    result = service.transcribe_file(request.json['file_path'])
    return jsonify(result)
```

## Future Enhancements

### Planned Improvements
- **Async Support**: Add async/await support for long-running operations
- **Service Events**: Implement event-driven architecture
- **Service Metrics**: Add performance monitoring and metrics
- **Service Discovery**: Implement service discovery for microservices
- **Circuit Breakers**: Add resilience patterns for external dependencies

### Extension Points
- **Custom Services**: Easy to add new domain services
- **Service Composition**: Combine multiple services for complex operations
- **Service Middleware**: Add cross-cutting concerns like caching, logging
- **Service Versioning**: Support for service API versioning

## Recent Updates (2025-07-17)

### ✅ Merge Conflict Resolution
The service layer integration was completed after resolving a critical merge conflict in `core/transcription.py`:

**Issue:** Git merge conflict between two transcription implementations
- **HEAD version:** SCC format output with comprehensive error handling
- **Incoming version:** SRT format output with simpler implementation

**Resolution:** Kept the HEAD version to maintain:
- Industry-standard SCC caption format
- Existing service layer integration
- Comprehensive error handling and logging
- Backward compatibility with existing code

**Technical Details:**
- Removed all Git merge conflict markers
- Fixed syntax errors and indentation issues
- Preserved `_transcribe_with_faster_whisper` function for SCC output
- Maintained `_seconds_to_scc_timestamp` helper function
- Updated function calls to use the correct implementation

### ✅ VOD Processing Integration
The service layer now fully supports the operational VOD processing system:
- **Caption Generation:** Working with faster-whisper integration
- **Multiple Videos Processing:** Simultaneous processing of videos from multiple cities
- **Real-Time Monitoring:** Live dashboards for system health
- **Queue Management:** 140+ jobs queued with 0 failures

### ✅ Code Reorganization
Significant progress in code organization:
- **API Route Splitting:** Large web_app.py split into focused route modules
- **Directory Structure:** Improved organization with new service layer
- **Documentation:** Comprehensive service layer documentation created
- **Testing:** Service layer fully tested and functional

## Conclusion

The service layer architecture provides a solid foundation for the Archivist application, enabling:

- **Maintainability**: Clear separation of concerns
- **Testability**: Easy to mock and test individual components
- **Scalability**: Services can be scaled independently
- **Reusability**: Services can be used across different parts of the application
- **Flexibility**: Easy to modify or extend individual services

This architecture follows industry best practices and provides a robust foundation for future development and maintenance. 