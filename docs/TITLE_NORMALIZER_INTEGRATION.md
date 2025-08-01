# Title Normalizer - Integration Guide

## Overview

This guide shows how to integrate the Title Normalizer CLI Tool into your existing Archivist monitoring dashboard and automation systems for seamless production operation.

## 🔗 Dashboard Integration

### 1. **Add to Monitoring Dashboard**

#### Integration with `core/monitoring/integrated_dashboard.py`

Add the following route to your existing dashboard:

```python
# Add to core/monitoring/integrated_dashboard.py

@self.app.route('/api/title-normalizer/status')
def api_title_normalizer_status():
    """Get title normalization status and recent operations."""
    try:
        # Get recent normalization operations from database or logs
        recent_operations = get_recent_title_normalizations()
        
        return jsonify({
            'success': True,
            'data': {
                'last_operation': recent_operations.get('last_operation'),
                'total_processed': recent_operations.get('total_processed', 0),
                'total_updated': recent_operations.get('total_updated', 0),
                'recent_errors': recent_operations.get('recent_errors', []),
                'status': 'ready'
            }
        })
    except Exception as e:
        logger.error(f"Error getting title normalizer status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@self.app.route('/api/title-normalizer/locations')
def api_title_normalizer_locations():
    """Get available Cablecast locations for title normalization."""
    try:
        from core.chronologic_order import ProductionCablecastTitleManager
        
        manager = ProductionCablecastTitleManager()
        locations = manager.get_locations()
        
        return jsonify({
            'success': True,
            'data': {
                'locations': locations,
                'count': len(locations)
            }
        })
    except Exception as e:
        logger.error(f"Error getting locations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@self.app.route('/api/title-normalizer/trigger', methods=['POST'])
def api_title_normalizer_trigger():
    """Trigger title normalization operation."""
    try:
        data = request.get_json()
        location_id = data.get('location_id')
        project_id = data.get('project_id')
        dry_run = data.get('dry_run', True)  # Default to dry run for safety
        
        if not location_id and not project_id:
            return jsonify({
                'success': False,
                'error': 'Must specify location_id or project_id'
            }), 400
        
        # Start normalization in background
        task_id = start_title_normalization_task(location_id, project_id, dry_run)
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task_id,
                'status': 'started',
                'dry_run': dry_run
            }
        })
    except Exception as e:
        logger.error(f"Error triggering title normalization: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

### 2. **Add Dashboard UI Components**

#### Add to Dashboard HTML Template

```html
<!-- Add to core/monitoring/integrated_dashboard.py _render_dashboard method -->

<!-- Title Normalizer Section -->
<div class="dashboard-section">
    <h3>Title Normalizer</h3>
    <div class="status-card">
        <div class="status-item">
            <span class="label">Status:</span>
            <span class="value" id="title-normalizer-status">Ready</span>
        </div>
        <div class="status-item">
            <span class="label">Last Operation:</span>
            <span class="value" id="title-normalizer-last-op">None</span>
        </div>
        <div class="status-item">
            <span class="label">Total Processed:</span>
            <span class="value" id="title-normalizer-total">0</span>
        </div>
    </div>
    
    <div class="action-buttons">
        <button onclick="listLocations()" class="btn btn-secondary">List Channels</button>
        <button onclick="showNormalizationDialog()" class="btn btn-primary">Start Normalization</button>
    </div>
</div>

<!-- Normalization Dialog -->
<div id="normalization-dialog" class="modal" style="display: none;">
    <div class="modal-content">
        <h3>Title Normalization</h3>
        <form id="normalization-form">
            <div class="form-group">
                <label for="location-select">Channel:</label>
                <select id="location-select" required>
                    <option value="">Select a channel...</option>
                </select>
            </div>
            <div class="form-group">
                <label for="project-select">Project (Optional):</label>
                <select id="project-select">
                    <option value="">All projects</option>
                </select>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" id="dry-run" checked>
                    Dry Run (Preview only)
                </label>
            </div>
            <div class="form-actions">
                <button type="button" onclick="closeNormalizationDialog()" class="btn btn-secondary">Cancel</button>
                <button type="submit" class="btn btn-primary">Start</button>
            </div>
        </form>
    </div>
</div>
```

#### Add JavaScript Functions

```javascript
// Add to core/monitoring/integrated_dashboard.py _render_dashboard_js method

// Title Normalizer Functions
function updateTitleNormalizerStatus() {
    fetch('/api/title-normalizer/status')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('title-normalizer-status').textContent = data.data.status;
                document.getElementById('title-normalizer-last-op').textContent = 
                    data.data.last_operation || 'None';
                document.getElementById('title-normalizer-total').textContent = 
                    data.data.total_processed;
            }
        })
        .catch(error => console.error('Error updating title normalizer status:', error));
}

function listLocations() {
    fetch('/api/title-normalizer/locations')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('location-select');
                select.innerHTML = '<option value="">Select a channel...</option>';
                
                data.data.locations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location.id;
                    option.textContent = `${location.name} (ID: ${location.id})`;
                    select.appendChild(option);
                });
                
                showNormalizationDialog();
            }
        })
        .catch(error => console.error('Error listing locations:', error));
}

