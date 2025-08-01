# Import Standardization Plan

## Overview
This document outlines the plan to standardize import patterns across the Archivist codebase for better consistency, maintainability, and to reduce circular import risks.

## 🎯 Goals

1. **Consistent Import Ordering** - Standardize the order of imports
2. **Eliminate Unused Imports** - Remove imports that are not used
3. **Reduce Circular Dependencies** - Organize imports to prevent circular imports
4. **Improve Readability** - Make imports easier to read and understand
5. **Follow PEP 8 Standards** - Adhere to Python style guidelines

## 📋 Standard Import Pattern

### Import Order (PEP 8 Compliant)
```python
# 1. Standard library imports (alphabetical)
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 2. Third-party imports (alphabetical)
from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource
from loguru import logger

# 3. Local application imports (alphabetical)
from core.config import MOUNT_POINTS, NAS_PATH
from core.exceptions import (
    CablecastError,
    ValidationError,
    create_error_response
)
from core.models import TranscriptionResultORM
from core.services import VODService
```

### Import Rules

1. **Group imports by type** (standard library, third-party, local)
2. **Alphabetical order within each group**
3. **Use absolute imports** for local modules (prefer `from core.config import X` over `from .config import X`)
4. **Group related imports** on multiple lines for readability
5. **Use parentheses** for multi-line imports
6. **One import per line** for clarity
7. **Remove unused imports**

## 🔍 Current Issues Identified

### 1. Mixed Import Styles
```python
# Inconsistent - mixing single and grouped imports
import os, sys, time  # ❌ Multiple imports on one line
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, OUTPUT_DIR, COMPUTE_TYPE, BATCH_SIZE  # ❌ Very long line
```

### 2. Inconsistent Ordering
```python
# Mixed order - standard library, third-party, and local imports mixed
from loguru import logger
import os
from core.config import WHISPER_MODEL
import time
from typing import Dict, Optional, List
```

### 3. Unused Imports
```python
# Some imports may not be used in the file
import json  # ❌ May not be used
import subprocess  # ❌ May not be used
```

### 4. Circular Import Risks
```python
# Potential circular imports between modules
from core.services import TranscriptionService  # In core/transcription.py
from core.transcription import run_whisper_transcription  # In core/services/transcription.py
```

## 📁 Files to Update

### High Priority (Core Application)
1. `core/services/transcription.py` - Main transcription service
2. `web/api/cablecast.py` - Main API endpoints
3. `core/config.py` - Configuration module
4. `core/file_manager.py` - File management
5. `core/services/queue_analytics.py` - Queue analytics
6. `core/exceptions.py` - Exception definitions

### Medium Priority (Services and Models)
1. `core/models/__init__.py` - Model definitions
2. `core/services/__init__.py` - Service definitions
3. `core/cablecast_client.py` - Cablecast client
4. `core/vod_automation.py` - VOD automation
5. `core/transcription.py` - Legacy transcription module

### Low Priority (Scripts and Tests)
1. `scripts/development/vod_cli.py` - CLI tools
2. `scripts/monitoring/system_status.py` - Monitoring scripts
3. `test_*.py` - Test files
4. `verify_*.py` - Verification scripts

## 🛠️ Implementation Strategy

### Phase 1: Core Application Files
1. **Analyze current imports** in each file
2. **Identify unused imports** and remove them
3. **Reorder imports** according to standard pattern
4. **Test functionality** to ensure no breaking changes

### Phase 2: Service Layer
1. **Standardize service imports**
2. **Resolve circular dependencies**
3. **Update import statements**

### Phase 3: Scripts and Tests
1. **Update script imports**
2. **Standardize test imports**
3. **Verify all functionality**

## 📊 Success Metrics

### Before Standardization
- ❌ Inconsistent import ordering
- ❌ Mixed import styles
- ❌ Potential unused imports
- ❌ Circular import risks
- ❌ Non-PEP 8 compliant

### After Standardization
- ✅ Consistent import ordering across all files
- ✅ Standardized import styles
- ✅ No unused imports
- ✅ No circular dependencies
- ✅ PEP 8 compliant imports

## 🔧 Tools and Validation

### Automated Tools
- **isort** - For automatic import sorting
- **flake8** - For import style checking
- **pylint** - For unused import detection

### Manual Validation
- **Import dependency analysis** - Check for circular imports
- **Functionality testing** - Ensure no breaking changes
- **Code review** - Manual verification of import patterns

## 📝 Example Transformations

### Before (Inconsistent)
```python
import os, sys
from loguru import logger
from core.config import WHISPER_MODEL, USE_GPU, LANGUAGE, OUTPUT_DIR, COMPUTE_TYPE, BATCH_SIZE
import time
from typing import Dict, Optional, List
from core.exceptions import TranscriptionError, handle_transcription_error
from core.scc_summarizer import summarize_scc
```

### After (Standardized)
```python
import os
import sys
import time
from typing import Dict, List, Optional

from loguru import logger

from core.config import (
    BATCH_SIZE,
    COMPUTE_TYPE,
    LANGUAGE,
    OUTPUT_DIR,
    USE_GPU,
    WHISPER_MODEL
)
from core.exceptions import TranscriptionError, handle_transcription_error
from core.scc_summarizer import summarize_scc
```

## 🚀 Benefits

### Immediate Benefits
- **Better Readability** - Consistent import patterns
- **Easier Maintenance** - Standardized structure
- **Reduced Errors** - No unused imports or circular dependencies

### Long-term Benefits
- **Improved Performance** - No unused imports loaded
- **Better Debugging** - Clear import dependencies
- **Easier Onboarding** - New developers understand patterns
- **PEP 8 Compliance** - Follows Python standards

## 📋 Implementation Checklist

- [ ] Create import standardization plan
- [ ] Analyze current import patterns
- [ ] Identify files to update
- [ ] Update core application files
- [ ] Update service layer files
- [ ] Update scripts and tests
- [ ] Test all functionality
- [ ] Document new import patterns
- [ ] Create import style guide
- [ ] Set up automated tools for future compliance 