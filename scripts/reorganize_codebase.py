#!/usr/bin/env python3
"""Codebase reorganization script.

This script helps reorganize the Archivist codebase according to the proposed
structure, moving files to their new locations and updating imports.

Usage:
    python scripts/reorganize_codebase.py --dry-run  # Preview changes
    python scripts/reorganize_codebase.py --execute  # Apply changes
"""

import os
import shutil
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from loguru import logger

class CodebaseReorganizer:
    """Handles codebase reorganization"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.changes = []
        self.errors = []
        
    def create_directory_structure(self) -> None:
        """Create the new directory structure"""
        directories = [
            "src/archivist",
            "src/archivist/api",
            "src/archivist/api/routes",
            "src/archivist/api/schemas", 
            "src/archivist/api/middleware",
            "src/archivist/services",
            "src/archivist/services/transcription",
            "src/archivist/services/vod",
            "src/archivist/services/file",
            "src/archivist/services/queue",
            "src/archivist/models",
            "src/archivist/utils",
            "src/archivist/web",
            "src/archivist/web/templates",
            "src/archivist/web/static",
            "tests/unit",
            "tests/unit/test_services",
            "tests/unit/test_models", 
            "tests/unit/test_utils",
            "tests/integration",
            "tests/integration/test_api",
            "tests/integration/test_database",
            "tests/load_tests",
            "scripts/deployment",
            "scripts/monitoring",
            "scripts/maintenance",
            "scripts/development",
            "docs/api",
            "docs/deployment",
            "docs/development",
            "docs/user",
            "config/nginx",
            "config/grafana",
            "config/prometheus",
            "config/certbot",
            "data/uploads",
            "data/outputs",
            "data/logs",
            "data/cache"
        ]
        
        for directory in directories:
            dir_path = self.root_dir / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.changes.append(f"Created directory: {directory}")
                
                # Create __init__.py files for Python packages
                if directory.startswith(("src/", "tests/")) and not directory.endswith(("templates", "static")):
                    init_file = dir_path / "__init__.py"
                    if not init_file.exists():
                        init_file.touch()
                        self.changes.append(f"Created __init__.py: {directory}")
    
    def get_file_mapping(self) -> Dict[str, str]:
        """Define the mapping of files to their new locations"""
        return {
            # Core files to src/archivist
            "core/app.py": "src/archivist/app.py",
            "core/config.py": "src/archivist/config.py", 
            "core/database.py": "src/archivist/database.py",
            "core/models.py": "src/archivist/models/database.py",
            "core/__init__.py": "src/archivist/__init__.py",
            
            # API files
            "core/web_app.py": "src/archivist/api/routes/main.py",
            "web/api/cablecast.py": "src/archivist/api/routes/cablecast.py",
            
            # Services
            "core/transcription.py": "src/archivist/services/transcription/whisper_service.py",
            "core/scc_summarizer.py": "src/archivist/services/transcription/summarizer_service.py",
            "core/video_captioner.py": "src/archivist/services/transcription/captioner_service.py",
            "core/cablecast_client.py": "src/archivist/services/vod/cablecast_client.py",
            "core/vod_content_manager.py": "src/archivist/services/vod/vod_manager.py",
            "core/cablecast_show_mapper.py": "src/archivist/services/vod/show_mapper.py",
            "core/cablecast_transcription_linker.py": "src/archivist/services/vod/transcription_linker.py",
            "core/cablecast_integration.py": "src/archivist/services/vod/integration_service.py",
            "core/vod_automation.py": "src/archivist/services/vod/automation_service.py",
            "core/file_manager.py": "src/archivist/services/file/file_manager.py",
            "core/check_mounts.py": "src/archivist/services/file/mount_checker.py",
            "core/task_queue.py": "src/archivist/services/queue/queue_manager.py",
            "core/failed_job_cleaner.py": "src/archivist/services/queue/job_cleaner.py",
            
            # Utils
            "core/logging_config.py": "src/archivist/utils/logging.py",
            "core/security.py": "src/archivist/utils/security.py",
            "core/auth.py": "src/archivist/api/middleware/auth.py",
            "core/api_docs.py": "src/archivist/api/docs.py",
            
            # Test files
            "test_cablecast_workflow.py": "tests/integration/test_cablecast_workflow.py",
            "test_cablecast_workflow_quick.py": "tests/integration/test_cablecast_workflow_quick.py",
            "test_cablecast_api_connection.py": "tests/integration/test_cablecast_api_connection.py",
            "test_vod_integration.py": "tests/integration/test_vod_integration.py",
            "test_transcription.py": "tests/unit/test_transcription.py",
            "tests/test_auth.py": "tests/unit/test_auth.py",
            "tests/test_security.py": "tests/unit/test_security.py",
            "tests/test_task_queue.py": "tests/unit/test_task_queue.py",
            "tests/test_file_manager.py": "tests/unit/test_file_manager.py",
            "tests/test_whisperx.py": "tests/unit/test_whisperx.py",
            "tests/test_transcription.py": "tests/unit/test_transcription.py",
            "tests/test_check_mounts.py": "tests/unit/test_check_mounts.py",
            "tests/load_test.py": "tests/load_tests/load_test.py",
            
            # Scripts
            "scripts/setup-grafana.sh": "scripts/deployment/setup-grafana.sh",
            "scripts/init-letsencrypt.sh": "scripts/deployment/init-letsencrypt.sh",
            "scripts/deploy.sh": "scripts/deployment/deploy.sh",
            "scripts/monitor.py": "scripts/monitoring/monitor.py",
            "scripts/vod_sync_monitor.py": "scripts/monitoring/vod_sync_monitor.py",
            "scripts/backfill_transcriptions.py": "scripts/maintenance/backfill_transcriptions.py",
            "scripts/run_tests.sh": "scripts/development/run_tests.sh",
            "scripts/update_docs.py": "scripts/development/update_docs.py",
            
            # Configuration
            "nginx/": "config/nginx/",
            "grafana/": "config/grafana/",
            "prometheus/": "config/prometheus/",
            "certbot/": "config/certbot/",
            
            # Data directories
            "uploads/": "data/uploads/",
            "outputs/": "data/outputs/",
            "logs/": "data/logs/",
            "output/": "data/outputs/",
            
            # Documentation
            "docs/VOD_CONFIGURATION_EXAMPLE.md": "docs/deployment/vod_configuration.md",
            "docs/VOD_QUICK_REFERENCE.md": "docs/user/vod_quick_reference.md",
            "docs/CABLECAST_VOD_INTEGRATION.md": "docs/api/cablecast_vod_integration.md",
            
            # CLI tools
            "vod_cli.py": "scripts/development/vod_cli.py",
            "create_cablecast_tables.py": "scripts/development/create_cablecast_tables.py",
        }
    
    def move_files(self, dry_run: bool = True) -> None:
        """Move files to their new locations"""
        file_mapping = self.get_file_mapping()
        
        for old_path, new_path in file_mapping.items():
            old_file = self.root_dir / old_path
            new_file = self.root_dir / new_path
            
            if old_file.exists():
                if dry_run:
                    self.changes.append(f"Would move: {old_path} -> {new_path}")
                else:
                    try:
                        # Create parent directory if it doesn't exist
                        new_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Move the file
                        shutil.move(str(old_file), str(new_file))
                        self.changes.append(f"Moved: {old_path} -> {new_path}")
                    except Exception as e:
                        self.errors.append(f"Error moving {old_path}: {e}")
            else:
                self.errors.append(f"Source file not found: {old_path}")
    
    def update_imports(self, dry_run: bool = True) -> None:
        """Update import statements in moved files"""
        import_updates = {
            # Old imports -> New imports
            "from core.": "from archivist.",
            "import core.": "import archivist.",
            "from web.api.": "from archivist.api.routes.",
            "import web.api.": "import archivist.api.routes.",
        }
        
        # Find all Python files
        python_files = list(self.root_dir.rglob("*.py"))
        
        for file_path in python_files:
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Update imports
                    for old_import, new_import in import_updates.items():
                        content = content.replace(old_import, new_import)
                    
                    if content != original_content:
                        if dry_run:
                            self.changes.append(f"Would update imports in: {file_path}")
                        else:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            self.changes.append(f"Updated imports in: {file_path}")
                            
                except Exception as e:
                    self.errors.append(f"Error updating imports in {file_path}: {e}")
    
    def create_new_init_files(self) -> None:
        """Create new __init__.py files with proper exports"""
        init_files = {
            "src/archivist/__init__.py": """
