# 🖥️ Archivist GUI Monitoring Guide

## 🚀 **Quick Access URLs**

### **Primary Monitoring Dashboard**
- **URL:** http://localhost:5051
- **Purpose:** Real-time system monitoring, health checks, and VOD processing status
- **Auto-refresh:** Every 30 seconds
- **Features:** System resources, Celery workers, flex mounts, API health

### **Admin UI Dashboard**
- **URL:** http://localhost:8080
- **Purpose:** Administrative interface, task management, and queue monitoring
- **Features:** Celery worker status, job queue management, city configuration

## 📊 **Current System Status** (as of 2025-07-17 15:46)

### ✅ **System Health Overview**
- **Overall Status:** Degraded (6 degraded, 7 healthy components)
- **Celery Workers:** 3 workers running (healthy)
- **System Resources:** CPU 6.4%, Memory 16.8%, Disk 2.7% (healthy)
- **Cablecast API:** Responding normally (healthy)

### 🗂️ **Flex Server Storage Status**
- ✅ **Healthy Mounts (5/9):**
  - `/mnt/flex-1` (Birchwood) - 2.7TB free
  - `/mnt/flex-5` (Spare Storage 1) - 2.9TB free
  - `/mnt/flex-6` (Spare Storage 2) - 3.6TB free
  - `/mnt/flex-8` (White Bear Lake) - 1.5TB free

- ⚠️ **Degraded Mounts (4/9):**
  - `/mnt/flex-2` (Dellwood/Grant/Willernie) - Write permission issues
  - `/mnt/flex-3` (Lake Elmo) - Write permission issues
  - `/mnt/flex-4` (Mahtomedi) - Write permission issues
  - `/mnt/flex-7` (Oakdale) - Write permission issues

### 🔄 **VOD Processing Status**
- **Queue Status:** 112 jobs queued, 0 failed
- **Active Workers:** 2 Celery workers processing tasks
- **Recent Task:** VOD processing task triggered (ID: 068f2052-1cf8-40a4-8491-32f57e96d727)
- **Caption Generation:** ✅ Fixed (faster_whisper dependency installed)

## 🎯 **How to Monitor VOD Processing in Real-Time**

### **1. Access the Monitoring Dashboard**
```bash
# Open in your browser
http://localhost:5051
```

**What to Look For:**
- **System Resources:** CPU, memory, and disk usage
- **Celery Workers:** Number of active workers and their status
- **Storage Health:** Flex mount status and available space
- **API Health:** Cablecast API response times

### **2. Access the Admin UI**
```bash
# Open in your browser
http://localhost:8080
```

**What to Look For:**
- **Queue Status:** Number of jobs queued, started, finished, failed
- **Worker Status:** Active Celery workers and their health
- **City Configuration:** Flex mount assignments per city

### **3. Monitor Task Processing via Command Line**
```bash
# Check active Celery tasks
celery -A core.tasks inspect active

# Check reserved (queued) tasks
celery -A core.tasks inspect reserved

# Monitor logs in real-time
tail -f logs/archivist.log | grep -E "(VOD|process|task)"

# Check specific task status
celery -A core.tasks inspect stats
```

### **4. API Endpoints for Programmatic Monitoring**
```bash
# System health check
curl http://localhost:5051/api/health

# Admin status
curl http://localhost:8080/api/admin/status

# Celery statistics
curl http://localhost:5051/api/celery

# Flex mount status
curl http://localhost:5051/api/mounts
```

## 📈 **Real-Time Monitoring Features**

### **Dashboard Auto-Refresh**
- **Monitoring Dashboard:** Refreshes every 30 seconds automatically
- **Admin UI:** Manual refresh or API polling
- **Log Monitoring:** Real-time log streaming available

### **Key Metrics to Watch**
1. **Queue Depth:** Number of jobs waiting to be processed
2. **Worker Activity:** Active vs idle workers
3. **Processing Speed:** Jobs completed per minute
4. **Error Rate:** Failed jobs and error messages
5. **Storage Usage:** Available space on flex mounts

### **Alert Indicators**
- **Red Status:** Service down or critical error
- **Yellow Status:** Degraded performance or warnings
- **Green Status:** Healthy operation

## 🔧 **Troubleshooting via GUIs**

### **If VOD Processing Stops:**
1. Check **Monitoring Dashboard** for system resource issues
2. Check **Admin UI** for queue status and worker health
3. Look for error messages in the logs
4. Verify flex mount accessibility

### **If Caption Generation Fails:**
1. Check worker logs for `faster_whisper` errors
2. Verify video file accessibility
3. Check system resources (CPU/memory)
4. Monitor task queue for stuck jobs

### **If Flex Mounts Show Issues:**
1. Check mount permissions
2. Verify network connectivity to flex servers
3. Check available disk space
4. Review mount configuration

## 🎬 **VOD Processing Workflow Monitoring**

### **Processing Pipeline Steps:**
1. **Discovery:** Finding videos on flex servers
2. **Download:** Retrieving video files (if needed)
3. **Caption Generation:** Creating SCC captions with faster_whisper
4. **Retranscoding:** Embedding captions in video
5. **Upload:** Saving processed videos
6. **Cleanup:** Removing temporary files

### **Monitoring Each Step:**
- **Discovery:** Check logs for "Found X videos" messages
- **Download:** Monitor file transfer progress
- **Caption Generation:** Watch for transcription progress
- **Retranscoding:** Monitor FFmpeg process activity
- **Upload:** Check file save operations
- **Cleanup:** Verify temporary file removal

## 📱 **Mobile-Friendly Monitoring**

Both GUIs are responsive and work on mobile devices:
- **Monitoring Dashboard:** Optimized for mobile viewing
- **Admin UI:** Touch-friendly interface
- **Real-time updates:** Works on mobile browsers

## 🔄 **Scheduled Tasks Monitoring**

### **Daily Scheduled Tasks:**
- **03:00 UTC:** Daily caption check for latest VODs
- **04:00 UTC:** Daily VOD processing for recent content
- **19:00 Local:** Evening VOD processing (5 most recent videos per city)
- **02:30 UTC:** VOD cleanup and maintenance

### **Monitoring Scheduled Tasks:**
- Check Celery beat scheduler status
- Monitor task execution logs
- Verify scheduled task completion

## 🎉 **Success Indicators**

### **Healthy VOD Processing:**
- ✅ Queue depth decreasing over time
- ✅ Workers actively processing tasks
- ✅ Caption generation completing successfully
- ✅ Processed videos appearing in output directories
- ✅ No failed jobs in queue
- ✅ System resources within normal ranges

### **System Optimization:**
- ✅ CPU usage < 80%
- ✅ Memory usage < 70%
- ✅ Disk usage < 90%
- ✅ Network connectivity stable
- ✅ All critical services running

---

**Last Updated:** 2025-07-17 15:46 UTC  
**Status:** ✅ Caption generation fixed, system processing videos  
**Next Check:** Monitor task queue for processing completion 