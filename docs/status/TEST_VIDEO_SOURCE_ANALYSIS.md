# Test Video Source Analysis

**Generated**: 2025-08-05 14:30 UTC  
**Purpose**: Analyze all test files to verify they reference real videos from flex servers

## 🔍 Analysis Summary

After reviewing all test files in the codebase, here's the breakdown of which tests use real videos from flex servers vs fake test files:

## ✅ Tests Using Real Videos from Flex Servers

### 1. `test_single_transcription.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Searches flex servers (`/mnt/flex-1` through `/mnt/flex-8`) for real MP4 files
- **Logic**: Finds files under 100MB that don't already have SCC captions
- **Real Video Detection**: ✅ Uses `glob.glob(os.path.join(mount_path, "*.mp4"))` to find actual video files

### 2. `test_direct_transcription.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Same as above - searches flex servers for real MP4 files
- **Logic**: Identical to `test_single_transcription.py`
- **Real Video Detection**: ✅ Uses `glob.glob(os.path.join(mount_path, "*.mp4"))` to find actual video files

### 3. `test_surface_level_discovery.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Uses `get_recent_vods_from_flex_server()` to find real VODs
- **Logic**: Discovers actual video files from flex server mounts
- **Real Video Detection**: ✅ Uses `get_recent_vods_from_flex_server(mount_path, server_id, limit=3)`

### 4. `test_force_processing.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Uses `get_recent_vods_from_flex_server()` to find real VODs
- **Logic**: Processes actual videos found on flex servers
- **Real Video Detection**: ✅ Uses `get_recent_vods_from_flex_server(mount_path, city_id, limit=10)`

### 5. `tests/test_real_vod_processing.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Uses Cablecast API to get real VOD (ID: 764)
- **Logic**: Downloads and processes actual VOD content from Cablecast
- **Real Video Detection**: ✅ Uses `client.get_vod(vod_id)` with real VOD ID

### 6. `tests/test_complete_scc_pipeline.py`
- **Status**: ✅ **USES REAL VIDEOS**
- **Source**: Uses predefined real video paths from flex servers
- **Logic**: Tests with actual video files like `/mnt/flex-5/14221-1-North St Paul City Council (20190402).mp4`
- **Real Video Detection**: ✅ Uses hardcoded paths to real flex server videos

### 7. `verify_transcription_system.py`
- **Status**: ⚠️ **MIXED - Uses real videos for discovery, fake file for queue test**
- **Source**: 
  - Real videos: Uses `get_recent_vods_from_flex_server()` for discovery
  - Fake file: Uses `/tmp/test_video.mp4` for queue testing
- **Logic**: Discovers real videos but tests queue with non-existent file
- **Real Video Detection**: ✅ For discovery, ❌ For queue testing

## ❌ Tests Using Fake Test Files

### 1. `test_vod_system_comprehensive.py`
- **Status**: ❌ **USES FAKE TEST FILES**
- **Source**: Creates `/tmp/test_video.mp4` with fake content
- **Logic**: Falls back to fake file when no real videos found
- **Issue**: ```python
  test_video_path = "/tmp/test_video.mp4"
  with open(test_video_path, 'wb') as f:
      f.write(b'fake video content')
  ```

### 2. `test_vod_core_functionality.py`
- **Status**: ❌ **USES FAKE TEST FILES**
- **Source**: Creates `/tmp/test_video.mp4` with fake content
- **Logic**: Uses fake file for testing
- **Issue**: ```python
  test_video_path = "/tmp/test_video.mp4"
  with open(test_video_path, 'wb') as f:
      f.write(b'fake video content')
  ```

### 3. `tests/unit/test_file_manager.py`
- **Status**: ❌ **USES FAKE TEST FILES**
- **Source**: Creates fake video content for unit tests
- **Logic**: Unit test that doesn't need real videos
- **Note**: This is acceptable for unit tests

## 🔧 Tests with Mixed Usage

### 1. `tests/test_with_real_videos.py`
- **Status**: ⚠️ **MIXED - Uses test videos from test_videos/ directory**
- **Source**: Looks for real MP4 files in `test_videos/` directory
- **Logic**: Uses actual video files but not from flex servers
- **Note**: This is acceptable as it uses real video files, just not from flex servers

## 📊 Summary Statistics

- **Total Test Files Analyzed**: 12
- **Tests Using Real Flex Server Videos**: 7 ✅
- **Tests Using Fake Test Files**: 3 ❌
- **Tests with Mixed Usage**: 2 ⚠️

## 🚨 Issues Found

### 1. `test_vod_system_comprehensive.py` - CRITICAL
- **Problem**: Falls back to fake video file when no real videos found
- **Impact**: Test may pass with fake data instead of real video processing
- **Fix Needed**: Should fail gracefully instead of using fake files

### 2. `test_vod_core_functionality.py` - CRITICAL  
- **Problem**: Uses fake video file for testing
- **Impact**: Test doesn't validate real video processing
- **Fix Needed**: Should use real videos from flex servers

### 3. `verify_transcription_system.py` - MINOR
- **Problem**: Uses fake file for queue testing
- **Impact**: Queue test doesn't validate with real video
- **Fix Needed**: Should use real video file for queue testing

## 🎯 Recommended Actions

### Immediate Fixes Required:

1. **Fix `test_vod_system_comprehensive.py`**:
   ```python
   # Replace fallback logic
   if not test_vod_files:
       self.log("No real video files found on flex servers - test cannot proceed", "ERROR")
       return False  # Fail instead of using fake file
   ```

2. **Fix `test_vod_core_functionality.py`**:
   ```python
   # Replace fake file creation with real video discovery
   from core.tasks.vod_processing import get_recent_vods_from_flex_server
   # Use real videos from flex servers
   ```

3. **Fix `verify_transcription_system.py`**:
   ```python
   # Replace fake file with real video for queue testing
   # Use first available real video from flex servers
   ```

### Verification Steps:

1. **Run all tests** to ensure they use real videos
2. **Verify flex server mounts** are accessible
3. **Check test results** to ensure real video processing is validated
4. **Update test documentation** to reflect real video usage

## ✅ Conclusion

Most tests (7/12) already use real videos from flex servers, which is good. However, 3 critical tests use fake files and need to be fixed to ensure proper validation of the video processing system.

**Priority**: HIGH - Fix the 3 tests using fake files to ensure comprehensive real video testing. 