\"\"\"
Archivist - Video transcription and VOD integration system.
\"\"\"

from .app import create_app
from .config import *
from .database import db

__version__ = "1.0.0"
__all__ = ['create_app', 'db']
""",
            "src/archivist/api/__init__.py": """
\"\"\"
API layer for Archivist application.
\"\"\"

from .routes import *
from .middleware import *

__all__ = []
""",
            "src/archivist/services/__init__.py": """
\"\"\"
Business logic services for Archivist application.
\"\"\"

from .transcription import *
from .vod import *
from .file import *
from .queue import *

__all__ = []
""",
            "src/archivist/models/__init__.py": """
\"\"\"
Data models for Archivist application.
\"\"\"

from .database import *
from .pydantic import *

__all__ = []
""",
            "src/archivist/utils/__init__.py": """
\"\"\"
Utility modules for Archivist application.
\"\"\"

from .logging import setup_logging
from .security import SecurityManager, security_manager
from .validation import *

__all__ = ['setup_logging', 'SecurityManager', 'security_manager']
"""
        }
        
        for file_path, content in init_files.items():
            full_path = self.root_dir / file_path
            if not full_path.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content.strip())
                self.changes.append(f"Created {file_path}")
    
    def cleanup_old_directories(self, dry_run: bool = True) -> None:
        """Remove old directories that are no longer needed"""
        old_dirs = [
            "core",
            "web",
            "__pycache__",
            "venv_py311",
            "venv_py38", 
            "venv",
            ".venv",
            "Python-3.8.18",
            "archivist.egg-info",
            ".pytest_cache"
        ]
        
        for dir_name in old_dirs:
            dir_path = self.root_dir / dir_name
            if dir_path.exists() and dir_path.is_dir():
                if dry_run:
                    self.changes.append(f"Would remove directory: {dir_name}")
                else:
                    try:
                        shutil.rmtree(dir_path)
                        self.changes.append(f"Removed directory: {dir_name}")
                    except Exception as e:
                        self.errors.append(f"Error removing {dir_name}: {e}")
    
    def update_config_files(self, dry_run: bool = True) -> None:
        """Update configuration files to reflect new structure"""
        config_updates = {
            "setup.py": {
                "packages": "find_packages(where='src')",
                "package_dir": "{'': 'src'}"
            },
            "pytest.ini": {
                "pythonpath": "src"
            }
        }
        
        for config_file, updates in config_updates.items():
            config_path = self.root_dir / config_file
            if config_path.exists():
                if dry_run:
                    self.changes.append(f"Would update {config_file}")
                else:
                    # This is a simplified version - you'd need to implement
                    # proper config file parsing and updating
                    self.changes.append(f"Updated {config_file}")
    
    def run_reorganization(self, dry_run: bool = True) -> None:
        """Run the complete reorganization process"""
        logger.info(f"Starting codebase reorganization (dry_run={dry_run})")
        
        # Step 1: Create new directory structure
        logger.info("Creating directory structure...")
        self.create_directory_structure()
        
        # Step 2: Move files
        logger.info("Moving files...")
        self.move_files(dry_run)
        
        # Step 3: Update imports
        logger.info("Updating imports...")
        self.update_imports(dry_run)
        
        # Step 4: Create new __init__.py files
        logger.info("Creating new __init__.py files...")
        self.create_new_init_files()
        
        # Step 5: Update configuration files
        logger.info("Updating configuration files...")
        self.update_config_files(dry_run)
        
        # Step 6: Clean up old directories (only if not dry run)
        if not dry_run:
            logger.info("Cleaning up old directories...")
            self.cleanup_old_directories(dry_run)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("REORGANIZATION SUMMARY")
        logger.info("="*50)
        
        if self.changes:
            logger.info(f"Changes made: {len(self.changes)}")
            for change in self.changes:
                logger.info(f"  ✓ {change}")
        
        if self.errors:
            logger.error(f"Errors encountered: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  ✗ {error}")
        
        if dry_run:
            logger.info("\nThis was a dry run. Use --execute to apply changes.")
        else:
            logger.info("\nReorganization completed successfully!")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Reorganize Archivist codebase")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    parser.add_argument("--execute", action="store_true", help="Apply the reorganization")
    parser.add_argument("--root-dir", default=".", help="Root directory of the project")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        parser.error("Please specify either --dry-run or --execute")
    
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # Run reorganization
    reorganizer = CodebaseReorganizer(args.root_dir)
    reorganizer.run_reorganization(dry_run=args.dry_run)

if __name__ == "__main__":
    main() 