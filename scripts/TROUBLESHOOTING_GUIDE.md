# Troubleshooting Guide

## Overview
This guide provides solutions for common issues encountered with the Archivist system.

## 🚨 **Critical Issues**

### **Issue: Web UI Not Loading**
**Symptoms:**
- Browser shows "Connection refused" or "Page not found"
- API endpoints return 500 errors
- System status shows "unhealthy"

**Diagnosis:**
```bash
# Check if web server is running
ps aux | grep -E "(gunicorn|python.*test_web_ui)"

# Check port availability
netstat -tlnp | grep :5050

# Check logs
tail -f logs/archivist.log
```

**Solutions:**
1. **Start the web server:**
   ```bash
   # Development mode
   bash scripts/deployment/run_web.sh development
   
   # Production mode
   bash scripts/deployment/run_web.sh production
   ```

2. **Check virtual environment:**
   ```bash
   source venv_py311/bin/activate
   ```

3. **Verify dependencies:**
   ```bash
   pip install gunicorn flask-socketio
   ```

### **Issue: Redis Connection Failed**
**Symptoms:**
- Monitoring shows "Redis: unhealthy"
- Task queue not working
- Rate limiting errors

**Diagnosis:**
```bash
# Check Redis service
redis-cli ping

# Check Redis logs
sudo journalctl -u redis-server -f
```

**Solutions:**
1. **Start Redis service:**
   ```bash
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

2. **Check Redis configuration:**
   ```bash
   # Verify Redis is listening
   netstat -tlnp | grep :6379
   
   # Test connection
   redis-cli -h localhost -p 6379 ping
   ```

3. **Check environment variables:**
   ```bash
   echo $REDIS_HOST
   echo $REDIS_PORT
   ```

### **Issue: Database Connection Failed**
**Symptoms:**
- Monitoring shows "Database: unhealthy"
- API errors related to database
- Transcription results not saved

**Diagnosis:**
```bash
# Check PostgreSQL service
pg_isready -h localhost

# Check database logs
sudo journalctl -u postgresql -f
```

**Solutions:**
1. **Start PostgreSQL service:**
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Check database configuration:**
   ```bash
   # Verify DATABASE_URL
   echo $DATABASE_URL
   
   # Test connection
   psql $DATABASE_URL -c "SELECT 1;"
   ```

3. **Check database permissions:**
   ```bash
   # Verify user exists
   sudo -u postgres psql -c "\du"
   
   # Create user if needed
   sudo -u postgres createuser archivist
   sudo -u postgres createdb archivist
   ```

## 🔧 **Performance Issues**

### **Issue: High CPU Usage**
**Symptoms:**
- System becomes slow
- Monitoring shows CPU > 80%
- Transcription tasks hang

**Diagnosis:**
```bash
# Check CPU usage
top -p $(pgrep -f archivist)

# Check Celery workers
celery -A core.tasks inspect active
```

**Solutions:**
1. **Reduce worker concurrency:**
   ```bash
   # Edit worker script
   # Change --concurrency=2 to --concurrency=1
   ```

2. **Monitor resource usage:**
   ```bash
   python3 scripts/monitoring/unified_monitor.py --continuous --interval 30
   ```

3. **Restart workers:**
   ```bash
   pkill -f celery
   bash scripts/deployment/run_worker.sh
   ```

### **Issue: High Memory Usage**
**Symptoms:**
- System becomes unresponsive
- Out of memory errors
- Processes killed by OOM killer

**Diagnosis:**
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check Redis memory
redis-cli info memory
```

**Solutions:**
1. **Restart Redis:**
   ```bash
   sudo systemctl restart redis-server
   ```

2. **Clear Redis cache:**
   ```bash
   redis-cli flushall
   ```

3. **Monitor memory usage:**
   ```bash
   python3 scripts/monitoring/unified_monitor.py --type system
   ```

## 📁 **File System Issues**

### **Issue: NAS Mount Not Accessible**
**Symptoms:**
- File browser shows "Error loading files"
- VOD paths not found
- Transcription jobs fail

**Diagnosis:**
```bash
# Check mount points
df -h | grep /mnt

# Check file permissions
ls -la /mnt/

# Test file access
find /mnt -name "*.mp4" | head -5
```

**Solutions:**
1. **Remount NAS:**
   ```bash
   sudo mount -a
   ```

2. **Check mount configuration:**
   ```bash
   cat /etc/fstab | grep /mnt
   ```

3. **Verify network connectivity:**
   ```bash
   ping [NAS_IP_ADDRESS]
   ```

### **Issue: Disk Space Full**
**Symptoms:**
- File operations fail
- Log files grow large
- System becomes slow

**Diagnosis:**
```bash
# Check disk usage
df -h

# Check large files
du -sh /opt/Archivist/logs/*
du -sh /opt/Archivist/output/*
```

**Solutions:**
1. **Clean up logs:**
   ```bash
   # Remove old log files
   find /opt/Archivist/logs -name "*.log" -mtime +7 -delete
   ```

