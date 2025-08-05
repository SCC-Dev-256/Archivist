#!/usr/bin/env python3
"""
Broker Connectivity Test

This script comprehensively tests broker connectivity from Celery's perspective.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(message: str, level: str = "INFO"):
    """Log messages with timestamps."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def main():
    """Main test function."""
    log("Testing Broker Connectivity from Celery's Perspective")
    log("=" * 60)
    
    # Test 1: Check environment variables
    log("\n=== Environment Variables Check ===")
    eager_vars = [
        'CELERY_TASK_ALWAYS_EAGER',
        'CELERY_ALWAYS_EAGER',
        'CELERY_EAGER_PROPAGATES_EXCEPTIONS',
        'CELERY_TASK_EAGER_PROPAGATES'
    ]
    
    for var in eager_vars:
        value = os.getenv(var)
        log(f"{var}: {value if value else 'Not set'}")
        if value and value.lower() in ['true', '1', 'yes']:
            log(f"⚠ {var} is forcing eager mode!", "WARNING")
    
    # Test 2: Check Redis connection string format
    log("\n=== Redis Connection String Analysis ===")
    try:
        from core.config import REDIS_URL
        log(f"REDIS_URL: {REDIS_URL}")
        
        # Parse the URL
        from urllib.parse import urlparse
        parsed = urlparse(REDIS_URL)
        log(f"  - Scheme: {parsed.scheme}")
        log(f"  - Host: {parsed.hostname}")
        log(f"  - Port: {parsed.port}")
        log(f"  - Path: {parsed.path}")
        log(f"  - Username: {parsed.username}")
        log(f"  - Password: {'***' if parsed.password else 'None'}")
        
        # Test direct Redis connection
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        log("✓ Direct Redis connection successful")
        
    except Exception as e:
        log(f"✗ Redis connection string analysis failed: {e}", "ERROR")
        return 1
    
    # Test 3: Test Celery broker connection
    log("\n=== Celery Broker Connection Test ===")
    try:
        from celery import Celery
        
        # Create a test app with the same configuration
        test_app = Celery('test_broker')
        test_app.conf.broker_url = REDIS_URL
        test_app.conf.result_backend = REDIS_URL
        
        log("✓ Test Celery app created")
        
        # Test broker connection using Celery's internal methods
        try:
            # Test Redis connection directly
            import redis
            r = redis.from_url(REDIS_URL)
            r.ping()
            log("✓ Celery Redis backend connection successful")
        except Exception as e:
            log(f"✗ Celery Redis backend connection failed: {e}", "ERROR")
        
        # Test broker connection using Celery's broker
        try:
            # Test Celery broker connection
            test_app.control.ping()
            log("✓ Celery broker connection successful")
        except Exception as e:
            log(f"✗ Celery broker connection failed: {e}", "ERROR")
            
    except Exception as e:
        log(f"✗ Celery broker test failed: {e}", "ERROR")
        return 1
    
    # Test 4: Test main app broker connection
    log("\n=== Main App Broker Connection Test ===")
    try:
        from core.tasks import celery_app
        
        # Check if the app can connect to its broker
        try:
            # Try to access the broker directly
            broker_url = getattr(celery_app.conf, 'broker_url', None)
            log(f"Main app broker URL: {broker_url}")
            
            if broker_url:
                # Test connection using the same URL
                r = redis.from_url(broker_url)
                r.ping()
                log("✓ Main app broker URL is accessible")
            else:
                log("✗ Main app broker URL is not set", "ERROR")
                
        except Exception as e:
            log(f"✗ Main app broker connection test failed: {e}", "ERROR")
            
    except Exception as e:
        log(f"✗ Main app broker test failed: {e}", "ERROR")
        return 1
    
    # Test 5: Check Celery configuration in detail
    log("\n=== Detailed Celery Configuration Check ===")
    try:
        from core.tasks import celery_app
        
        # Check all relevant configuration settings
        config_settings = [
            'broker_url',
            'result_backend',
            'task_always_eager',
            'task_eager_propagates',
            'broker_connection_retry',
            'broker_connection_max_retries',
            'broker_connection_timeout',
            'broker_transport_options',
            'broker_pool_limit',
            'broker_heartbeat',
            'broker_login_method',
            'broker_use_ssl',
            'broker_ssl_cert_reqs',
            'broker_ssl_ca_certs',
            'broker_ssl_certfile',
            'broker_ssl_keyfile',
        ]
        
        for setting in config_settings:
            try:
                value = getattr(celery_app.conf, setting, None)
                if value is not None:
                    log(f"  {setting}: {value}")
            except Exception:
                pass
                
    except Exception as e:
        log(f"✗ Configuration check failed: {e}", "ERROR")
        return 1
    
    # Test 6: Test with different Redis connection formats
    log("\n=== Redis Connection Format Tests ===")
    redis_formats = [
        'redis://localhost:6379/0',
        'redis://127.0.0.1:6379/0',
        'redis://localhost:6379',
        'redis://127.0.0.1:6379',
    ]
    
    for redis_format in redis_formats:
        try:
            r = redis.from_url(redis_format)
            r.ping()
            log(f"✓ {redis_format} - Direct connection works")
            
            # Test Celery app with this format
            test_app = Celery('test_format')
            test_app.conf.broker_url = redis_format
            test_app.conf.result_backend = redis_format
            
            @test_app.task
            def test_task():
                return "test"
            
            result = test_task.delay()
            log(f"  - Task result type: {type(result)}")
            
        except Exception as e:
            log(f"✗ {redis_format} - Failed: {e}", "ERROR")
    
    # Test 7: Check if there are any Celery workers running
    log("\n=== Celery Worker Status Check ===")
    try:
        import subprocess
        
        # Check for running Celery processes
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        celery_processes = [line for line in result.stdout.split('\n') if 'celery' in line.lower()]
        
        if celery_processes:
            log("✓ Celery processes found:")
            for process in celery_processes[:5]:  # Show first 5
                log(f"  - {process.strip()}")
        else:
            log("⚠ No Celery processes found", "WARNING")
            
        # Check Celery worker status
        try:
            result = subprocess.run(['celery', '-A', 'core.tasks', 'inspect', 'active'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                log("✓ Celery inspect active successful")
                log(f"  Output: {result.stdout[:200]}...")
            else:
                log(f"⚠ Celery inspect failed: {result.stderr}", "WARNING")
        except Exception as e:
            log(f"⚠ Celery inspect failed: {e}", "WARNING")
            
    except Exception as e:
        log(f"✗ Worker status check failed: {e}", "ERROR")
    
    log("\n" + "=" * 60)
    log("Broker connectivity test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 