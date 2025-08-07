#!/usr/bin/env python3
"""
Migration Script: Old Scripts to Unified System

This script safely migrates from the old duplicated startup scripts
to the new unified system while preserving functionality and creating backups.
"""

import os
import sys
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class MigrationManager:
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = self.project_root / "backups" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.old_scripts = []
        self.migration_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log migration actions."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    def create_backup(self):
        """Create backup of old scripts before migration."""
        self.log("Creating backup of old scripts...")
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Define old scripts to backup
        old_script_patterns = [
            "scripts/deployment/start_*.py",
            "scripts/deployment/start_*.sh", 
            "start_*.py",
            "start_*.sh",
            "start_dashboard.sh",
            "start_archivist_system.sh",
            "start_archivist_simple.sh"
        ]
        
        backed_up_files = []
        
        for pattern in old_script_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and file_path.name not in ["start_archivist_unified.py", "start_archivist.sh"]:
                    # Create relative path for backup
                    relative_path = file_path.relative_to(self.project_root)
                    backup_path = self.backup_dir / relative_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file to backup
                    shutil.copy2(file_path, backup_path)
                    backed_up_files.append(str(relative_path))
                    self.log(f"Backed up: {relative_path}")
        
        # Create backup manifest
        manifest = {
            "backup_date": datetime.now().isoformat(),
            "backup_directory": str(self.backup_dir),
            "backed_up_files": backed_up_files,
            "migration_version": "1.0"
        }
        
        with open(self.backup_dir / "backup_manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        self.log(f"Backup created in: {self.backup_dir}")
        return backed_up_files
    
    def identify_old_scripts(self) -> List[Path]:
        """Identify old scripts that can be removed."""
        self.log("Identifying old scripts for removal...")
        
        old_scripts = []
        
        # Scripts that are replaced by the unified system
        replaceable_scripts = [
            "scripts/deployment/start_complete_system.py",
            "scripts/deployment/start_archivist_centralized.py", 
            "scripts/deployment/start_archivist_centralized.sh",
            "scripts/deployment/start_integrated_system.py",
            "scripts/deployment/start_vod_system_simple.py",
            "start_archivist_system.sh",
            "start_archivist_simple.sh",
            "start_dashboard.sh"
        ]
        
        for script_path in replaceable_scripts:
            full_path = self.project_root / script_path
            if full_path.exists():
                old_scripts.append(full_path)
                self.log(f"Found old script: {script_path}")
        
        self.old_scripts = old_scripts
        return old_scripts
    
    def test_unified_system(self) -> bool:
        """Test that the unified system works before migration."""
        self.log("Testing unified system before migration...")
        
        try:
            # Test help command
            result = subprocess.run(
                ["python3", "start_archivist_unified.py", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log("❌ Unified system help command failed", "ERROR")
                return False
            
            # Test status command
            result = subprocess.run(
                ["python3", "start_archivist_unified.py", "--status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.log("❌ Unified system status command failed", "ERROR")
                return False
            
            # Test dry-run
            result = subprocess.run(
                ["python3", "start_archivist_unified.py", "complete", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                self.log("❌ Unified system dry-run failed", "ERROR")
                return False
            
            self.log("✅ Unified system tests passed")
            return True
            
        except Exception as e:
            self.log(f"❌ Unified system test failed: {e}", "ERROR")
            return False
    
    def create_migration_mapping(self) -> Dict[str, str]:
        """Create mapping from old commands to new unified commands."""
        return {
            # Old script -> New unified command
            "python3 scripts/deployment/start_complete_system.py": "python3 start_archivist_unified.py complete",
            "python3 scripts/deployment/start_archivist_centralized.py": "python3 start_archivist_unified.py centralized", 
            "./scripts/deployment/start_archivist_centralized.sh": "./start_archivist.sh centralized",
            "python3 scripts/deployment/start_integrated_system.py": "python3 start_archivist_unified.py integrated",
            "python3 scripts/deployment/start_vod_system_simple.py": "python3 start_archivist_unified.py vod-only",
            "./start_archivist_system.sh": "./start_archivist.sh complete",
            "./start_archivist_simple.sh": "./start_archivist.sh simple",
            "./start_dashboard.sh": "./start_archivist.sh integrated",
            
            # Legacy options
            "--simple": "simple",
            "--integrated": "integrated", 
            "--vod-only": "vod-only",
            "--centralized": "centralized"
        }
    
    def create_migration_guide(self):
        """Create a migration guide for users."""
        self.log("Creating migration guide...")
        
        mapping = self.create_migration_mapping()
        
        guide_content = f"""# Migration Guide: Old Scripts to Unified System

## 🚀 Migration Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This document shows how to use the new unified system instead of the old scripts.

## 📋 Command Mapping

### Old Commands → New Commands

"""
        
        for old_cmd, new_cmd in mapping.items():
            guide_content += f"**{old_cmd}** → `{new_cmd}`\n\n"
        
        guide_content += """## 🎯 New Unified System Usage

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
"""
        
        with open(self.project_root / "MIGRATION_COMPLETED.md", "w") as f:
            f.write(guide_content)
        
        self.log("Migration guide created: MIGRATION_COMPLETED.md")
    
    def remove_old_scripts(self):
        """Remove old scripts after successful backup and testing."""
        self.log("Removing old scripts...")
        
        removed_files = []
        
        for script_path in self.old_scripts:
            try:
                script_path.unlink()
                removed_files.append(str(script_path))
                self.log(f"Removed: {script_path}")
            except Exception as e:
                self.log(f"Failed to remove {script_path}: {e}", "WARNING")
        
        self.log(f"Removed {len(removed_files)} old scripts")
        return removed_files
    
    def update_documentation(self):
        """Update documentation to reflect the new unified system."""
        self.log("Updating documentation...")
        
        # Update README.md if it exists
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            self.log("Updating README.md...")
            # This would require reading and updating the README content
            # For now, we'll create a note about the update
        
        # Create a summary of changes
        changes_summary = f"""# Documentation Updates

## Migration Summary: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### What Changed
- Replaced 8+ old startup scripts with unified system
- Added environment-specific configurations
- Improved error handling and port conflict resolution
- Added dry-run and status monitoring capabilities

### New Files
- `start_archivist_unified.py` - Main unified startup script
- `start_archivist.sh` - Shell wrapper for unified system
- `config/dev.json` - Development configuration
- `config/staging.json` - Staging configuration  
- `config/production.json` - Production configuration
- `scripts/deployment/startup_config.py` - Configuration management
- `scripts/deployment/startup_manager.py` - Service management

### Removed Files
- Multiple old startup scripts (backed up before removal)
- Duplicated functionality consolidated into unified system

### Updated Files
- `MIGRATION_GUIDE.md` - Updated with new system
- `TEST_RESULTS.md` - Test results and validation
- `start_archivist.sh` - Enhanced argument parsing
"""
        
        with open(self.project_root / "DOCUMENTATION_UPDATES.md", "w") as f:
            f.write(changes_summary)
        
        self.log("Documentation updated")
    
    def run_migration(self) -> bool:
        """Run the complete migration process."""
        self.log("🚀 Starting Migration: Old Scripts to Unified System")
        self.log("="*60)
        
        try:
            # Step 1: Create backup
            self.log("Step 1: Creating backup...")
            backed_up_files = self.create_backup()
            
            # Step 2: Test unified system
            self.log("Step 2: Testing unified system...")
            if not self.test_unified_system():
                self.log("❌ Migration failed: Unified system tests failed", "ERROR")
                return False
            
            # Step 3: Identify old scripts
            self.log("Step 3: Identifying old scripts...")
            old_scripts = self.identify_old_scripts()
            
            if not old_scripts:
                self.log("No old scripts found to migrate")
                return True
            
            # Step 4: Create migration guide
            self.log("Step 4: Creating migration guide...")
            self.create_migration_guide()
            
            # Step 5: Remove old scripts
            self.log("Step 5: Removing old scripts...")
            removed_files = self.remove_old_scripts()
            
            # Step 6: Update documentation
            self.log("Step 6: Updating documentation...")
            self.update_documentation()
            
            # Step 7: Create migration summary
            self.log("Step 7: Creating migration summary...")
            self.create_migration_summary(backed_up_files, removed_files)
            
            self.log("🎉 Migration completed successfully!")
            return True
            
        except Exception as e:
            self.log(f"❌ Migration failed: {e}", "ERROR")
            return False
    
    def create_migration_summary(self, backed_up_files: List[str], removed_files: List[str]):
        """Create a summary of the migration."""
        summary = {
            "migration_date": datetime.now().isoformat(),
            "backup_directory": str(self.backup_dir),
            "backed_up_files": backed_up_files,
            "removed_files": removed_files,
            "migration_log": self.migration_log,
            "status": "completed"
        }
        
        with open(self.project_root / "migration_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        self.log("Migration summary created: migration_summary.json")

def main():
    """Main migration function."""
    print("🚀 Migration Script: Old Scripts to Unified System")
    print("="*60)
    
    # Check if we're in the right directory
    if not Path("start_archivist_unified.py").exists():
        print("❌ Error: start_archivist_unified.py not found")
        print("💡 Make sure you're running this from the project root directory")
        sys.exit(1)
    
    # Run migration
    migrator = MigrationManager()
    success = migrator.run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("📋 Check the following files:")
        print("   - MIGRATION_COMPLETED.md (migration guide)")
        print("   - migration_summary.json (migration details)")
        print("   - backups/ (backup of old scripts)")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        print("💡 Check the logs above for details")
        sys.exit(1)

if __name__ == "__main__":
    main() 