function showNormalizationDialog() {
    document.getElementById('normalization-dialog').style.display = 'block';
}

function closeNormalizationDialog() {
    document.getElementById('normalization-dialog').style.display = 'none';
}

function startNormalization(locationId, projectId, dryRun) {
    const payload = {
        location_id: locationId,
        project_id: projectId || null,
        dry_run: dryRun
    };
    
    fetch('/api/title-normalizer/trigger', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Title normalization started', 'success');
            closeNormalizationDialog();
            // Start polling for status updates
            pollNormalizationStatus(data.data.task_id);
        } else {
            showNotification('Failed to start normalization: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error starting normalization:', error);
        showNotification('Error starting normalization', 'error');
    });
}

// Add form submission handler
document.getElementById('normalization-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const locationId = document.getElementById('location-select').value;
    const projectId = document.getElementById('project-select').value;
    const dryRun = document.getElementById('dry-run').checked;
    
    if (!locationId) {
        showNotification('Please select a channel', 'error');
        return;
    }
    
    startNormalization(locationId, projectId, dryRun);
});

// Update status every 30 seconds
setInterval(updateTitleNormalizerStatus, 30000);
```

## 🔄 Celery Task Integration

### 1. **Add Celery Task**

Create a new task in `core/tasks/title_normalization.py`:

```python
# core/tasks/title_normalization.py

from celery import shared_task
from loguru import logger
from core.chronologic_order import ProductionCablecastTitleManager
from core.monitoring.metrics import get_metrics_collector

@shared_task(name="title_normalization.process_channel")
def process_channel_title_normalization(location_id: int, project_id: int = None, dry_run: bool = True):
    """
    Celery task for processing title normalization on a channel.
    
    Args:
        location_id: Cablecast location ID
        project_id: Optional project ID to filter
        dry_run: If True, only preview changes
    """
    try:
        logger.info(f"Starting title normalization for location {location_id}, project {project_id}, dry_run: {dry_run}")
        
        # Initialize manager
        manager = ProductionCablecastTitleManager()
        manager.rate_limit_delay = 1.0  # Conservative rate limiting for background tasks
        manager.batch_size = 25  # Smaller batches for background processing
        
        # Get shows
        shows = manager.get_all_shows(location_id=location_id, project_id=project_id)
        
        if not shows:
            logger.warning(f"No shows found for location {location_id}")
            return {
                'success': True,
                'message': 'No shows found',
                'total_shows': 0,
                'processed': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0
            }
        
        # Process shows
        results = manager.process_shows(shows, dry_run=dry_run)
        
        # Update metrics
        metrics = get_metrics_collector()
        metrics.increment('title_normalization_shows_processed', results['processed'])
        metrics.increment('title_normalization_shows_updated', results['updated'])
        metrics.increment('title_normalization_shows_skipped', results['skipped'])
        metrics.increment('title_normalization_errors', results['errors'])
        
        logger.info(f"Title normalization completed: {results}")
        
        return {
            'success': True,
            'message': 'Title normalization completed',
            'total_shows': results['total_shows'],
            'processed': results['processed'],
            'updated': results['updated'],
            'skipped': results['skipped'],
            'errors': results['errors'],
            'duration': results['duration']
        }
        
    except Exception as e:
        logger.error(f"Title normalization failed: {e}")
        
        # Update error metrics
        metrics = get_metrics_collector()
        metrics.increment('title_normalization_failures')
        
        return {
            'success': False,
            'error': str(e)
        }
```

### 2. **Add Task Management Functions**

```python
# Add to core/monitoring/integrated_dashboard.py

def start_title_normalization_task(location_id: int, project_id: int = None, dry_run: bool = True):
    """Start title normalization as a background task."""
    from core.tasks.title_normalization import process_channel_title_normalization
    
    task = process_channel_title_normalization.delay(location_id, project_id, dry_run)
    return task.id

def get_title_normalization_task_status(task_id: str):
    """Get status of title normalization task."""
    from core.tasks.title_normalization import process_channel_title_normalization
    
    task = process_channel_title_normalization.AsyncResult(task_id)
    
    if task.ready():
        if task.successful():
            return {
                'status': 'completed',
                'result': task.result
            }
        else:
            return {
                'status': 'failed',
                'error': str(task.info)
            }
    else:
        return {
            'status': 'running',
            'progress': task.info.get('progress', 0) if task.info else 0
        }
```

## 📊 Metrics Integration

### 1. **Add Metrics Collection**

```python
# Add to core/monitoring/metrics.py

def track_title_normalization_metrics(results: dict):
    """Track title normalization metrics."""
    metrics = get_metrics_collector()
    
    # Increment counters
    metrics.increment('title_normalization_shows_processed', results.get('processed', 0))
    metrics.increment('title_normalization_shows_updated', results.get('updated', 0))
    metrics.increment('title_normalization_shows_skipped', results.get('skipped', 0))
    metrics.increment('title_normalization_errors', results.get('errors', 0))
    
    # Record timing
    if results.get('duration'):
        metrics.timer('title_normalization_duration', results['duration'])
    
    # Update gauges
    metrics.gauge('title_normalization_last_run_timestamp', time.time())
    metrics.gauge('title_normalization_total_processed', results.get('total_shows', 0))
