#!/bin/bash

# VOD Services Manual Starter
# This script provides commands to start services manually

echo "VOD Services Manual Starter"
echo "=========================="
echo ""
echo "Run these commands in separate terminals:"
echo ""
echo "Terminal 1 - Redis (if not running):"
echo "redis-server --daemonize yes"
echo ""
echo "Terminal 2 - Admin UI:"
echo "cd /opt/Archivist && source venv/bin/activate && python3 -c 'from core.admin_ui import AdminUI; AdminUI(host=\"127.0.0.1\", port=8080, dashboard_port=5051).run()'"
echo ""
echo "Terminal 3 - Celery Worker:"
echo "cd /opt/Archivist && source venv/bin/activate && celery -A core.tasks worker --loglevel=info --concurrency=2"
echo ""
echo "Terminal 4 - Celery Beat:"
echo "cd /opt/Archivist && source venv/bin/activate && celery -A core.tasks beat --loglevel=info"
echo ""
echo "After starting all services, run:"
echo "python3 test_vod_system_comprehensive.py"
echo ""
echo "To check service status:"
echo "curl http://127.0.0.1:8080/api/admin/status"
echo "redis-cli ping"
echo ""

# Check if Redis is running
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is running"
else
    echo "✗ Redis is not running"
fi

# Check if Admin UI is running
if curl -s http://127.0.0.1:8080/api/admin/status > /dev/null 2>&1; then
    echo "✓ Admin UI is running"
else
    echo "✗ Admin UI is not running"
fi

echo "" 