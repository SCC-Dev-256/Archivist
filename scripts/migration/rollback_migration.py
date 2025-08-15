#!/usr/bin/env python3
"""
Rollback Script: Unified System to Old Scripts

This script allows rolling back from the unified system to the old scripts
if needed. It restores files from the backup created during migration.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class RollbackManager:
    def __init__(self, backup_dir: str = None):
        self.project_root = Path.cwd()
        self.backup_dir = Path(backup_dir) if backup_dir else self.find_latest_backup()
        self.rollback_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log rollback actions."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.rollback_log.append(log_entry)
        print(log_entry)
    
    def find_latest_backup(self) -> Path:
        """Find the latest backup directory."""
        backups_dir = self.project_root / "backups"
        if not backups_dir.exists():
            raise FileNotFoundError("No backups directory found")
        
        # Find migration backup directories
        migration_backups = [d for d in backups_dir.iterdir() 
                           if d.is_dir() and d.name.startswith("migration_")]
        
        if not migration_backups:
            raise FileNotFoundError("No migration backups found")
        
        # Sort by creation time and get the latest
        latest_backup = max(migration_backups, key=lambda d: d.stat().st_mtime)
        self.log(f"Found latest backup: {latest_backup}")
        return latest_backup
    
    def validate_backup(self) -> bool:
        """Validate that the backup is complete and valid."""
        self.log("Validating backup...")
        
        # Check if backup directory exists
        if not self.backup_dir.exists():
            self.log(f"❌ Backup directory not found: {self.backup_dir}", "ERROR")
            return False
        
        # Check for backup manifest
        manifest_path = self.backup_dir / "backup_manifest.json"
        if not manifest_path.exists():
            self.log("❌ Backup manifest not found", "ERROR")
            return False
        
        # Load and validate manifest
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            self.log(f"Backup date: {manifest.get('backup_date', 'Unknown')}")
            self.log(f"Backed up files: {len(manifest.get('backed_up_files', []))}")
            
            # Check if all backed up files exist
            for file_path in manifest.get('backed_up_files', []):
                backup_file = self.backup_dir / file_path
                if not backup_file.exists():
                    self.log(f"❌ Backed up file missing: {file_path}", "ERROR")
                    return False
            
            self.log("✅ Backup validation passed")
            return True
            
        except Exception as e:
            self.log(f"❌ Backup validation failed: {e}", "ERROR")
            return False
    
    def backup_current_system(self):
        """Create backup of current unified system before rollback."""
        self.log("Creating backup of current unified system...")
        
        current_backup_dir = self.project_root / "backups" / f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Files to backup from current system
        current_files = [
            "start_archivist_unified.py",
            "start_archivist.sh",
            "config/dev.json",
            "config/staging.json", 
            "config/production.json",
            "scripts/deployment/startup_config.py",
            "scripts/deployment/startup_manager.py"
        ]
        
        backed_up_files = []
        
        for file_path in current_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                backup_path = current_backup_dir / file_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_path)
                backed_up_files.append(file_path)
                self.log(f"Backed up current: {file_path}")
        
        # Create current backup manifest
        current_manifest = {
            "rollback_date": datetime.now().isoformat(),
            "backup_directory": str(current_backup_dir),
            "backed_up_files": backed_up_files,
            "rollback_version": "1.0"
        }
        
        with open(current_backup_dir / "rollback_manifest.json", "w") as f:
            json.dump(current_manifest, f, indent=2)
        
        self.log(f"Current system backed up to: {current_backup_dir}")
        return current_backup_dir
    
    def restore_old_scripts(self) -> List[str]:
        """Restore old scripts from backup."""
        self.log("Restoring old scripts...")
        
        # Load backup manifest
        manifest_path = self.backup_dir / "backup_manifest.json"
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        restored_files = []
        
        for file_path in manifest.get('backed_up_files', []):
            backup_file = self.backup_dir / file_path
            restore_file = self.project_root / file_path
            
            try:
                # Create parent directory if needed
                restore_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Restore file
                shutil.copy2(backup_file, restore_file)
                restored_files.append(file_path)
                self.log(f"Restored: {file_path}")
                
            except Exception as e:
                self.log(f"Failed to restore {file_path}: {e}", "WARNING")
        
        self.log(f"Restored {len(restored_files)} files")
        return restored_files
    
    def remove_unified_system(self):
        """Remove unified system files."""
        self.log("Removing unified system files...")
        
        files_to_remove = [
            "start_archivist_unified.py",
            "start_archivist.sh",
            "config/dev.json",
            "config/staging.json",
            "config/production.json",
            "scripts/deployment/startup_config.py", 
            "scripts/deployment/startup_manager.py"
        ]
        
        removed_files = []
        
        for file_path in files_to_remove:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    full_path.unlink()
                    removed_files.append(file_path)
                    self.log(f"Removed: {file_path}")
                except Exception as e:
                    self.log(f"Failed to remove {file_path}: {e}", "WARNING")
        
        self.log(f"Removed {len(removed_files)} unified system files")
        return removed_files
    
    def create_rollback_guide(self):
        """Create a rollback guide."""
        self.log("Creating rollback guide...")
        
        guide_content = f"""# Rollback Guide: Unified System to Old Scripts

