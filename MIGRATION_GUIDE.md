# Migration Guide: Unified Startup System

## 🚀 **Overview**

This guide helps you migrate from the old duplicated startup scripts to the new unified startup system. The new system consolidates all functionality into a single, configurable entry point.

## 📋 **What Changed**

### **Before (Old System)**
- **8 different startup scripts** with duplicated code
- **Inconsistent behavior** across different scripts
- **Maintenance nightmare** - bug fixes needed in multiple files
- **User confusion** - no clear guidance on which script to use

### **After (New System)**
- **Single unified entry point** with multiple modes
- **Consistent behavior** across all modes
- **Easy maintenance** - single source of truth
- **Clear guidance** - one script with multiple options

## 🔄 **Migration Process**

### **Automated Migration (Recommended)**
Use the automated migration script for a safe, complete migration:

```bash
# Run the migration script
python3 migrate_to_unified_system.py
```

This script will:
1. ✅ Create a complete backup of all old scripts
2. ✅ Test the unified system before migration
3. ✅ Remove old duplicated scripts
4. ✅ Create migration documentation
5. ✅ Generate a migration summary

### **Manual Migration (Advanced)**
If you prefer manual migration, follow these steps:

#### **Step 1: Update Your Startup Commands**

#### **Old Commands → New Commands**

| Old Command | New Command | Description |
|-------------|-------------|-------------|
| `./start_archivist_system.sh` | `./start_archivist.sh complete` | Full system startup |
| `./start_archivist_simple.sh` | `./start_archivist.sh simple` | Simple mode with alternative ports |
| `python3 scripts/deployment/start_complete_system.py` | `./start_archivist.sh complete` | Complete system |
| `python3 scripts/deployment/start_integrated_system.py` | `./start_archivist.sh integrated` | Integrated dashboard |
| `python3 scripts/deployment/start_vod_system_simple.py` | `./start_archivist.sh vod-only` | VOD processing only |
| `python3 scripts/deployment/start_archivist_centralized.py` | `./start_archivist.sh centralized` | Centralized management |

### **Step 2: Update Your Scripts and Documentation**

#### **Update Shell Scripts**
If you have custom scripts that call the old startup commands, update them:

```bash
# Old
./start_archivist_system.sh

# New
./start_archivist.sh complete
```

#### **Update Documentation**
Update any documentation that references the old scripts:

```markdown
# Old
Run `./start_archivist_system.sh` to start the system

# New
Run `./start_archivist.sh complete` to start the system
```

### **Step 3: Use New Features**

#### **Configuration Files**
Create configuration files for different environments:

```bash
# Development
./start_archivist.sh --config-file config/dev.json

# Production
./start_archivist.sh --config-file config/prod.json

# Custom ports
./start_archivist.sh simple --ports admin=5052,dashboard=5053
```

#### **Dry Run Mode**
Test your configuration without starting services:

```bash
./start_archivist.sh complete --dry-run
```

#### **Status Check**
Check system status:

```bash
./start_archivist.sh --status
```

## 📁 **New File Structure**

```
/opt/Archivist/
├── start_archivist.sh                    # Main entry point (shell wrapper)
├── start_archivist_unified.py            # Unified Python startup script
├── config/
│   └── archivist-startup.json            # Example configuration
├── scripts/deployment/
│   ├── startup_config.py                 # Configuration management
│   └── startup_manager.py                # Core startup logic
└── [old scripts - can be removed]
    ├── start_archivist_system.sh         # ❌ Remove
    ├── start_archivist_simple.sh         # ❌ Remove
    ├── scripts/deployment/start_*.py     # ❌ Remove
    └── scripts/deployment/start_*.sh     # ❌ Remove
```

## 🎯 **Available Modes**

### **Complete Mode** (Default)
```bash
./start_archivist.sh complete
```
- Full system with all features
- Admin UI, monitoring dashboard, VOD processing
- All services enabled

### **Simple Mode**
```bash
./start_archivist.sh simple
```
- Basic system with alternative ports (5052, 5053)
- Reduced concurrency (2 workers)
- Monitoring disabled

### **Integrated Mode**
```bash
./start_archivist.sh integrated
```
- Focus on unified interface
- VOD processing and monitoring enabled
- Health checks enabled

### **VOD-Only Mode**
```bash
./start_archivist.sh vod-only
```
- VOD processing only
- Admin UI and monitoring disabled
- Reduced concurrency (2 workers)

### **Centralized Mode**
```bash
./start_archivist.sh centralized
```
- Full service management
- Auto-restart and health monitoring
- Enhanced monitoring (30s intervals)

## ⚙️ **Configuration Options**

### **Command Line Options**
```bash
# Custom ports
./start_archivist.sh complete --ports admin=8080,dashboard=5051

# Custom concurrency
./start_archivist.sh complete --concurrency 8

# Custom log level
./start_archivist.sh complete --log-level DEBUG

# Configuration file
./start_archivist.sh --config-file config/production.json
```

### **Configuration Files**
Create JSON or YAML configuration files:

```json
{
  "mode": "complete",
  "ports": {
    "admin_ui": 8080,
    "dashboard": 5051
  },
  "celery": {
    "concurrency": 4
  },
  "features": {
    "monitoring": true,
    "auto_restart": true
  }
}
```

### **Environment-Specific Configurations**
The system includes pre-configured settings for different environments:

#### **Development** (`config/dev.json`)
- Alternative ports (8081, 5052) to avoid conflicts
- Reduced concurrency (2 workers)
- Debug logging enabled
- Health monitoring disabled
- Auto-restart disabled

