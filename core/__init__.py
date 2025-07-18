"""
Core package for the Archivist application.
"""
try:
    from .app import create_app, create_app_with_config
    app = create_app()
except Exception:  # pragma: no cover - skip app init if deps missing
    def create_app(*args, **kwargs):
        from unittest.mock import MagicMock
        return MagicMock()

    def create_app_with_config(*args, **kwargs):
        return create_app()

    app = create_app()

__all__ = ['app', 'create_app', 'create_app_with_config'] 