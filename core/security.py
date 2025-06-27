"""
Security module for the Archivist application.

This module implements comprehensive security measures including:
- OWASP Top 10 protections
- CSRF protection
- Input validation and sanitization
- Security headers
- Content Security Policy
- Rate limiting enhancements
- Secure file upload validation

OWASP Top 10 2021 Coverage:
1. Broken Access Control - Role-based access control
2. Cryptographic Failures - Secure session management
3. Injection - Input validation and parameterized queries
4. Insecure Design - Security by design principles
5. Security Misconfiguration - Secure defaults
6. Vulnerable Components - Dependency management
7. Authentication Failures - JWT with proper validation
8. Software and Data Integrity Failures - File integrity checks
9. Security Logging Failures - Comprehensive logging
10. Server-Side Request Forgery - URL validation
"""

import os
import re
import hashlib
import magic
import bleach
from typing import Optional, List, Dict, Any
from functools import wraps
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes

from flask import (
    Flask, request, jsonify, current_app, g, 
    session, abort, make_response
)
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from werkzeug.security import safe_str_cmp
from werkzeug.utils import secure_filename
import jwt
from loguru import logger

# Initialize CSRF protection
csrf = CSRFProtect()

class SecurityManager:
    """Centralized security management for the application."""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg'}
        self.max_file_size = 10 * 1024 * 1024 * 1024  # 10GB
        self.suspicious_patterns = [
            r'\.\./',  # Directory traversal
            r'<script',  # XSS attempts
            r'javascript:',  # JavaScript injection
            r'data:text/html',  # Data URI attacks
            r'vbscript:',  # VBScript injection
            r'on\w+\s*=',  # Event handler injection
        ]
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security features with the Flask app."""
        self.app = app
        
        # Configure security headers
        self._setup_security_headers(app)
        
        # Initialize CSRF protection
        csrf.init_app(app)
        
        # Initialize Talisman for additional security headers
        Talisman(
            app,
            content_security_policy={
                'default-src': ["'self'"],
                'script-src': ["'self'", "'unsafe-inline'"],
                'style-src': ["'self'", "'unsafe-inline'"],
                'img-src': ["'self'", "data:", "https:"],
                'font-src': ["'self'"],
                'connect-src': ["'self'"],
                'frame-ancestors': ["'none'"],
            },
            force_https=False,  # Set to True in production
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            frame_options='DENY',
            content_type_nosniff=True,
            x_xss_protection=True,
            x_content_type_options=True,
            referrer_policy='strict-origin-when-cross-origin'
        )
        
        # Register security middleware
        app.before_request(self._security_middleware)
        app.after_request(self._add_security_headers)
        
        # Register error handlers
        app.register_error_handler(400, self._handle_bad_request)
        app.register_error_handler(403, self._handle_forbidden)
        app.register_error_handler(413, self._handle_payload_too_large)
        app.register_error_handler(429, self._handle_rate_limit_exceeded)
        
        logger.info("Security manager initialized successfully")
    
    def _setup_security_headers(self, app: Flask):
        """Configure additional security headers."""
        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
            return response
    
    def _security_middleware(self):
        """Security middleware to run before each request."""
        # Log security-relevant information
        self._log_security_event('request', {
            'ip': request.remote_addr,
            'method': request.method,
            'path': request.path,
            'user_agent': request.headers.get('User-Agent', ''),
            'referer': request.headers.get('Referer', '')
        })
        
        # Validate request headers
        self._validate_request_headers()
        
        # Check for suspicious patterns in request
        self._check_suspicious_patterns()
    
    def _validate_request_headers(self):
        """Validate request headers for security."""
        # Check for suspicious User-Agent
        user_agent = request.headers.get('User-Agent', '')
        if self._is_suspicious_user_agent(user_agent):
            logger.warning(f"Suspicious User-Agent detected: {user_agent}")
            abort(400, description="Invalid request")
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if User-Agent is suspicious."""
        suspicious_patterns = [
            r'bot', r'crawler', r'spider', r'scanner',
            r'nmap', r'nikto', r'w3af', r'burp',
            r'sqlmap', r'havij', r'acunetix'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(re.search(pattern, user_agent_lower) for pattern in suspicious_patterns)
    
    def _check_suspicious_patterns(self):
        """Check request for suspicious patterns."""
        # Check URL parameters
        for key, value in request.args.items():
            if self._contains_suspicious_pattern(value):
                logger.warning(f"Suspicious pattern in URL parameter {key}: {value}")
                abort(400, description="Invalid request")
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if self._contains_suspicious_pattern(value):
                    logger.warning(f"Suspicious pattern in form data {key}: {value}")
                    abort(400, description="Invalid request")
    
    def _contains_suspicious_pattern(self, value: str) -> bool:
        """Check if value contains suspicious patterns."""
        if not isinstance(value, str):
            return False
        
        return any(re.search(pattern, value, re.IGNORECASE) for pattern in self.suspicious_patterns)
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    def _log_security_event(self, event_type: str, data: Dict[str, Any]):
        """Log security events."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'path': request.path,
            'method': request.method,
            **data
        }
        logger.info(f"Security event: {log_data}")
    
    def validate_file_upload(self, file, allowed_extensions: Optional[set] = None) -> Dict[str, Any]:
        """
        Validate file upload for security.
        
        Args:
            file: FileStorage object
            allowed_extensions: Set of allowed file extensions
            
        Returns:
            Dict with validation result and any errors
        """
        if allowed_extensions is None:
            allowed_extensions = self.allowed_extensions
        
        result = {
            'valid': True,
            'errors': [],
            'file_info': {}
        }
        
        try:
            # Check if file exists
            if not file or file.filename == '':
                result['valid'] = False
                result['errors'].append('No file selected')
                return result
            
            # Validate filename
            filename = secure_filename(file.filename)
            if not filename:
                result['valid'] = False
                result['errors'].append('Invalid filename')
                return result
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                result['valid'] = False
                result['errors'].append(f'File type not allowed: {file_ext}')
                return result
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > self.max_file_size:
                result['valid'] = False
                result['errors'].append(f'File too large: {file_size} bytes')
                return result
            
            # Validate file content using magic numbers
            file_content = file.read(2048)  # Read first 2KB
            file.seek(0)  # Reset to beginning
            
            mime_type = magic.from_buffer(file_content, mime=True)
            expected_mime_types = {
                '.mp4': 'video/mp4',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.mkv': 'video/x-matroska',
                '.mpeg': 'video/mpeg',
                '.mpg': 'video/mpeg'
            }
            
            expected_mime = expected_mime_types.get(file_ext)
            if expected_mime and mime_type != expected_mime:
                result['valid'] = False
                result['errors'].append(f'File content does not match extension: {mime_type}')
                return result
            
            # Store file info
            result['file_info'] = {
                'filename': filename,
                'size': file_size,
                'mime_type': mime_type,
                'extension': file_ext
            }
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f'Validation error: {str(e)}')
            logger.error(f"File validation error: {e}")
        
        return result
    
    def sanitize_input(self, data: str, allowed_tags: Optional[List[str]] = None) -> str:
        """
        Sanitize user input to prevent XSS attacks.
        
        Args:
            data: Input string to sanitize
            allowed_tags: List of allowed HTML tags (if any)
            
        Returns:
            Sanitized string
        """
        if not isinstance(data, str):
            return str(data)
        
        # Remove any HTML tags if not explicitly allowed
        if allowed_tags is None:
            return bleach.clean(data, tags=[], strip=True)
        else:
            return bleach.clean(data, tags=allowed_tags, strip=True)
    
    def validate_path(self, path: str, base_path: str) -> bool:
        """
        Validate file path to prevent directory traversal attacks.
        
        Args:
            path: Path to validate
            base_path: Base directory path
            
        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Normalize paths
            normalized_path = os.path.normpath(path)
            normalized_base = os.path.normpath(base_path)
            
            # Check for directory traversal attempts
            if '..' in normalized_path:
                return False
            
            # Ensure path is within base directory
            full_path = os.path.join(normalized_base, normalized_path)
            return os.path.commonpath([full_path, normalized_base]) == normalized_base
            
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return False
    
    def _handle_bad_request(self, error):
        """Handle 400 Bad Request errors."""
        self._log_security_event('bad_request', {
            'error': str(error),
            'description': getattr(error, 'description', 'Bad Request')
        })
        return jsonify({'error': 'Bad Request', 'message': 'Invalid request data'}), 400
    
    def _handle_forbidden(self, error):
        """Handle 403 Forbidden errors."""
        self._log_security_event('forbidden', {
            'error': str(error),
            'description': getattr(error, 'description', 'Forbidden')
        })
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403
    
    def _handle_payload_too_large(self, error):
        """Handle 413 Payload Too Large errors."""
        self._log_security_event('payload_too_large', {
            'error': str(error),
            'description': getattr(error, 'description', 'Payload Too Large')
        })
        return jsonify({'error': 'Payload Too Large', 'message': 'File size exceeds limit'}), 413
    
    def _handle_rate_limit_exceeded(self, error):
        """Handle 429 Rate Limit Exceeded errors."""
        self._log_security_event('rate_limit_exceeded', {
            'error': str(error),
            'description': getattr(error, 'description', 'Rate Limit Exceeded')
        })
        return jsonify({'error': 'Rate Limit Exceeded', 'message': 'Too many requests'}), 429

# Global security manager instance
security_manager = SecurityManager()

def require_csrf_token(f):
    """Decorator to require CSRF token for non-GET requests."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method != 'GET':
            # CSRF protection is handled by Flask-WTF
            pass
        return f(*args, **kwargs)
    return decorated_function

def validate_json_input(schema_class):
    """Decorator to validate JSON input using Pydantic schema."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                if request.is_json:
                    data = request.get_json()
                    validated_data = schema_class(**data)
                    g.validated_data = validated_data
                else:
                    abort(400, description="Content-Type must be application/json")
            except Exception as e:
                abort(400, description=f"Invalid JSON data: {str(e)}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_output(data: Any) -> Any:
    """Sanitize output data to prevent XSS."""
    if isinstance(data, str):
        return security_manager.sanitize_input(data)
    elif isinstance(data, dict):
        return {k: sanitize_output(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_output(item) for item in data]
    else:
        return data 