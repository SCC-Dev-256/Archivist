# Exception Handling Guide - Archivist Application

**Date:** 2025-07-18  
**Status:** ✅ **COMPREHENSIVE EXCEPTION SYSTEM IMPLEMENTED**

## 🎯 **Overview**

This guide explains how to use the new specific exception types to improve error handling, debugging, and user experience throughout the Archivist application.

## 🏗️ **Exception Hierarchy**

```
ArchivistException (Base)
├── TranscriptionError
│   ├── WhisperModelError
│   ├── AudioProcessingError
│   └── SCCGenerationError
├── FileError
│   ├── FileNotFoundError
│   ├── FilePermissionError
│   ├── FileSizeError
│   └── FileFormatError
├── NetworkError
│   ├── ConnectionError
│   └── TimeoutError
├── DatabaseError
│   ├── DatabaseConnectionError
│   └── DatabaseQueryError
├── QueueError
│   ├── TaskNotFoundError
│   ├── TaskTimeoutError
│   └── TaskExecutionError
├── VODError
├── CablecastError
│   ├── CablecastAuthenticationError
│   └── CablecastShowNotFoundError
├── SecurityError
│   ├── AuthenticationError
│   └── AuthorizationError
├── ValidationError
│   ├── RequiredFieldError
│   └── InvalidFormatError
├── ConfigurationError
└── APIError
```

## 📋 **Exception Categories**

### **1. Transcription Exceptions**

**Use for:** All transcription-related errors

```python
from core.exceptions import (
    TranscriptionError, WhisperModelError, 
    AudioProcessingError, SCCGenerationError
)

# Model loading errors
raise WhisperModelError("Failed to load model", model_name="large-v2")

# Audio processing errors
raise AudioProcessingError("Invalid audio format", audio_file="video.mp4")

# SCC generation errors
raise SCCGenerationError("Failed to write SCC file", scc_file="output.scc")
```

### **2. File System Exceptions**

**Use for:** File operations, permissions, formats

```python
from core.exceptions import (
    FileError, FileNotFoundError, FilePermissionError,
    FileSizeError, FileFormatError
)

# File not found
raise FileNotFoundError("/path/to/missing/file.mp4")

# Permission denied
raise FilePermissionError("/path/to/file.mp4", operation="write")

# File too large
raise FileSizeError("/path/to/file.mp4", file_size=1024*1024*1024, max_size=100*1024*1024)

# Unsupported format
raise FileFormatError("/path/to/file.xyz", file_format="xyz", supported_formats=["mp4", "avi"])
```

### **3. Network Exceptions**

**Use for:** API calls, external service communication

```python
from core.exceptions import NetworkError, ConnectionError, TimeoutError, APIError

# Connection failed
raise ConnectionError("https://api.cablecast.com/shows")

# Request timeout
raise TimeoutError("https://api.cablecast.com/shows", timeout=30)

# API error
raise APIError("Service unavailable", status_code=503, endpoint="/api/shows")
```

### **4. Database Exceptions**

**Use for:** Database operations, queries, connections

```python
from core.exceptions import DatabaseError, DatabaseConnectionError, DatabaseQueryError

# Connection failed
raise DatabaseConnectionError("postgresql://localhost/archivist")

# Query error
raise DatabaseQueryError("SELECT * FROM transcriptions WHERE id = ?", query="SELECT * FROM transcriptions")
```

### **5. Queue Exceptions**

**Use for:** Task queue operations, Celery tasks

```python
from core.exceptions import QueueError, TaskNotFoundError, TaskTimeoutError, TaskExecutionError

# Task not found
raise TaskNotFoundError("task-123")

# Task timeout
raise TaskTimeoutError("task-123", timeout=3600)

# Task execution failed
raise TaskExecutionError("task-123", task_name="transcription.run_whisper")
```

### **6. VOD and Cablecast Exceptions**

**Use for:** VOD integration, Cablecast API

```python
from core.exceptions import (
    VODError, CablecastError, CablecastAuthenticationError, 
    CablecastShowNotFoundError
)

# VOD error
raise VODError("Failed to upload VOD", vod_id="vod-123", vod_url="https://example.com/vod.mp4")

# Cablecast authentication
raise CablecastAuthenticationError(endpoint="/api/shows")

# Show not found
raise CablecastShowNotFoundError("show-456")
```

### **7. Security Exceptions**

**Use for:** Authentication, authorization, security issues

```python
from core.exceptions import SecurityError, AuthenticationError, AuthorizationError

# Authentication failed
raise AuthenticationError("Invalid credentials", user="admin")

# Authorization failed
raise AuthorizationError("Access denied", resource="/api/admin", action="delete")
```

### **8. Validation Exceptions**

**Use for:** Input validation, data validation

```python
from core.exceptions import ValidationError, RequiredFieldError, InvalidFormatError

# Missing required field
raise RequiredFieldError("email")

# Invalid format
raise InvalidFormatError("email", "invalid-email", expected_format="user@domain.com")
```

## 🔧 **Using Exception Decorators**

### **Automatic Exception Handling**

```python
from core.exceptions import (
    handle_transcription_error, handle_file_error, 
    handle_network_error, handle_database_error
)

@handle_transcription_error
def transcribe_video(video_path: str):
    """This function will automatically wrap exceptions in TranscriptionError"""
    # Your transcription logic here
    pass

@handle_file_error
def process_file(file_path: str):
    """This function will automatically wrap exceptions in FileError"""
    # Your file processing logic here
    pass

@handle_network_error
def call_external_api(url: str):
    """This function will automatically wrap exceptions in NetworkError"""
    # Your API call logic here
    pass
```

