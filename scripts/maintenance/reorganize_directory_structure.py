#!/usr/bin/env python3
"""
Directory Structure Reorganization Script

This script automates the reorganization of the Archivist project directory structure
to improve maintainability and follow Python best practices.

Features:
- Safe file movement with backup creation
- Import statement updates
- Configuration file path updates
- Rollback capabilities
- Progress tracking and validation

Usage:
    python scripts/reorganize_directory_structure.py --dry-run  # Preview changes
    python scripts/reorganize_directory_structure.py --execute  # Perform reorganization
    python scripts/reorganize_directory_structure.py --rollback # Rollback changes
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reorganization.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DirectoryReorganizer:
    """Handles directory structure reorganization with safety features."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.reorganization_log = self.project_root / "reorganization_log.json"
        self.moved_files = []
        
        # Define new directory structure
        self.new_structure = {
            "archivist": {
                "core": "Core application modules",
                "web": "Web application components", 
                "api": "API endpoints",
                "services": "Business logic services",
                "models": "Data models",
                "utils": "Utility functions",
                "config": "Application configuration"
            },
            "tests": {
                "unit": "Unit tests",
                "integration": "Integration tests",
                "fixtures": "Test data and fixtures",
                "performance": "Performance tests"
            },
            "scripts": {
                "deployment": "Deployment scripts",
                "development": "Development utilities",
                "monitoring": "Monitoring and health checks",
                "maintenance": "Maintenance and cleanup",
                "setup": "Setup and installation"
            },
            "config": {
                "production": "Production configurations",
                "development": "Development configurations",
                "systemd": "Systemd service files",
                "docker": "Docker configurations"
            },
            "docs": {
                "api": "API documentation",
                "deployment": "Deployment guides",
                "development": "Development guides",
                "user": "User documentation",
                "status": "Status reports and updates"
            },
            "data": {
                "logs": "Application logs",
                "uploads": "File uploads",
                "outputs": "Processing outputs",
                "cache": "Application cache",
                "temp": "Temporary files"
            }
        }
        
        # Define file movement mappings
        self.file_movements = {
            # Test files
            "test_*.py": "tests/",
            "test_*.json": "tests/fixtures/",
            "test_*.txt": "tests/fixtures/",
            "test_*.wav": "tests/fixtures/",
            "test_*.scc": "tests/fixtures/",
            "test_*.srt": "tests/fixtures/",
            
            # Configuration files
            ".env": "config/development/",
            ".env.example": "config/development/",
            "archivist-vod.service": "config/systemd/",
            "docker-compose.yml": "config/docker/",
            "Dockerfile.*": "config/docker/",
            ".dockerignore": "config/docker/",
            
            # Documentation files
            "*_STATUS.md": "docs/status/",
            "*_REPORT.md": "docs/status/",
            "*_SUMMARY.md": "docs/status/",
            "*_RESOLVED.md": "docs/status/",
            "*_PROGRESS.md": "docs/status/",
            "*_UPDATES.md": "docs/status/",
            "*_GUIDE.md": "docs/user/",
            "*_MANUAL.md": "docs/user/",
            "*_REFERENCE.md": "docs/api/",
            "*_INTEGRATION.md": "docs/deployment/",
            "*_DEPLOYMENT.md": "docs/deployment/",
            "*_LAYER.md": "docs/development/",
            
            # Script files
            "start_*.py": "scripts/deployment/",
            "start_*.sh": "scripts/deployment/",
            "run_*.py": "scripts/development/",
            "run_*.sh": "scripts/development/",
            "test_*.py": "tests/",
            "monitoring_*.py": "scripts/monitoring/",
            "system_*.py": "scripts/monitoring/",
            "setup_*.sh": "scripts/setup/",
            "create_*.sh": "scripts/setup/",
            "mount_*.txt": "scripts/setup/",
            "fstab_*.txt": "scripts/setup/",
            
            # Data files
            "*.log": "data/logs/",
            "celerybeat-schedule": "data/cache/",
            "load_test_results.json": "data/outputs/",
            "test_results_*.json": "data/outputs/",
        }
        
        # Files to exclude from movement
        self.exclude_files = {
            "README.md",
            "LICENSE",
            "setup.py",
            "pyproject.toml",
            "requirements.txt",
            "pytest.ini",
            "Makefile",
            ".gitignore",
            "reorganization_log.json",
            "reorganization.log"
        }
        
        # Directories to exclude
        self.exclude_dirs = {
            ".git",
            "venv_py311",
            "__pycache__",
            "archivist.egg-info",
            "build",
            "dist"
        }
    
    def create_backup(self) -> bool:
        """Create a backup of the current directory structure."""
        try:
            logger.info(f"Creating backup at {self.backup_dir}")
            
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Copy all files except backup and cache directories
            for item in self.project_root.iterdir():
                if item.name in self.exclude_dirs or item.name.startswith("backup_"):
                    continue
                
                if item.is_file():
                    shutil.copy2(item, self.backup_dir / item.name)
                elif item.is_dir():
                    shutil.copytree(item, self.backup_dir / item.name, 
                                  ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            
            logger.info("Backup created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def create_new_structure(self) -> bool:
        """Create the new directory structure."""
        try:
            logger.info("Creating new directory structure")
            
            for parent_dir, subdirs in self.new_structure.items():
                for subdir, description in subdirs.items():
                    dir_path = self.project_root / parent_dir / subdir
                    dir_path.mkdir(parents=True, exist_ok=True)
                    
                    # Create README for each directory
                    readme_path = dir_path / "README.md"
                    if not readme_path.exists():
                        with open(readme_path, 'w') as f:
                            f.write(f"# {subdir.title()}\n\n{description}\n")
            
            logger.info("New directory structure created")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create new structure: {e}")
            return False
    
    def find_files_to_move(self) -> List[Tuple[Path, Path]]:
        """Find all files that need to be moved."""
        files_to_move = []
        
        for pattern, destination in self.file_movements.items():
            # Convert glob pattern to regex-like pattern
            if "*" in pattern:
                prefix = pattern.split("*")[0]
                suffix = pattern.split("*")[1] if len(pattern.split("*")) > 1 else ""
                
                for item in self.project_root.iterdir():
                    if item.is_file() and item.name.startswith(prefix) and item.name.endswith(suffix):
                        if item.name not in self.exclude_files:
                            dest_path = self.project_root / destination / item.name
                            files_to_move.append((item, dest_path))
            else:
                # Exact file match
                file_path = self.project_root / pattern
                if file_path.exists() and file_path.is_file():
                    dest_path = self.project_root / destination / file_path.name
                    files_to_move.append((file_path, dest_path))
        
        return files_to_move
    
    def move_files(self, files_to_move: List[Tuple[Path, Path]], dry_run: bool = False) -> bool:
        """Move files to their new locations."""
        try:
            logger.info(f"Moving {len(files_to_move)} files")
            
            for src_path, dest_path in files_to_move:
                if dry_run:
                    logger.info(f"Would move: {src_path} -> {dest_path}")
                    continue
                
                # Ensure destination directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(src_path), str(dest_path))
                self.moved_files.append((str(src_path), str(dest_path)))
                logger.info(f"Moved: {src_path} -> {dest_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to move files: {e}")
            return False
    
    def update_imports(self, dry_run: bool = False) -> bool:
        """Update import statements in Python files."""
        try:
            logger.info("Updating import statements")
            
            # Find all Python files
            python_files = list(self.project_root.rglob("*.py"))
            
            for py_file in python_files:
                if "venv" in str(py_file) or "__pycache__" in str(py_file):
                    continue
                
                try:
                    with open(py_file, 'r') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Update imports for moved modules
                    import_updates = {
                        "from core.": "from archivist.core.",
                        "import core.": "import archivist.core.",
                        "from web.": "from archivist.web.",
                        "import web.": "import archivist.web.",
                    }
                    
                    for old_import, new_import in import_updates.items():
                        content = content.replace(old_import, new_import)
                    
                    if content != original_content:
                        if dry_run:
                            logger.info(f"Would update imports in: {py_file}")
                        else:
                            with open(py_file, 'w') as f:
                                f.write(content)
                            logger.info(f"Updated imports in: {py_file}")
                            
                except Exception as e:
                    logger.warning(f"Could not process {py_file}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update imports: {e}")
            return False
    
    def update_config_paths(self, dry_run: bool = False) -> bool:
        """Update configuration file paths."""
        try:
            logger.info("Updating configuration file paths")
            
            # Find configuration files that reference paths
            config_files = [
                "config/development/.env",
                "config/development/.env.example",
                "config/systemd/archivist-vod.service",
                "config/docker/docker-compose.yml"
            ]
            
            for config_file in config_files:
                config_path = self.project_root / config_file
                if not config_path.exists():
                    continue
                
                try:
                    with open(config_path, 'r') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # Update common path references
                    path_updates = {
                        "./core/": "./archivist/core/",
                        "./web/": "./archivist/web/",
                        "./logs/": "./data/logs/",
                        "./output/": "./data/outputs/",
                        "./uploads/": "./data/uploads/",
                    }
                    
                    for old_path, new_path in path_updates.items():
                        content = content.replace(old_path, new_path)
                    
                    if content != original_content:
                        if dry_run:
                            logger.info(f"Would update paths in: {config_file}")
                        else:
                            with open(config_path, 'w') as f:
                                f.write(content)
                            logger.info(f"Updated paths in: {config_file}")
                            
                except Exception as e:
                    logger.warning(f"Could not process {config_file}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config paths: {e}")
            return False
    
    def cleanup_artifacts(self, dry_run: bool = False) -> bool:
        """Clean up development artifacts."""
        try:
            logger.info("Cleaning up development artifacts")
            
            artifacts_to_remove = [
                "venv_py311",
                "__pycache__",
                "*.pyc",
                "*.pyo",
                "*.pyd",
                ".coverage",
                "celerybeat-schedule",
                "archivist.egg-info"
            ]
            
            for artifact in artifacts_to_remove:
                if "*" in artifact:
                    # Handle glob patterns
                    for item in self.project_root.rglob(artifact):
                        if dry_run:
                            logger.info(f"Would remove: {item}")
                        else:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                            logger.info(f"Removed: {item}")
                else:
                    # Handle specific files/directories
                    artifact_path = self.project_root / artifact
                    if artifact_path.exists():
                        if dry_run:
                            logger.info(f"Would remove: {artifact_path}")
                        else:
                            if artifact_path.is_file():
                                artifact_path.unlink()
                            elif artifact_path.is_dir():
                                shutil.rmtree(artifact_path)
                            logger.info(f"Removed: {artifact_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup artifacts: {e}")
            return False
    
    def save_reorganization_log(self) -> bool:
        """Save reorganization log for potential rollback."""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "backup_dir": str(self.backup_dir),
                "moved_files": self.moved_files,
                "new_structure": self.new_structure
            }
            
            with open(self.reorganization_log, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            logger.info("Reorganization log saved")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save reorganization log: {e}")
            return False
    
    def rollback(self) -> bool:
        """Rollback reorganization changes."""
        try:
            logger.info("Rolling back reorganization changes")
            
            if not self.backup_dir.exists():
                logger.error("Backup directory not found")
                return False
            
            # Remove reorganized files
            for parent_dir in self.new_structure.keys():
                dir_path = self.project_root / parent_dir
                if dir_path.exists():
                    shutil.rmtree(dir_path)
                    logger.info(f"Removed: {dir_path}")
            
            # Restore from backup
            for item in self.backup_dir.iterdir():
                dest_path = self.project_root / item.name
                if dest_path.exists():
                    if dest_path.is_file():
                        dest_path.unlink()
                    elif dest_path.is_dir():
                        shutil.rmtree(dest_path)
                
                if item.is_file():
                    shutil.copy2(item, dest_path)
                elif item.is_dir():
                    shutil.copytree(item, dest_path)
                
                logger.info(f"Restored: {item.name}")
            
            # Clean up backup
            shutil.rmtree(self.backup_dir)
            if self.reorganization_log.exists():
                self.reorganization_log.unlink()
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False
    
    def validate_structure(self) -> bool:
        """Validate the new directory structure."""
        try:
            logger.info("Validating new directory structure")
            
            # Check that all required directories exist
            for parent_dir, subdirs in self.new_structure.items():
                for subdir in subdirs.keys():
                    dir_path = self.project_root / parent_dir / subdir
                    if not dir_path.exists():
                        logger.error(f"Missing directory: {dir_path}")
                        return False
            
            # Check that no old files remain in root
            old_files = [
                "test_*.py",
                ".env",
                "archivist-vod.service",
                "docker-compose.yml",
                "Dockerfile.*"
            ]
            
            for pattern in old_files:
                if "*" in pattern:
                    prefix = pattern.split("*")[0]
                    suffix = pattern.split("*")[1] if len(pattern.split("*")) > 1 else ""
                    
                    for item in self.project_root.iterdir():
                        if (item.is_file() and 
                            item.name.startswith(prefix) and 
                            item.name.endswith(suffix) and
                            item.name not in self.exclude_files):
                            logger.warning(f"Old file still in root: {item}")
                else:
                    file_path = self.project_root / pattern
                    if file_path.exists():
                        logger.warning(f"Old file still in root: {file_path}")
            
            logger.info("Directory structure validation completed")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False
    
    def run_tests(self) -> bool:
        """Run tests to ensure functionality is preserved."""
        try:
            logger.info("Running tests to validate reorganization")
            
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                logger.info("All tests passed")
                return True
            else:
                logger.error(f"Tests failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            return False

def main():
    """Main function to handle command line arguments and execute reorganization."""
    parser = argparse.ArgumentParser(description="Reorganize Archivist directory structure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--execute", action="store_true", help="Execute reorganization")
    parser.add_argument("--rollback", action="store_true", help="Rollback reorganization")
    parser.add_argument("--validate", action="store_true", help="Validate current structure")
    parser.add_argument("--test", action="store_true", help="Run tests after reorganization")
    
    args = parser.parse_args()
    
    reorganizer = DirectoryReorganizer()
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        
        # Create new structure
        reorganizer.create_new_structure()
        
        # Find files to move
        files_to_move = reorganizer.find_files_to_move()
        logger.info(f"Found {len(files_to_move)} files to move")
        
        # Preview file movements
        reorganizer.move_files(files_to_move, dry_run=True)
        
        # Preview import updates
        reorganizer.update_imports(dry_run=True)
        
        # Preview config updates
        reorganizer.update_config_paths(dry_run=True)
        
        logger.info("=== DRY RUN COMPLETED ===")
        
    elif args.execute:
        logger.info("=== EXECUTING REORGANIZATION ===")
        
        # Create backup
        if not reorganizer.create_backup():
            logger.error("Failed to create backup. Aborting.")
            return 1
        
        # Create new structure
        if not reorganizer.create_new_structure():
            logger.error("Failed to create new structure. Aborting.")
            return 1
        
        # Move files
        files_to_move = reorganizer.find_files_to_move()
        if not reorganizer.move_files(files_to_move):
            logger.error("Failed to move files. Aborting.")
            return 1
        
        # Update imports
        if not reorganizer.update_imports():
            logger.error("Failed to update imports. Aborting.")
            return 1
        
        # Update config paths
        if not reorganizer.update_config_paths():
            logger.error("Failed to update config paths. Aborting.")
            return 1
        
        # Clean up artifacts
        if not reorganizer.cleanup_artifacts():
            logger.warning("Failed to cleanup artifacts")
        
        # Save reorganization log
        reorganizer.save_reorganization_log()
        
        # Validate structure
        if not reorganizer.validate_structure():
            logger.warning("Structure validation failed")
        
        logger.info("=== REORGANIZATION COMPLETED ===")
        
    elif args.rollback:
        logger.info("=== ROLLING BACK REORGANIZATION ===")
        
        if not reorganizer.rollback():
            logger.error("Rollback failed")
            return 1
        
        logger.info("=== ROLLBACK COMPLETED ===")
        
    elif args.validate:
        logger.info("=== VALIDATING STRUCTURE ===")
        
        if reorganizer.validate_structure():
            logger.info("Structure validation passed")
        else:
            logger.error("Structure validation failed")
            return 1
        
    elif args.test:
        logger.info("=== RUNNING TESTS ===")
        
        if reorganizer.run_tests():
            logger.info("All tests passed")
        else:
            logger.error("Tests failed")
            return 1
        
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 