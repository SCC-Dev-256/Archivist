# Script Migration Guide

## Overview
This guide helps you migrate from the old script architecture to the new consolidated script system.

## 🚨 **Breaking Changes**

### **Worker System Migration (RQ → Celery)**
**Old Commands:**
```bash
# Old RQ worker
bash scripts/deployment/run_worker.sh
```

**New Commands:**
```bash
# New Celery worker
bash scripts/deployment/run_worker.sh

# Debug worker (consolidated)
bash scripts/deployment/run_worker_debug.sh
```

### **Web Server Consolidation**
**Old Commands:**
```bash
# Old separate scripts
python3 test_web_ui.py
bash scripts/deployment/run_web.sh
```

**New Commands:**
```bash
# Unified web server with modes
bash scripts/deployment/run_web.sh development  # Flask-SocketIO
bash scripts/deployment/run_web.sh production   # Gunicorn
```

### **Startup Script Consolidation**
**Old Commands:**
```bash
# Multiple startup scripts
bash scripts/deployment/start_archivist.sh
bash scripts/deployment/start_archivist_centralized.sh
python3 scripts/deployment/start_integrated_system.py
```

**New Commands:**
```bash
# Unified startup system
bash scripts/deployment/start_system.sh full        # Complete system
bash scripts/deployment/start_system.sh development # Development mode
bash scripts/deployment/start_system.sh web         # Web only
bash scripts/deployment/start_system.sh worker      # Worker only
```

### **Monitoring Consolidation**
**Old Commands:**
```bash
# Separate monitoring scripts
python3 scripts/monitoring/monitor.py
python3 scripts/monitoring/system_status.py
python3 scripts/monitoring/vod_sync_monitor.py
```

**New Commands:**
```bash
# Unified monitoring
python3 scripts/monitoring/unified_monitor.py --type all
python3 scripts/monitoring/unified_monitor.py --type system
python3 scripts/monitoring/unified_monitor.py --type api
python3 scripts/monitoring/unified_monitor.py --type vod
python3 scripts/monitoring/unified_monitor.py --continuous --interval 30
```

## 📋 **Migration Checklist**

### **Phase 1: Environment Setup**
- [ ] **Update Virtual Environment**: Ensure `venv_py311` is active
- [ ] **Install Dependencies**: `pip install gunicorn`
- [ ] **Verify Services**: Redis and PostgreSQL running
- [ ] **Update Environment Variables**: Check `.env` file

### **Phase 2: Script Migration**
- [ ] **Replace Worker Scripts**: Use new Celery-based workers
- [ ] **Update Web Server**: Use unified web server with modes
- [ ] **Consolidate Startup**: Use unified startup system
- [ ] **Update Monitoring**: Use unified monitoring framework

### **Phase 3: Testing**
- [ ] **Test Development Mode**: `bash scripts/deployment/start_system.sh development`
- [ ] **Test Production Mode**: `bash scripts/deployment/start_system.sh full`
- [ ] **Test Monitoring**: `python3 scripts/monitoring/unified_monitor.py --type all`
- [ ] **Verify API Endpoints**: Test web UI functionality

## 🔄 **Command Mapping**

### **Development Workflow**
| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `python3 test_web_ui.py` | `bash scripts/deployment/run_web.sh development` | Development server |
| `bash scripts/deployment/run_worker.sh` | `bash scripts/deployment/run_worker.sh` | Same command, different backend |
| `python3 scripts/monitoring/monitor.py` | `python3 scripts/monitoring/unified_monitor.py --type all` | Enhanced monitoring |

### **Production Workflow**
| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `bash scripts/deployment/start_archivist.sh` | `bash scripts/deployment/start_system.sh full` | Complete system |
| `bash scripts/deployment/run_web.sh` | `bash scripts/deployment/run_web.sh production` | Production server |
| `bash scripts/deployment/run_worker_debug.sh` | `bash scripts/deployment/run_worker_debug.sh` | Debug worker |

### **Monitoring Workflow**
| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `python3 scripts/monitoring/monitor.py` | `python3 scripts/monitoring/unified_monitor.py --type system` | System monitoring |
| `python3 scripts/monitoring/system_status.py` | `python3 scripts/monitoring/unified_monitor.py --type api` | API monitoring |
| `python3 scripts/monitoring/vod_sync_monitor.py` | `python3 scripts/monitoring/unified_monitor.py --type vod` | VOD monitoring |

## ⚠️ **Common Issues and Solutions**

### **Issue: "ModuleNotFoundError: No module named 'core'**
**Solution:**
```bash
# Ensure virtual environment is activated
source venv_py311/bin/activate

# Set PYTHONPATH
export PYTHONPATH=/opt/Archivist
```

### **Issue: "Redis connection failed"**
**Solution:**
```bash
# Check Redis status
redis-cli ping

# Start Redis if needed
sudo systemctl start redis-server
```

### **Issue: "Database connection failed"**
**Solution:**
```bash
# Check PostgreSQL status
pg_isready -h localhost

# Start PostgreSQL if needed
sudo systemctl start postgresql

# Check DATABASE_URL in .env file
cat .env | grep DATABASE_URL
```

### **Issue: "Gunicorn not found"**
**Solution:**
```bash
# Install gunicorn
pip install gunicorn

# Or use development mode instead
bash scripts/deployment/run_web.sh development
```

## 🎯 **Quick Migration Commands**

### **For Development:**
```bash
# 1. Activate environment
source venv_py311/bin/activate

# 2. Start development system
bash scripts/deployment/start_system.sh development

# 3. Monitor system
python3 scripts/monitoring/unified_monitor.py --type all
```

### **For Production:**
```bash
# 1. Activate environment
source venv_py311/bin/activate

# 2. Start production system
bash scripts/deployment/start_system.sh full

# 3. Monitor continuously
python3 scripts/monitoring/unified_monitor.py --continuous --interval 60
```

## 📊 **Benefits of Migration**

### **Before Migration:**
- 15+ separate scripts
- Inconsistent interfaces
- Manual service management
- Separate monitoring tools

### **After Migration:**
- 9 core unified scripts
- Consistent command-line interfaces
- Automated service management
- Comprehensive monitoring framework

## 🆘 **Support**

If you encounter issues during migration:

1. **Check the troubleshooting section** in this guide
2. **Review the logs**: `tail -f logs/archivist.log`
3. **Run health checks**: `python3 scripts/monitoring/unified_monitor.py --type all`
4. **Verify services**: Check Redis and PostgreSQL status

## 📝 **Deprecation Timeline**

### **Phase 1 (Current)**: 
- Old scripts still available but deprecated
- New scripts fully functional
- Migration guide provided

### **Phase 2 (Next Release)**:
- Old scripts will show deprecation warnings
- New scripts become default
- Documentation updated

### **Phase 3 (Future Release)**:
- Old scripts removed
- Only new consolidated scripts available
- Complete migration required