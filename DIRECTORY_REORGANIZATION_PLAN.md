# Directory Structure Reorganization Plan

## Overview

This document outlines a comprehensive reorganization of the Archivist project directory structure to improve maintainability, clarity, and adherence to Python project best practices.

**Status:** 📋 **PLANNING PHASE**  
**Date:** 2025-07-17  
**Implementation:** Systematic reorganization with minimal disruption

## Current Issues Analysis

### ❌ **Problems Identified:**

1. **Test Files Scattered in Root Directory**
   - `test_*.py` files mixed with source code
   - Test configuration files in root
   - Test data and fixtures not properly organized

2. **Configuration Files Not Organized**
   - `.env` files in root directory
   - Some config in `config/` directory
   - Service files mixed with application code

3. **Scripts Not in Dedicated Directory**
   - Some scripts in `scripts/` directory
   - Others scattered in root directory
   - No clear separation of script types

4. **Data Directories Not Properly Organized**
   - Multiple output directories (`output/`, `data/outputs/`, `data/output/`)
   - Log files scattered across directories
   - No clear data lifecycle management

5. **Documentation Files Cluttered**
   - Many `.md` files in root directory
   - No clear documentation hierarchy
   - Status reports mixed with documentation

6. **Development Artifacts Exposed**
   - Virtual environment in root (`venv_py311/`)
   - Cache directories visible (`__pycache__/`)
   - Build artifacts not properly managed

## Proposed Directory Structure

### **New Root Structure:**

```
archivist/
├── .github/                    # GitHub workflows and templates
├── .gitignore                  # Git ignore rules
├── README.md                   # Main project documentation
├── LICENSE                     # Project license
├── pyproject.toml             # Modern Python project configuration
├── setup.py                   # Package setup (legacy support)
├── requirements/              # Dependency management
│   ├── base.txt              # Base dependencies
│   ├── dev.txt               # Development dependencies
│   ├── prod.txt              # Production dependencies
│   └── test.txt              # Test dependencies
├── archivist/                 # Main application package
│   ├── __init__.py
│   ├── core/                 # Core application modules
│   ├── web/                  # Web application components
│   ├── api/                  # API endpoints
│   ├── services/             # Business logic services
│   ├── models/               # Data models
│   ├── utils/                # Utility functions
│   └── config/               # Application configuration
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── fixtures/             # Test data and fixtures
│   ├── conftest.py           # Pytest configuration
│   └── requirements-test.txt # Test dependencies
├── scripts/                  # Utility scripts
│   ├── deployment/           # Deployment scripts
│   ├── development/          # Development utilities
│   ├── monitoring/           # Monitoring and health checks
│   ├── maintenance/          # Maintenance and cleanup
│   └── setup/                # Setup and installation
├── config/                   # Configuration files
│   ├── production/           # Production configurations
│   ├── development/          # Development configurations
│   ├── nginx/                # Nginx configurations
│   ├── systemd/              # Systemd service files
│   └── docker/               # Docker configurations
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   ├── deployment/           # Deployment guides
│   ├── development/          # Development guides
│   ├── user/                 # User documentation
│   └── status/               # Status reports and updates
├── data/                     # Data directories
│   ├── logs/                 # Application logs
│   ├── uploads/              # File uploads
│   ├── outputs/              # Processing outputs
│   ├── cache/                # Application cache
│   └── temp/                 # Temporary files
├── docker/                   # Docker-related files
│   ├── Dockerfile.web        # Web service Dockerfile
│   ├── Dockerfile.worker     # Worker service Dockerfile
│   └── docker-compose.yml    # Docker Compose configuration
└── .gitignore               # Git ignore rules
```

## Detailed Reorganization Plan

### **Phase 1: Core Application Restructuring**

#### 1.1 Create Main Application Package
```bash
# Create new application package structure
mkdir -p archivist/{core,web,api,services,models,utils,config}
```

#### 1.2 Move Core Modules
```bash
# Move existing core modules
mv core/* archivist/core/
mv web/* archivist/web/
```

#### 1.3 Update Import Statements
- Update all import statements to use new package structure
- Ensure relative imports work correctly
- Update `__init__.py` files

### **Phase 2: Test Suite Reorganization**

#### 2.1 Consolidate Test Files
```bash
# Move scattered test files to tests directory
mv test_*.py tests/
mv *.json tests/fixtures/  # Test data files
```

#### 2.2 Organize Test Structure
```bash
# Create test subdirectories
mkdir -p tests/{unit,integration,fixtures,performance}
```

#### 2.3 Update Test Configuration
- Update `pytest.ini` for new structure
- Update test discovery patterns
- Ensure test dependencies are properly managed

### **Phase 3: Scripts Organization**

#### 3.1 Categorize Scripts
```bash
# Create script categories
mkdir -p scripts/{deployment,development,monitoring,maintenance,setup}
```

#### 3.2 Move Scripts by Category
```bash
# Deployment scripts
mv scripts/deploy.sh scripts/deployment/
mv archivist-vod.service scripts/deployment/

# Development scripts
mv scripts/reorganize_codebase.py scripts/development/
mv scripts/manage_deps.py scripts/development/

# Monitoring scripts
mv monitoring_dashboard.py scripts/monitoring/
mv system_status.py scripts/monitoring/

# Setup scripts
mv setup_flex_mounts.sh scripts/setup/
mv create_credentials.sh scripts/setup/
```

### **Phase 4: Configuration Management**