## 🎯 **Best Practices**

### **1. Replace Bare Exception Catches**

**❌ Before:**
```python
try:
    result = some_operation()
except Exception as e:
    logger.error(f"Error: {e}")
    return jsonify({'error': str(e)}), 500
```

**✅ After:**
```python
try:
    result = some_operation()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    error_response = create_error_response(e)
    return jsonify(error_response), 404
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    error_response = create_error_response(e)
    return jsonify(error_response), 503
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return jsonify({
        'success': False,
        'error': {
            'code': 'UNKNOWN_ERROR',
            'message': 'An unexpected error occurred',
            'details': {'original_error': str(e)}
        }
    }), 500
```

### **2. Use Specific Exceptions**

**❌ Generic:**
```python
raise Exception("Something went wrong")
```

**✅ Specific:**
```python
raise FileNotFoundError("/path/to/file.mp4")
raise CablecastAuthenticationError("/api/shows")
raise ValidationError("Invalid email format", field="email", value="invalid-email")
```

### **3. Include Context Information**

```python
# Good - includes context
raise FileError(
    "Failed to process video file", 
    file_path="/path/to/video.mp4",
    details={'operation': 'transcription', 'file_size': 1024*1024}
)

# Better - includes original exception
try:
    process_video("/path/to/video.mp4")
except OSError as e:
    raise FileError(
        "Failed to process video file", 
        file_path="/path/to/video.mp4",
        original_exception=e
    )
```

### **4. Use Error Response Utilities**

```python
from core.exceptions import create_error_response, map_exception_to_http_status

try:
    result = some_operation()
except ArchivistException as e:
    # Automatically create standardized error response
    error_response = create_error_response(e)
    status_code = map_exception_to_http_status(e)
    return jsonify(error_response), status_code
```

## 📊 **HTTP Status Code Mapping**

The system automatically maps exceptions to appropriate HTTP status codes:

- **404**: `FileNotFoundError`, `TaskNotFoundError`, `CablecastShowNotFoundError`
- **403**: `FilePermissionError`, `AuthenticationError`, `AuthorizationError`
- **400**: `ValidationError`, `RequiredFieldError`, `InvalidFormatError`
- **408**: `TimeoutError`, `TaskTimeoutError`
- **503**: `ConnectionError`, `DatabaseConnectionError`
- **500**: `ConfigurationError`, `SecurityError`, other application errors

## 🔍 **Debugging with Exceptions**

### **Rich Error Information**

```python
try:
    result = transcribe_video("video.mp4")
except TranscriptionError as e:
    print(f"Error Code: {e.error_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.details}")
    print(f"Original Exception: {e.original_exception}")
    print(f"Traceback: {e.traceback}")
```

### **Exception to Dictionary**

```python
try:
    result = some_operation()
except ArchivistException as e:
    error_dict = e.to_dict()
    # Returns: {
    #     'error_code': 'FILE_ERROR',
    #     'message': 'File not found: /path/to/file.mp4',
    #     'details': {'file_path': '/path/to/file.mp4'},
    #     'traceback': '...'
    # }
```

## 🚀 **Migration Strategy**

### **Phase 1: Update New Code**
- Use specific exceptions in all new code
- Use exception decorators for automatic handling
- Use error response utilities

### **Phase 2: Update Existing Code**
- Replace bare `except Exception:` with specific handlers
- Add context information to exceptions
- Use standardized error responses

### **Phase 3: Monitor and Improve**
- Monitor error logs for patterns
- Add new exception types as needed
- Improve error messages and context

## 📝 **Example: Complete API Endpoint**

```python
from flask import jsonify
from core.exceptions import (
    FileNotFoundError, ValidationError, TranscriptionError,
    create_error_response, map_exception_to_http_status
)

@app.route('/api/transcribe', methods=['POST'])
def transcribe_video():
    try:
        data = request.get_json()
        
        # Validation
        if not data or 'file_path' not in data:
            raise ValidationError("Missing file_path", field="file_path")
        
        file_path = data['file_path']
        
        # File existence check
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)
        
        # Transcription
        result = transcribe_service.transcribe_file(file_path)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        error_response = create_error_response(e)
        return jsonify(error_response), 400
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        error_response = create_error_response(e)
        return jsonify(error_response), 404
        
    except TranscriptionError as e:
        logger.error(f"Transcription error: {e}")
        error_response = create_error_response(e)
        return jsonify(error_response), 500
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNKNOWN_ERROR',
                'message': 'An unexpected error occurred',
                'details': {'original_error': str(e)}
            }
        }), 500
```

## 🎉 **Benefits**

### **1. Better Error Identification**
- Specific exception types make it easy to identify error categories
- Rich context information helps with debugging
- Original exceptions preserved for detailed analysis

### **2. Improved User Experience**
- Appropriate HTTP status codes
- Consistent error response format
- Meaningful error messages

### **3. Easier Debugging**
- Detailed error information in logs
- Stack traces preserved
- Context information included

### **4. Better Monitoring**
- Error categorization for metrics
- Specific error codes for alerting
- Structured error data for analysis

---

**Next Steps:** Start using these specific exceptions in your code to improve error handling and debugging capabilities! 