#### **Staging** (`config/staging.json`)
- Standard ports (8080, 5051)
- Balanced concurrency (4 workers)
- Info logging
- Health monitoring enabled
- Auto-restart enabled

#### **Production** (`config/production.json`)
- Standard ports (8080, 5051)
- High concurrency (8 workers)
- Warning-level logging
- Aggressive health monitoring (15s intervals)
- Maximum auto-restart attempts (5)

## 🔧 **Advanced Configuration**

### **Environment Variables**
The system automatically loads from `.env` files and environment variables:

```bash
# .env file
VOD_PROCESSING_TIME=19:00
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Environment variables
export ARCHIVIST_MODE=complete
export ARCHIVIST_CONCURRENCY=4
```

### **Service Configuration**
Enable/disable specific services:

```json
{
  "services": {
    "admin_ui": {
      "enabled": true,
      "auto_restart": true,
      "max_restart_attempts": 3
    },
    "monitoring_dashboard": {
      "enabled": false
    }
  }
}
```

## 🧪 **Testing the Migration**

### **1. Test Each Mode**
```bash
# Test complete mode
./start_archivist.sh complete --dry-run

# Test simple mode
./start_archivist.sh simple --dry-run

# Test integrated mode
./start_archivist.sh integrated --dry-run
```

### **2. Test Configuration Files**
```bash
# Create test config
cp config/archivist-startup.json config/test.json

# Test with config file
./start_archivist.sh --config-file config/test.json --dry-run
```

### **3. Test Legacy Compatibility**
```bash
# Test legacy options
./start_archivist.sh --simple
./start_archivist.sh --integrated
./start_archivist.sh --vod-only
```

## 🚨 **Breaking Changes**

### **What's Different**
1. **Port assignments** may be different in simple mode
2. **Concurrency levels** may be different
3. **Service startup order** is now consistent
4. **Error messages** are now standardized

### **What's the Same**
1. **All functionality** is preserved
2. **Environment variables** still work
3. **Core services** (Redis, PostgreSQL, Celery) work the same
4. **API endpoints** remain unchanged

## 🔄 **Rollback Process**

If you need to rollback to the old system:

### **Automated Rollback (Recommended)**
```bash
# Rollback to the latest backup
python3 rollback_migration.py

# Or specify a specific backup directory
python3 rollback_migration.py backups/migration_20250101_120000
```

The rollback script will:
1. ✅ Validate the backup is complete
2. ✅ Create backup of current unified system
3. ✅ Restore all old scripts from backup
4. ✅ Remove unified system files
5. ✅ Create rollback documentation

### **Manual Rollback (Advanced)**
If you prefer manual rollback:

```bash
# 1. Find your backup directory
ls backups/migration_*

# 2. Restore old scripts
cp backups/migration_YYYYMMDD_HHMMSS/scripts/deployment/start_*.py scripts/deployment/
cp backups/migration_YYYYMMDD_HHMMSS/start_*.sh ./

# 3. Remove unified system
rm start_archivist_unified.py
rm start_archivist.sh
rm -rf config/
rm scripts/deployment/startup_*.py
```

## 🛠️ **Troubleshooting**

### **Common Issues**

#### **1. "start_archivist_unified.py not found"**
```bash
# Make sure you're in the project root
cd /opt/Archivist
ls -la start_archivist_unified.py
```

#### **2. "Python modules not found"**
```bash
# Install dependencies
pip install -r requirements.txt

# Or activate virtual environment
source venv_py311/bin/activate
```

#### **3. "Port already in use"**
```bash
# The new system automatically handles port conflicts
# It will find alternative ports automatically

# Or use specific ports
./start_archivist.sh simple --ports admin=5052,dashboard=5053

# Or stop conflicting services
sudo systemctl stop nginx
```

#### **4. "Configuration file not found"**
```bash
# Create config directory
mkdir -p config

# Copy example config
cp config/archivist-startup.json config/my-config.json

# Or use environment-specific configs
./start_archivist.sh --config-file config/dev.json
```

#### **5. "Mount permission denied"**
```bash
# Fix mount permissions
./scripts/setup/fix_mount_permissions.sh

# Or run with sudo if needed
sudo ./scripts/setup/fix_mount_permissions.sh
```

#### **6. "Dashboard integration error"**
```bash
# This is now fixed in the unified system
# The system automatically handles dashboard integration

# If you still see issues, try:
./start_archivist.sh integrated --dry-run
```

### **Getting Help**
```bash
# Show help
./start_archivist.sh --help

# Show status
./start_archivist.sh --status

# Dry run to see what would happen
./start_archivist.sh complete --dry-run
```

## 📈 **Benefits After Migration**

### **1. Reduced Maintenance**
- **Single source of truth** for startup logic
- **Bug fixes apply to all modes**
- **Consistent behavior** across deployments

### **2. Improved User Experience**
- **Clear entry point** with mode selection
- **Consistent error messages**
- **Unified status reporting**

### **3. Better Code Quality**
- **DRY compliance** (no more duplication)
- **Comprehensive testing**
- **Robust error handling**

### **4. Enhanced Flexibility**
- **Configuration-driven behavior**
- **Easy to add new modes**
- **Environment-specific settings**

## 🎉 **Migration Complete**

Once you've updated your startup commands and tested the new system, you can:

1. **Remove old scripts** (optional)
2. **Update documentation**
3. **Create environment-specific configs**
4. **Enjoy the improved system!**

The new unified system provides all the functionality of the old scripts with better maintainability, consistency, and user experience. 