# Immediate Code Organization Improvements

## Quick Wins (Can be done immediately)

### 1. **Clean Root Directory**
```bash
# Move test files to tests/
mv test_*.py tests/integration/
mv test_cablecast_api_connection.py tests/integration/

# Move CLI tools to scripts/
mv vod_cli.py scripts/development/
mv create_cablecast_tables.py scripts/development/

# Move configuration files to config/
mv nginx/ config/
mv grafana/ config/
mv prometheus/ config/
mv certbot/ config/

# Move data directories
mv uploads/ data/
mv outputs/ data/
mv logs/ data/
```

### 2. **Split Large Files in Core**

#### `core/web_app.py` (642 lines) - Split into:
- `core/api/routes/browse.py` - Browse endpoints
- `core/api/routes/transcribe.py` - Transcription endpoints  
- `core/api/routes/queue.py` - Queue management endpoints
- `core/api/routes/vod.py` - VOD endpoints

#### `core/security.py` (469 lines) - Split into:
- `core/security/manager.py` - Security manager class
- `core/security/validation.py` - Input validation
- `core/security/headers.py` - Security headers
- `core/security/csrf.py` - CSRF protection

#### `core/transcription.py` (488 lines) - Split into:
- `core/transcription/whisper.py` - WhisperX integration
- `core/transcription/processor.py` - Processing logic
- `core/transcription/validator.py` - Validation logic

### 3. **Consolidate Similar Functionality**

#### Group Cablecast-related files:
```
core/cablecast/
├── __init__.py
├── client.py
├── integration.py
├── show_mapper.py
├── transcription_linker.py
├── vod_manager.py
└── automation.py
```

#### Group VOD-related files:
```
core/vod/
├── __init__.py
├── content_manager.py
├── automation.py
└── integration.py
```

### 4. **Improve Import Organization**

#### Create service layer abstractions:
```python
# core/services/__init__.py
from .transcription import TranscriptionService
from .vod import VODService
from .file import FileService
from .queue import QueueService

__all__ = ['TranscriptionService', 'VODService', 'FileService', 'QueueService']
```

#### Update imports to use service layer:
```python
# Instead of:
from core.transcription import run_whisper_transcription
from core.vod_content_manager import VODContentManager

# Use:
from core.services import TranscriptionService, VODService
```

### 5. **Standardize Error Handling**

#### Create centralized error handling:
```python
# core/exceptions.py
class ArchivistException(Exception):
    """Base exception for Archivist application"""
    pass

class TranscriptionError(ArchivistException):
    """Transcription-related errors"""
    pass

class VODError(ArchivistException):
    """VOD integration errors"""
    pass

class FileError(ArchivistException):
    """File operation errors"""
    pass
```

### 6. **Improve Configuration Management**

#### Split configuration by domain:
```python
# core/config/
├── __init__.py
├── base.py          # Base configuration
├── database.py      # Database settings
├── security.py      # Security settings
├── vod.py          # VOD settings
├── transcription.py # Transcription settings
└── monitoring.py    # Monitoring settings
```

### 7. **Better Test Organization**

#### Organize tests by functionality:
```
tests/
├── unit/
│   ├── test_services/
│   │   ├── test_transcription.py
│   │   ├── test_vod.py
│   │   └── test_file.py
│   ├── test_models/
│   └── test_utils/
├── integration/
│   ├── test_api/
│   ├── test_database/
│   └── test_cablecast/
└── fixtures/
```

## Implementation Steps

### Step 1: Quick Cleanup (30 minutes)
```bash
# Create new directories
mkdir -p tests/integration tests/unit scripts/development config data

# Move files
mv test_*.py tests/integration/
mv vod_cli.py scripts/development/
mv create_cablecast_tables.py scripts/development/
mv nginx/ config/
mv grafana/ config/
mv prometheus/ config/
mv certbot/ config/
mv uploads/ data/
mv outputs/ data/
mv logs/ data/
```

### Step 2: Split Large Files (2-3 hours)
1. Split `core/web_app.py` into route modules
2. Split `core/security.py` into focused modules
3. Split `core/transcription.py` into service modules

### Step 3: Create Service Layer (1-2 hours)
1. Create service abstractions
2. Update imports to use services
3. Add proper error handling

### Step 4: Improve Configuration (30 minutes)
1. Split configuration by domain
2. Create configuration validation
3. Add environment-specific configs

### Step 5: Update Tests (1 hour)
1. Reorganize test structure
2. Update test imports
3. Add missing test coverage

## Benefits of These Changes

### Immediate Benefits:
- **Cleaner root directory** - Easier to navigate
- **Smaller, focused files** - Better maintainability
- **Clear service boundaries** - Easier to understand
- **Better error handling** - More robust application
- **Organized tests** - Easier to find and run tests

### Long-term Benefits:
- **Easier onboarding** - New developers can find things quickly
- **Better scalability** - Clear patterns for adding features
- **Reduced technical debt** - Cleaner codebase
- **Improved testing** - Better test organization and coverage

## Files That Need Immediate Attention

### High Priority:
1. `core/web_app.py` (642 lines) - Too large, mixed concerns
2. `core/security.py` (469 lines) - Security logic mixed together
3. `core/transcription.py` (488 lines) - Business logic needs separation
4. Root directory clutter - Test files and configs scattered

### Medium Priority:
1. `core/task_queue.py` (380 lines) - Could be split into smaller modules
2. `core/vod_content_manager.py` (367 lines) - VOD logic needs organization
3. Import organization - Too many direct imports from core modules

### Low Priority:
1. Documentation organization
2. Script organization
3. Configuration file organization

## Quick Commands to Start

```bash
# 1. Create new directory structure
mkdir -p tests/{unit,integration} scripts/{development,deployment,monitoring} config data

# 2. Move files
mv test_*.py tests/integration/
mv vod_cli.py scripts/development/
mv nginx/ config/
mv grafana/ config/
mv prometheus/ config/
mv certbot/ config/
mv uploads/ data/
mv outputs/ data/
mv logs/ data/

# 3. Create service directories
mkdir -p core/{services,api,exceptions}

# 4. Start splitting large files
# (Manual process - create new files and move code)
```

This approach allows you to improve the codebase organization incrementally without a complete rewrite, while setting up the foundation for the larger reorganization later. 