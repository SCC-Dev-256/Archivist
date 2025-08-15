#!/usr/bin/env python3
"""
Unified Startup Configuration System

This module provides configuration management for the Archivist system startup,
consolidating all the different startup modes into a single, configurable system.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

class StartupMode(Enum):
    """Available startup modes for the Archivist system."""
    COMPLETE = "complete"      # Full system with all features
    SIMPLE = "simple"          # Basic system with alternative ports
    INTEGRATED = "integrated"  # Integrated dashboard mode
    VOD_ONLY = "vod-only"      # VOD processing only
    CENTRALIZED = "centralized" # Centralized service management

@dataclass
class ServiceConfig:
    """Configuration for individual services."""
    enabled: bool = True
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay: int = 10
    health_check_timeout: int = 30

@dataclass
class PortConfig:
    """Port configuration for services."""
    admin_ui: int = 8080
    dashboard: int = 5051
    api: int = 5050
    celery_flower: int = 5555
    redis: int = 6379
    postgresql: int = 5432

@dataclass
class CeleryConfig:
    """Celery worker configuration."""
    concurrency: int = 4
    queues: List[str] = field(default_factory=lambda: ["vod_processing", "default"])
    hostname: str = "vod_worker@%h"
    log_level: str = "info"
    scheduler: str = "celery.beat.PersistentScheduler"

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file_level: str = "DEBUG"
    rotation: str = "10 MB"
    retention: str = "7 days"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    file_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    enabled: bool = True
    interval: int = 60  # seconds
    timeout: int = 5    # seconds
    max_failures: int = 3

@dataclass
class StartupConfig:
    """Main configuration for the Archivist system startup."""
    
    # Basic configuration
    mode: StartupMode = StartupMode.COMPLETE
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    # Service configuration
    services: Dict[str, ServiceConfig] = field(default_factory=lambda: {
        "redis": ServiceConfig(),
        "postgresql": ServiceConfig(),
        "celery_worker": ServiceConfig(),
        "celery_beat": ServiceConfig(),
        "admin_ui": ServiceConfig(),
        "monitoring_dashboard": ServiceConfig(),
        "vod_sync_monitor": ServiceConfig(),
    })
    
    # Port configuration
    ports: PortConfig = field(default_factory=PortConfig)
    
    # Celery configuration
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    
    # Logging configuration
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Health check configuration
    health_checks: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    
    # Environment configuration
    environment: Dict[str, str] = field(default_factory=dict)
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "vod_processing": True,
        "transcription": True,
        "monitoring": True,
        "admin_ui": True,
        "auto_restart": True,
        "health_monitoring": True,
        "flex_integration": True,
    })
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Set mode-specific configurations
        self._apply_mode_configuration()
        
        # Load environment variables
        self._load_environment()
        
        # Validate configuration
        self._validate_configuration()
    
    def _apply_mode_configuration(self):
        """Apply mode-specific configuration overrides."""
        if self.mode == StartupMode.SIMPLE:
            # Simple mode uses alternative ports
            self.ports.admin_ui = 5052
            self.ports.dashboard = 5053
            self.celery.concurrency = 2
            self.features["monitoring"] = False
            
        elif self.mode == StartupMode.VOD_ONLY:
            # VOD-only mode disables some features
            self.features["admin_ui"] = False
            self.features["monitoring"] = False
            self.celery.concurrency = 2
            self.services["admin_ui"].enabled = False
            self.services["monitoring_dashboard"].enabled = False
            
        elif self.mode == StartupMode.INTEGRATED:
            # Integrated mode focuses on unified interface
            self.features["vod_processing"] = True
            self.features["monitoring"] = True
            self.health_checks.enabled = True
            
        elif self.mode == StartupMode.CENTRALIZED:
            # Centralized mode with full service management
            self.features["auto_restart"] = True
            self.features["health_monitoring"] = True
            self.health_checks.enabled = True
            self.health_checks.interval = 30
    
    def _load_environment(self):
        """Load configuration from environment variables."""
        # Load from .env file if it exists
        env_file = self.project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.environment[key.strip()] = value.strip()
        
        # Override with environment variables
        for key, value in os.environ.items():
            if key.startswith('ARCHIVIST_'):
                config_key = key[10:].lower()  # Remove ARCHIVIST_ prefix
                self.environment[config_key] = value
    
    def _validate_configuration(self):
        """Validate the configuration."""
        # Check for port conflicts
        used_ports = set()
        for port_name, port_value in self.ports.__dict__.items():
            if port_value in used_ports:
                raise ValueError(f"Port conflict: {port_name} uses port {port_value} which is already in use")
            used_ports.add(port_value)
        
        # Validate project root
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        
        # Validate concurrency settings
        if self.celery.concurrency < 1:
            raise ValueError("Celery concurrency must be at least 1")
    
    def get_service_config(self, service_name: str) -> ServiceConfig:
        """Get configuration for a specific service."""
        return self.services.get(service_name, ServiceConfig())
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return self.features.get(feature_name, False)
    
    def get_environment_var(self, key: str, default: str = "") -> str:
        """Get environment variable value."""
        return self.environment.get(key, os.environ.get(key, default))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            "mode": self.mode.value,
            "project_root": str(self.project_root),
            "ports": self.ports.__dict__,
            "celery": self.celery.__dict__,
            "logging": self.logging.__dict__,
            "health_checks": self.health_checks.__dict__,
            "features": self.features,
            "environment_keys": list(self.environment.keys()),
        }

def create_config_from_args(args: Optional[Dict[str, Any]] = None) -> StartupConfig:
    """Create configuration from command line arguments."""
    if args is None:
        args = {}
    
    # Parse mode
    mode_str = args.get('mode', 'complete')
    try:
        mode = StartupMode(mode_str)
    except ValueError:
        raise ValueError(f"Invalid mode: {mode_str}. Valid modes: {[m.value for m in StartupMode]}")
    
    # Create base configuration
    config = StartupConfig(mode=mode)
    
    # Apply argument overrides
    if 'ports' in args:
        port_pairs = args['ports'].split(',')
        for pair in port_pairs:
            if '=' in pair:
                service, port = pair.split('=', 1)
                setattr(config.ports, service, int(port))
    
    if 'concurrency' in args:
        config.celery.concurrency = int(args['concurrency'])
    
    if 'log_level' in args:
        config.logging.level = args['log_level']
    
    return config

def load_config_from_file(config_file: Path) -> StartupConfig:
    """Load configuration from a JSON/YAML file."""
    import json
    import yaml
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_file, 'r') as f:
        if config_file.suffix == '.json':
            data = json.load(f)
        elif config_file.suffix in ['.yml', '.yaml']:
            data = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
    
    # Convert dictionary to StartupConfig
    # This is a simplified version - in practice, you'd want more robust conversion
    mode = StartupMode(data.get('mode', 'complete'))
    config = StartupConfig(mode=mode)
    
    # Apply other settings from file
    if 'ports' in data:
        for key, value in data['ports'].items():
            setattr(config.ports, key, value)
    
    if 'celery' in data:
        for key, value in data['celery'].items():
            setattr(config.celery, key, value)
    
    return config 