#### 4.1 Organize Configuration Files
```bash
# Create configuration structure
mkdir -p config/{production,development,systemd,docker}

# Move configuration files
mv .env config/development/
mv .env.example config/development/
mv archivist-vod.service config/systemd/
mv docker-compose.yml config/docker/
mv Dockerfile.* config/docker/
```

#### 4.2 Environment-Specific Configs
- Create production configuration templates
- Separate development and production settings
- Document configuration management

### **Phase 5: Documentation Reorganization**

#### 5.1 Categorize Documentation
```bash
# Create documentation structure
mkdir -p docs/{api,deployment,development,user,status}

# Move documentation files
mv docs/API_REFERENCE.md docs/api/
mv docs/DEPLOYMENT_GUIDE.md docs/deployment/
mv docs/SERVICE_LAYER.md docs/development/
mv docs/USER_MANUAL.md docs/user/
```

#### 5.2 Status Reports Organization
```bash
# Move status reports
mv *_STATUS.md docs/status/
mv *_REPORT.md docs/status/
mv *_SUMMARY.md docs/status/
```

### **Phase 6: Data Directory Consolidation**

#### 6.1 Consolidate Data Directories
```bash
# Create unified data structure
mkdir -p data/{logs,uploads,outputs,cache,temp}

# Move existing data
mv output/* data/outputs/
mv logs/* data/logs/
mv uploads/* data/uploads/
```

#### 6.2 Clean Up Duplicates
- Remove duplicate directories
- Update all references to data paths
- Ensure proper permissions

### **Phase 7: Development Artifacts Management**

#### 7.1 Update .gitignore
```gitignore
# Virtual environments
venv*/
env*/
.venv/

# Cache directories
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Build artifacts
build/
dist/
*.egg-info/

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Application data
data/cache/
data/temp/
*.log
```

#### 7.2 Remove Exposed Artifacts
```bash
# Remove virtual environment from repository
rm -rf venv_py311/

# Remove cache directories
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

## Implementation Strategy

### **Step-by-Step Migration**

#### Step 1: Create New Structure (Non-Destructive)
```bash
# Create new directory structure without moving files
mkdir -p archivist/{core,web,api,services,models,utils,config}
mkdir -p tests/{unit,integration,fixtures,performance}
mkdir -p scripts/{deployment,development,monitoring,maintenance,setup}
mkdir -p config/{production,development,systemd,docker}
mkdir -p docs/{api,deployment,development,user,status}
mkdir -p data/{logs,uploads,outputs,cache,temp}
```

#### Step 2: Move Files Incrementally
```bash
# Move files one category at a time
# Start with least critical files (documentation, scripts)
# Then move core application files
# Finally update imports and configurations
```

#### Step 3: Update References
```bash
# Update all import statements
# Update configuration file paths
# Update documentation links
# Update deployment scripts
```

#### Step 4: Test and Validate
```bash
# Run full test suite
# Verify all functionality works
# Check deployment processes
# Validate documentation links
```

### **Rollback Plan**

#### Backup Strategy
```bash
# Create backup before reorganization
git checkout -b backup-before-reorganization
git add .
git commit -m "Backup before directory reorganization"

# Create reorganization branch
git checkout -b directory-reorganization
```

#### Rollback Commands
```bash
# If issues arise, rollback to backup
git checkout backup-before-reorganization
git branch -D directory-reorganization
```

## Benefits of New Structure

### **1. Improved Maintainability**
- Clear separation of concerns
- Logical file organization
- Easier to find and modify code
- Better code navigation

### **2. Enhanced Development Experience**
- Standard Python project structure
- Better IDE support
- Clearer import paths
- Easier testing setup

### **3. Better Deployment Management**
- Separated configuration by environment
- Clear deployment scripts
- Better Docker organization
- Simplified service management

### **4. Improved Documentation**
- Categorized documentation
- Clear status reporting
- Better user guides
- Organized API documentation

### **5. Enhanced Testing**
- Organized test structure
- Clear test data management
- Better test discovery
- Improved test performance

## Migration Checklist

### **Pre-Migration Tasks**
- [ ] Create backup branch
- [ ] Document current file locations
- [ ] Identify all import statements
- [ ] List all configuration file references
- [ ] Create rollback plan

### **Migration Tasks**
- [ ] Create new directory structure
- [ ] Move documentation files
- [ ] Move script files
- [ ] Move configuration files
- [ ] Move test files
- [ ] Move core application files
- [ ] Update import statements
- [ ] Update configuration references
- [ ] Update documentation links

### **Post-Migration Tasks**
- [ ] Run full test suite
- [ ] Verify all functionality
- [ ] Test deployment processes
- [ ] Update CI/CD pipelines
- [ ] Update documentation
- [ ] Remove old directories
- [ ] Update .gitignore

## Timeline

### **Week 1: Planning and Preparation**
- Complete detailed analysis
- Create backup branches
- Prepare migration scripts
- Document current state

### **Week 2: Core Migration**
- Move documentation and scripts
- Update basic references
- Test basic functionality
- Validate structure

### **Week 3: Application Migration**
- Move core application files
- Update import statements
- Test application functionality
- Fix any issues

### **Week 4: Finalization**
- Update all references
- Test complete system
- Update documentation
- Clean up old files

## Conclusion

This reorganization plan provides a clear path to a well-structured, maintainable codebase that follows Python best practices. The phased approach ensures minimal disruption while achieving significant improvements in code organization and maintainability.

The new structure will make the Archivist project more professional, easier to maintain, and more accessible to new developers while preserving all existing functionality. 