```

### 2. **Add to Health Checks**

```python
# Add to core/monitoring/health_checks.py

def check_title_normalizer_health() -> HealthCheckResult:
    """Check title normalizer health."""
    try:
        from core.chronologic_order import ProductionCablecastTitleManager
        
        manager = ProductionCablecastTitleManager()
        if manager.test_connection():
            return HealthCheckResult(
                component="title_normalizer",
                status="healthy",
                message="Title normalizer is operational",
                details={"connection": "successful"}
            )
        else:
            return HealthCheckResult(
                component="title_normalizer",
                status="unhealthy",
                message="Title normalizer connection failed",
                details={"connection": "failed"}
            )
    except Exception as e:
        return HealthCheckResult(
            component="title_normalizer",
            status="unhealthy",
            message=f"Title normalizer error: {e}",
            details={"error": str(e)}
        )
```

## 🔔 Alert Integration

### 1. **Add Alert Functions**

```python
# Add to core/utils/alerts.py

def send_title_normalization_alert(level: str, message: str, details: dict = None):
    """Send alert for title normalization events."""
    alert_data = {
        'level': level,
        'message': message,
        'component': 'title_normalizer',
        'timestamp': datetime.utcnow().isoformat(),
        'details': details or {}
    }
    
    send_alert(level, f"[Title Normalizer] {message}", **alert_data)

# Usage examples:
# send_title_normalization_alert('info', 'Title normalization started', {'location_id': 123})
# send_title_normalization_alert('success', 'Title normalization completed', results)
# send_title_normalization_alert('error', 'Title normalization failed', {'error': str(e)})
```

## 🚀 Automation Integration

### 1. **Scheduled Operations**

Add to your cron jobs or Celery beat schedule:

```python
# Add to celery configuration

# Weekly title normalization check
CELERY_BEAT_SCHEDULE = {
    'weekly-title-normalization-check': {
        'task': 'title_normalization.process_channel',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
        'args': (123, None, True),  # location_id, project_id, dry_run
        'options': {'queue': 'title_normalization'}
    }
}
```

### 2. **API Endpoint for Automation**

```python
# Add to web/api/cablecast.py

@bp.route('/title-normalizer/schedule', methods=['POST'])
@limiter.limit('10 per hour')
def schedule_title_normalization():
    """Schedule title normalization operation."""
    try:
        data = request.get_json()
        location_id = data.get('location_id')
        project_id = data.get('project_id')
        dry_run = data.get('dry_run', True)
        schedule_time = data.get('schedule_time')  # ISO format
        
        if not location_id:
            return jsonify({
                'success': False,
                'error': 'location_id is required'
            }), 400
        
        # Schedule the task
        from core.tasks.title_normalization import process_channel_title_normalization
        
        if schedule_time:
            # Schedule for specific time
            eta = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            task = process_channel_title_normalization.apply_async(
                args=[location_id, project_id, dry_run],
                eta=eta
            )
        else:
            # Run immediately
            task = process_channel_title_normalization.delay(location_id, project_id, dry_run)
        
        return jsonify({
            'success': True,
            'data': {
                'task_id': task.id,
                'scheduled': bool(schedule_time),
                'schedule_time': schedule_time
            }
        })
        
    except Exception as e:
        logger.error(f"Error scheduling title normalization: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

## 📋 Integration Checklist

### **Dashboard Integration**
- [ ] Add API endpoints for status and operations
- [ ] Add UI components to dashboard
- [ ] Add JavaScript functions for interaction
- [ ] Test dashboard integration

### **Task Integration**
- [ ] Create Celery task for background processing
- [ ] Add task management functions
- [ ] Test task execution and monitoring
- [ ] Add task status tracking

### **Metrics Integration**
- [ ] Add metrics collection functions
- [ ] Integrate with existing metrics system
- [ ] Add health check for title normalizer
- [ ] Test metrics collection

### **Alert Integration**
- [ ] Add alert functions for title normalization
- [ ] Integrate with existing alert system
- [ ] Test alert notifications
- [ ] Configure alert thresholds

### **Automation Integration**
- [ ] Add scheduled operations
- [ ] Create API endpoints for automation
- [ ] Test automation workflows
- [ ] Document automation procedures

## 🎯 Complete Integration

Once all integration steps are completed, the Title Normalizer will be fully integrated into your Archivist system with:

- ✅ **Dashboard Monitoring**: Real-time status and control
- ✅ **Background Processing**: Celery task integration
- ✅ **Metrics Collection**: Performance and usage tracking
- ✅ **Alert System**: Notifications for events
- ✅ **Automation**: Scheduled and API-triggered operations
- ✅ **Health Monitoring**: System health checks

The tool will be production-ready and fully integrated with your existing monitoring and automation infrastructure. 