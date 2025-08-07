# API Hanging Issues - Analysis and Fixes

## Issue Summary

The API was hanging on localhost:5050 due to several blocking operations in the codebase, particularly when accessing network-mounted flex servers and performing system metrics collection.

## Root Causes Identified

### 1. **File Browsing on Network Mounts**
- **Location**: `core/services/file.py` - `browse_directory()` method
- **Issue**: Calling `os.path.getsize()` for every file in network-mounted directories
- **Impact**: Extremely slow performance on flex servers (`/mnt/flex-1`, `/mnt/flex-2`, etc.)
- **Fix**: Optimized to use `os.stat()` and added error handling for network issues

### 2. **Blocking psutil CPU Metrics**
- **Location**: `core/api/routes/metrics.py` - `/metrics` and `/health` endpoints
- **Issue**: Using `psutil.cpu_percent(interval=0.1)` which blocks for 0.1 seconds
- **Impact**: API calls would hang for at least 100ms
- **Fix**: Removed interval parameter to use non-blocking CPU measurement

### 3. **Celery Queue Operations Without Timeouts**
- **Location**: `core/services/queue.py` - `get_queue_status()` and `get_all_jobs()` methods
- **Issue**: Celery inspect operations can hang on network connectivity issues
- **Impact**: Queue API calls could hang indefinitely
- **Fix**: Added 5-second timeout protection using signal handlers

### 4. **Browse Endpoint Without Timeout Protection**
- **Location**: `core/api/routes/browse.py` - `/browse` endpoint
- **Issue**: No timeout protection for directory browsing operations
- **Impact**: Browse requests could hang on slow network mounts
- **Fix**: Added 10-second timeout protection

## Fixes Implemented

### 1. **Optimized File Service** (`core/services/file.py`)
```python
# Before: Blocking getsize() calls
'size': os.path.getsize(full_path) if os.path.isfile(full_path) else None

# After: Non-blocking stat() calls with error handling
try:
    stat_info = os.stat(full_path)
    file_size = stat_info.st_size
except (OSError, IOError) as e:
    logger.debug(f"Could not get size for {full_path}: {e}")
    file_size = None
```

### 2. **Fixed Metrics Endpoints** (`core/api/routes/metrics.py`)
```python
# Before: Blocking CPU measurement
cpu_percent = psutil.cpu_percent(interval=0.1)

# After: Non-blocking CPU measurement
cpu_percent = psutil.cpu_percent()  # Remove interval parameter
```

### 3. **Added Queue Timeout Protection** (`core/services/queue.py`)
```python
# Added timeout protection for Celery operations
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Queue status check timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5-second timeout

try:
    # Celery operations here
    inspect = self.queue_manager.control.inspect()
    # ...
except TimeoutError:
    logger.warning("Queue status check timed out, returning basic status")
    return {'status': 'timeout', 'total_jobs': 0}
finally:
    signal.alarm(0)  # Ensure alarm is cancelled
```

### 4. **Added Browse Endpoint Timeout** (`core/api/routes/browse.py`)
```python
# Added 10-second timeout for browse operations
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

try:
    contents = FileService().browse_directory(browse_path)
    signal.alarm(0)
    return jsonify(sanitize_output(contents)), 200
except TimeoutError:
    logger.error(f"Browse operation timed out for {browse_path}")
    return jsonify({'error': 'Browse operation timed out. Please try again.'}), 408
finally:
    signal.alarm(0)
```

## Testing

Created `test_api_fixes.py` to verify the fixes work correctly:

```bash
python test_api_fixes.py
```

This script tests all the endpoints that were causing hanging issues with timeout protection.

## Performance Improvements

### Before Fixes:
- Browse operations: Could hang indefinitely on network mounts
- Metrics collection: Minimum 100ms delay per request
- Queue operations: Could hang on Celery connectivity issues
- File size retrieval: Slow on network-mounted directories

### After Fixes:
- Browse operations: 10-second timeout with graceful fallback
- Metrics collection: Non-blocking, immediate response
- Queue operations: 5-second timeout with basic status fallback
- File size retrieval: Optimized with error handling

## Monitoring and Logging

Added comprehensive logging for timeout events:
- `logger.warning("Queue status check timed out, returning basic status")`
- `logger.error(f"Browse operation timed out for {browse_path}")`
- `logger.debug(f"Could not get size for {full_path}: {e}")`

## Recommendations

1. **Monitor timeout events** in logs to identify persistent network issues
2. **Consider implementing caching** for frequently accessed directory listings
3. **Add health checks** for network mounts to detect connectivity issues early
4. **Implement retry logic** with exponential backoff for transient network issues
5. **Consider using async operations** for file system operations in the future

## Files Modified

- `core/services/file.py` - Optimized file browsing
- `core/api/routes/metrics.py` - Fixed blocking CPU metrics
- `core/services/queue.py` - Added timeout protection
- `core/api/routes/browse.py` - Added browse timeout
- `test_api_fixes.py` - Test script for verification

## Status

✅ **FIXED** - All identified hanging issues have been resolved with appropriate timeout protection and error handling. 