2. **Clean up output:**
   ```bash
   # Remove old output files
   find /opt/Archivist/output -name "*.mp4" -mtime +30 -delete
   ```

3. **Monitor disk usage:**
   ```bash
   python3 scripts/monitoring/unified_monitor.py --type system
   ```

## 🔐 **Security Issues**

### **Issue: CSRF Token Errors**
**Symptoms:**
- API requests fail with 403 errors
- "CSRF token missing" errors
- Web UI shows authentication errors

**Diagnosis:**
```bash
# Check CSRF endpoint
curl -s http://localhost:5050/api/csrf-token

# Check browser console for errors
```

**Solutions:**
1. **Clear browser cache:**
   - Hard refresh (Ctrl+F5)
   - Clear browser data

2. **Check CSRF configuration:**
   ```bash
   # Verify SECRET_KEY is set
   echo $SECRET_KEY
   ```

3. **Restart web server:**
   ```bash
   pkill -f gunicorn
   bash scripts/deployment/run_web.sh development
   ```

### **Issue: Rate Limiting Errors**
**Symptoms:**
- API requests return 429 errors
- "Too many requests" messages
- Web UI becomes unresponsive

**Diagnosis:**
```bash
# Check rate limit keys
redis-cli keys "flask-limiter:*"

# Check rate limit configuration
python3 scripts/monitoring/unified_monitor.py --type rate_limits
```

**Solutions:**
1. **Clear rate limits:**
   ```bash
   redis-cli del $(redis-cli keys "flask-limiter:*")
   ```

2. **Adjust rate limits:**
   ```bash
   # Edit .env file
   export RATE_LIMIT_DAILY=500
   export RATE_LIMIT_HOURLY=100
   ```

3. **Restart Redis:**
   ```bash
   sudo systemctl restart redis-server
   ```

## 🧪 **Testing Issues**

### **Issue: Tests Fail**
**Symptoms:**
- Test scripts return errors
- API tests fail
- Monitoring tests show unhealthy status

**Diagnosis:**
```bash
# Run test script
bash scripts/development/run_tests.sh

# Check test logs
tail -f logs/test.log
```

**Solutions:**
1. **Verify environment:**
   ```bash
   # Check virtual environment
   which python3
   echo $VIRTUAL_ENV
   
   # Check dependencies
   pip list | grep -E "(flask|celery|redis)"
   ```

2. **Run individual tests:**
   ```bash
   # Test API endpoints
   curl -s http://localhost:5050/api/queue
   curl -s http://localhost:5050/api/browse
   curl -s http://localhost:5050/api/csrf-token
   ```

3. **Check service status:**
   ```bash
   python3 scripts/monitoring/unified_monitor.py --type all
   ```

## 📊 **Monitoring Issues**

### **Issue: Monitoring Script Fails**
**Symptoms:**
- Monitoring script crashes
- No monitoring data
- Health checks fail

**Diagnosis:**
```bash
# Run monitoring with verbose output
python3 scripts/monitoring/unified_monitor.py --type all

# Check monitoring logs
tail -f logs/unified_monitor.log
```

**Solutions:**
1. **Check dependencies:**
   ```bash
   pip install psutil redis requests
   ```

2. **Verify configuration:**
   ```bash
   # Check environment variables
   echo $REDIS_HOST
   echo $API_HOST
   echo $API_PORT
   ```

3. **Run individual checks:**
   ```bash
   python3 scripts/monitoring/unified_monitor.py --type system
   python3 scripts/monitoring/unified_monitor.py --type api
   ```

## 🆘 **Emergency Procedures**

### **System Unresponsive**
1. **Stop all processes:**
   ```bash
   bash scripts/deployment/stop_archivist.sh
   ```

2. **Restart services:**
   ```bash
   sudo systemctl restart redis-server
   sudo systemctl restart postgresql
   ```

3. **Start fresh:**
   ```bash
   bash scripts/deployment/start_system.sh development
   ```

### **Data Loss Prevention**
1. **Backup database:**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

2. **Backup configuration:**
   ```bash
   cp .env .env.backup
   cp -r logs logs.backup
   ```

3. **Check disk space:**
   ```bash
   df -h
   ```

## 📞 **Getting Help**

### **Before Contacting Support:**
1. **Collect logs:**
   ```bash
   # System logs
   tail -100 logs/archivist.log > issue_logs.txt
   
   # Monitoring data
   cp logs/health_check.json issue_monitoring.json
   
   # System status
   python3 scripts/monitoring/unified_monitor.py --type all > issue_status.txt
   ```

2. **Document the issue:**
   - What were you doing when the issue occurred?
   - What error messages did you see?
   - What steps have you already tried?

3. **Check known issues:**
   - Review this troubleshooting guide
   - Check the migration guide
   - Review recent changes

### **Support Information:**
- **Logs Location**: `/opt/Archivist/logs/`
- **Configuration**: `/opt/Archivist/.env`
- **Scripts**: `/opt/Archivist/scripts/`
- **Documentation**: `/opt/Archivist/scripts/README.md`