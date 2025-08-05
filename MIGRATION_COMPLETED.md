# Migration Guide: Old Scripts to Unified System

## 🚀 Migration Completed: 2025-08-04 17:55:10

This document shows how to use the new unified system instead of the old scripts.

## 📋 Command Mapping

### Old Commands → New Commands

**python3 scripts/deployment/start_complete_system.py** → `python3 start_archivist_unified.py complete`

**python3 scripts/deployment/start_archivist_centralized.py** → `python3 start_archivist_unified.py centralized`

**./scripts/deployment/start_archivist_centralized.sh** → `./start_archivist.sh centralized`

**python3 scripts/deployment/start_integrated_system.py** → `python3 start_archivist_unified.py integrated`

**python3 scripts/deployment/start_vod_system_simple.py** → `python3 start_archivist_unified.py vod-only`

**./start_archivist_system.sh** → `./start_archivist.sh complete`

**./start_archivist_simple.sh** → `./start_archivist.sh simple`

**./start_dashboard.sh** → `./start_archivist.sh integrated`

**--simple** → `simple`

**--integrated** → `integrated`

**--vod-only** → `vod-only`

**--centralized** → `centralized`

## 🎯 New Unified System Usage

### Basic Usage
```bash
# Start complete system (default)
./start_archivist.sh

# Start specific mode
./start_archivist.sh complete
./start_archivist.sh simple
./start_archivist.sh integrated
./start_archivist.sh vod-only
./start_archivist.sh centralized

# Use Python directly
python3 start_archivist_unified.py complete
python3 start_archivist_unified.py simple --dry-run
```

### Advanced Options
```bash
# Custom ports
./start_archivist.sh complete --ports admin=8081,dashboard=5052

# Custom configuration
./start_archivist.sh --config-file config/production.json

# Dry-run mode
./start_archivist.sh complete --dry-run

# Check status
./start_archivist.sh --status
```

## 🔧 Environment-Specific Configurations

- **Development**: `config/dev.json`
- **Staging**: `config/staging.json` 
- **Production**: `config/production.json`

## 📊 Benefits of Unified System

1. **Single Entry Point**: One script replaces 8+ old scripts
2. **Consistent Interface**: Same options across all modes
3. **Better Error Handling**: Automatic port conflict resolution
4. **Configuration Files**: Environment-specific settings
5. **Dry-Run Mode**: Test without starting services
6. **Status Monitoring**: Built-in health checks

## 🔄 Rollback

If you need to rollback to the old system:
1. Check the backup directory: `backups/migration_YYYYMMDD_HHMMSS/`
2. Restore files from the backup
3. Run the rollback script: `python3 rollback_migration.py`

## 📞 Support

For issues with the unified system:
1. Check the migration guide: `MIGRATION_GUIDE.md`
2. Review the test results: `TEST_RESULTS.md`
3. Run validation: `python3 validate_unified_system.py`