## 🔄 Rollback Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This document confirms that the system has been rolled back to the old scripts.

## 📋 What Was Restored

The following old scripts have been restored:
"""
        
        # Load backup manifest to get file list
        manifest_path = self.backup_dir / "backup_manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            for file_path in manifest.get('backed_up_files', []):
                guide_content += f"- `{file_path}`\n"
        
        guide_content += f"""
## 📁 Backup Information

- **Original Backup**: {self.backup_dir}
- **Rollback Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 Using the Old System

You can now use the old scripts as before:

```bash
# Complete system
python3 scripts/deployment/start_complete_system.py

# Integrated system  
python3 scripts/deployment/start_integrated_system.py

# VOD system
python3 scripts/deployment/start_vod_system_simple.py

# Dashboard
./start_dashboard.sh
```

## ⚠️ Important Notes

1. **Unified system removed**: The new unified system has been removed
2. **Old scripts restored**: All old scripts have been restored from backup
3. **Configuration files**: Old configuration approach is restored
4. **No automatic rollback**: You'll need to manually migrate again if desired

## 🔧 If You Want to Migrate Again

If you want to try the unified system again:

1. Run the migration script: `python3 migrate_to_unified_system.py`
2. The unified system will be restored from the rollback backup
3. Follow the migration guide: `MIGRATION_COMPLETED.md`

## 📞 Support

For issues with the old system:
1. Check the original documentation
2. Review the backup manifest: `backups/migration_*/backup_manifest.json`
3. Restore from a different backup if needed
"""
        
        with open(self.project_root / "ROLLBACK_COMPLETED.md", "w") as f:
            f.write(guide_content)
        
        self.log("Rollback guide created: ROLLBACK_COMPLETED.md")
    
    def run_rollback(self) -> bool:
        """Run the complete rollback process."""
        self.log("🔄 Starting Rollback: Unified System to Old Scripts")
        self.log("="*60)
        
        try:
            # Step 1: Validate backup
            self.log("Step 1: Validating backup...")
            if not self.validate_backup():
                self.log("❌ Rollback failed: Backup validation failed", "ERROR")
                return False
            
            # Step 2: Backup current system
            self.log("Step 2: Backing up current system...")
            current_backup = self.backup_current_system()
            
            # Step 3: Restore old scripts
            self.log("Step 3: Restoring old scripts...")
            restored_files = self.restore_old_scripts()
            
            # Step 4: Remove unified system
            self.log("Step 4: Removing unified system...")
            removed_files = self.remove_unified_system()
            
            # Step 5: Create rollback guide
            self.log("Step 5: Creating rollback guide...")
            self.create_rollback_guide()
            
            # Step 6: Create rollback summary
            self.log("Step 6: Creating rollback summary...")
            self.create_rollback_summary(restored_files, removed_files, current_backup)
            
            self.log("🎉 Rollback completed successfully!")
            return True
            
        except Exception as e:
            self.log(f"❌ Rollback failed: {e}", "ERROR")
            return False
    
    def create_rollback_summary(self, restored_files: List[str], removed_files: List[str], current_backup: Path):
        """Create a summary of the rollback."""
        summary = {
            "rollback_date": datetime.now().isoformat(),
            "original_backup_directory": str(self.backup_dir),
            "current_backup_directory": str(current_backup),
            "restored_files": restored_files,
            "removed_files": removed_files,
            "rollback_log": self.rollback_log,
            "status": "completed"
        }
        
        with open(self.project_root / "rollback_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        self.log("Rollback summary created: rollback_summary.json")

def main():
    """Main rollback function."""
    print("🔄 Rollback Script: Unified System to Old Scripts")
    print("="*60)
    
    # Check command line arguments
    backup_dir = None
    if len(sys.argv) > 1:
        backup_dir = sys.argv[1]
        print(f"Using specified backup directory: {backup_dir}")
    
    try:
        # Run rollback
        rollback_manager = RollbackManager(backup_dir)
        success = rollback_manager.run_rollback()
        
        if success:
            print("\n🎉 Rollback completed successfully!")
            print("📋 Check the following files:")
            print("   - ROLLBACK_COMPLETED.md (rollback guide)")
            print("   - rollback_summary.json (rollback details)")
            print("   - backups/ (backup of unified system)")
            sys.exit(0)
        else:
            print("\n❌ Rollback failed!")
            print("💡 Check the logs above for details")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you have a valid backup directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 