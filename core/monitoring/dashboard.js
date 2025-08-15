let currentTab = 'overview';

function showTab(tabName) {
    // Hide all tab panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    // Remove active class from all tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    // Show selected tab pane
    document.getElementById(tabName).classList.add('active');
    // Add active class to selected tab
    event.target.classList.add('active');
    currentTab = tabName;
    // Refresh data for the selected tab
    refreshTabData(tabName);
}

function refreshAllData() {
    refreshTabData(currentTab);
}

function refreshTabData(tabName) {
    switch(tabName) {
        case 'overview':
            refreshOverviewData();
            break;
        case 'realtime':
            refreshRealtimeData();
            break;
        case 'queue':
            refreshQueueData();
            break;
        case 'celery':
            refreshCeleryData();
            break;
        case 'health':
            refreshHealthData();
            break;
        case 'metrics':
            refreshMetricsData();
            break;
    }
}

// SocketIO connection and real-time task monitoring
let socket = null;
let currentTaskFilter = 'all';

function initializeSocketIO() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to SocketIO server');
        updateSocketStatus(true);
        socket.emit('join_task_monitoring');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from SocketIO server');
        updateSocketStatus(false);
    });
    
    socket.on('task_updates', function(data) {
        updateRealtimeTasks(data);
    });
    
    socket.on('filtered_tasks', function(data) {
        updateRealtimeTasks(data);
    });
    
    socket.on('system_metrics', function(data) {
        updateSystemHealth(data);
    });
    
    socket.on('error', function(data) {
        console.error('SocketIO error:', data);
    });
}

function updateSocketStatus(connected) {
    const statusIndicator = document.getElementById('socket-status');
    const statusText = document.getElementById('socket-text');
    
    if (connected) {
        statusIndicator.className = 'status-indicator status-healthy';
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.className = 'status-indicator status-unhealthy';
        statusText.textContent = 'Disconnected';
    }
}

function refreshRealtimeData() {
    // Load initial real-time data
    fetch('/api/tasks/realtime')
        .then(response => response.json())
        .then(data => {
            updateRealtimeTasks(data);
        });
    
    // Load task analytics
    fetch('/api/tasks/analytics')
        .then(response => response.json())
        .then(data => {
            updateTaskAnalytics(data);
        });
}

function updateRealtimeTasks(data) {
    if (data.error) {
        document.getElementById('realtime-tasks-list').innerHTML = 
            `<div style="color: red; padding: 20px;">Error: ${data.error}</div>`;
        return;
    }
    
    // Update summary values
    const summary = data.summary || {};
    document.getElementById('total-tasks').textContent = summary.total || 0;
    document.getElementById('active-tasks').textContent = summary.active || 0;
    document.getElementById('reserved-tasks').textContent = summary.reserved || 0;
    document.getElementById('queued-tasks').textContent = summary.queued || 0;
    
    // Update task list
    const tasks = data.tasks || [];
    const tasksContainer = document.getElementById('realtime-tasks-list');
    
    if (tasks.length === 0) {
        tasksContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No tasks found</div>';
        return;
    }
    
    let html = '';
    tasks.forEach(task => {
        const statusClass = `status-${task.status}`;
        const progressPercent = task.progress || 0;
        const duration = task.duration ? Math.round(task.duration) : 0;
        
        html += `
            <div class="task-item">
                <div class="task-info">
                    <div class="task-name">${task.name}</div>
                    <div class="task-details">
                        ID: ${task.id} | Type: ${task.type} | Worker: ${task.worker || 'N/A'} | Duration: ${duration}s
                        ${task.video_path ? '| File: ' + task.video_path : ''}
                    </div>
                </div>
                <div class="task-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <div style="text-align: center; font-size: 0.8em; margin-top: 2px;">${progressPercent}%</div>
                </div>
                <span class="task-status ${statusClass}">${task.status}</span>
            </div>
        `;
    });
    
    tasksContainer.innerHTML = html;
}

function updateTaskAnalytics(data) {
    if (data.error) {
        document.getElementById('task-analytics-data').innerHTML = 
            `<div style="color: red;">Error: ${data.error}</div>`;
        return;
    }
    
    const analyticsContainer = document.getElementById('task-analytics-data');
    let html = '<div class="analytics-grid">';
    
    html += `
        <div class="analytics-card">
            <div class="analytics-value">${data.average_completion_time || 0}s</div>
            <div>Average Completion Time</div>
        </div>
        <div class="analytics-card">
            <div class="analytics-value">${data.success_rate || 0}%</div>
            <div>Success Rate</div>
        </div>
        <div class="analytics-card">
            <div class="analytics-value">${data.total_tasks || 0}</div>
            <div>Total Tasks</div>
        </div>
        <div class="analytics-card">
            <div class="analytics-value">${data.completed_tasks || 0}</div>
            <div>Completed Tasks</div>
        </div>
        <div class="analytics-card">
            <div class="analytics-value">${data.recent_performance?.last_24h || 0}</div>
            <div>Tasks (24h)</div>
        </div>
        <div class="analytics-card">
            <div class="analytics-value">${data.recent_performance?.successful_24h || 0}</div>
            <div>Successful (24h)</div>
        </div>
    `;
    
    html += '</div>';
    
    // Add task type distribution
    if (data.task_types && Object.keys(data.task_types).length > 0) {
        html += '<h4 style="margin-top: 20px;">Task Type Distribution</h4><div class="analytics-grid">';
        Object.entries(data.task_types).forEach(([type, count]) => {
            html += `
                <div class="analytics-card">
                    <div class="analytics-value">${count}</div>
                    <div>${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    analyticsContainer.innerHTML = html;
}

function filterTasks(taskType) {
    currentTaskFilter = taskType;
    
    // Update filter button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Request filtered data from server
    if (socket && socket.connected) {
        socket.emit('filter_tasks', { type: taskType });
    } else {
        // Fallback to HTTP request
        fetch(`/api/tasks/realtime?filter=${taskType}`)
            .then(response => response.json())
            .then(data => {
                updateRealtimeTasks(data);
            });
    }
}

function refreshOverviewData() {
    // Load system health
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateSystemHealth(data);
        });
    
    // Load queue overview
    fetch('/api/queue/jobs')
        .then(response => response.json())
        .then(data => {
            updateQueueOverview(data);
        });
    
    // Load Celery overview
    fetch('/api/celery/workers')
        .then(response => response.json())
        .then(data => {
            updateCeleryOverview(data);
        });
    
    // Load recent activity
    fetch('/api/unified/tasks')
        .then(response => response.json())
        .then(data => {
            updateRecentActivity(data);
        });
}

function refreshQueueData() {
    fetch('/api/queue/jobs')
        .then(response => response.json())
        .then(data => {
            updateQueueJobs(data);
        });
}

function refreshCeleryData() {
    fetch('/api/celery/tasks')
        .then(response => response.json())
        .then(data => {
            updateCeleryTasks(data);
        });
}

function refreshHealthData() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            updateHealthChecks(data);
        });
}

function refreshMetricsData() {
    fetch('/api/metrics')
        .then(response => response.json())
        .then(data => {
            updatePerformanceMetrics(data);
        });
}

function updateSystemHealth(data) {
    const div = document.getElementById('system-health');
    const overallStatus = data.system?.overall_status || 'unknown';
    const statusClass = overallStatus === 'healthy' ? 'healthy' : 
                      overallStatus === 'degraded' ? 'degraded' : 'unhealthy';
    
    div.innerHTML = `
        <div><span class="status-indicator status-${statusClass}"></span>Overall: ${overallStatus.toUpperCase()}</div>
        <div>CPU: ${data.system?.cpu_percent || 0}%</div>
        <div>Memory: ${data.system?.memory_percent || 0}%</div>
        <div>Disk: ${data.system?.disk_percent || 0}%</div>
        <div>Redis: ${data.redis?.status || 'Disconnected'}</div>
        <div>Celery Workers: ${data.celery?.active_workers?.length || 0} active</div>
    `;
}

function updateQueueOverview(data) {
    const div = document.getElementById('queue-overview');
    const summary = data.summary || {};
    
    div.innerHTML = `
        <div class="metric-value">${data.total || 0}</div>
        <div class="metric-label">Total Jobs</div>
        <div>Queued: ${summary.queued || 0}</div>
        <div>Started: ${summary.started || 0}</div>
        <div>Finished: ${summary.finished || 0}</div>
        <div>Failed: ${summary.failed || 0}</div>
    `;
}

function updateCeleryOverview(data) {
    const div = document.getElementById('celery-overview');
    const summary = data.summary || {};
    
    div.innerHTML = `
        <div class="metric-value">${summary.active_workers || 0}</div>
        <div class="metric-label">Active Workers</div>
        <div>Total Workers: ${summary.total_workers || 0}</div>
        <div>Status: ${summary.worker_status || 'unknown'}</div>
    `;
}

function updateRecentActivity(data) {
    const div = document.getElementById('recent-activity');
    const tasks = data.tasks || [];
    const summary = data.summary || {};
    
    let html = `
        <div class="metric-value">${summary.total || 0}</div>
        <div class="metric-label">Total Tasks</div>
        <div>RQ Jobs: ${summary.rq_count || 0}</div>
        <div>Celery Active: ${summary.celery_active || 0}</div>
        <div>Celery Reserved: ${summary.celery_reserved || 0}</div>
    `;
    
    if (tasks.length > 0) {
        html += '<div style="margin-top: 15px;"><strong>Recent Tasks:</strong></div>';
        tasks.slice(0, 5).forEach(task => {
            const statusClass = task.status === 'finished' ? 'healthy' : 
                              task.status === 'failed' ? 'unhealthy' : 'degraded';
            html += `
                <div style="margin: 5px 0; padding: 5px; border-bottom: 1px solid #eee;">
                    <div><strong>${task.name}</strong> (${task.type})</div>
                    <div>Status: <span class="status-indicator status-${statusClass}"></span>${task.status}</div>
                </div>
            `;
        });
    }
    
    div.innerHTML = html;
}

function updateQueueJobs(data) {
    const div = document.getElementById('queue-jobs');
    const jobs = data.jobs || [];
    
    if (jobs.length === 0) {
        div.innerHTML = '<p>No jobs in queue</p>';
        return;
    }
    
    let html = `
        <table class="task-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Video Path</th>
                    <th>Created</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    jobs.forEach(job => {
        const statusClass = job.status === 'finished' ? 'healthy' : 
                          job.status === 'failed' ? 'unhealthy' : 'degraded';
        const progress = job.progress || 0;
        
        html += `
            <tr>
                <td>${job.id}</td>
                <td><span class="status-indicator status-${statusClass}"></span>${job.status}</td>
                <td>${progress}%</td>
                <td>${job.video_path || 'N/A'}</td>
                <td>${new Date(job.created_at).toLocaleString()}</td>
                <td>
                    ${job.status === 'queued' ? '<button class="action-button" onclick="stopJob(\'' + job.id + '\')">Stop</button>' : ''}
                    ${job.status === 'started' ? '<button class="action-button warning" onclick="pauseJob(\'' + job.id + '\')">Pause</button>' : ''}
                    ${job.status === 'paused' ? '<button class="action-button" onclick="resumeJob(\'' + job.id + '\')">Resume</button>' : ''}
                    <button class="action-button danger" onclick="removeJob(\'' + job.id + '\')">Remove</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    div.innerHTML = html;
}

function updateCeleryTasks(data) {
    const div = document.getElementById('celery-tasks');
    const summary = data.summary || {};
    
    let html = `
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">${summary.total_tasks || 0}</div>
                <div class="metric-label">Total Tasks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${summary.active_tasks || 0}</div>
                <div class="metric-label">Active Tasks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${summary.reserved_tasks || 0}</div>
                <div class="metric-label">Reserved Tasks</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${summary.worker_count || 0}</div>
                <div class="metric-label">Workers</div>
            </div>
        </div>
    `;
    
    if (data.active) {
        html += '<h3>Active Tasks</h3>';
        Object.entries(data.active).forEach(([worker, tasks]) => {
            html += `<h4>Worker: ${worker}</h4>`;
            if (tasks.length > 0) {
                html += '<table class="task-table"><thead><tr><th>Task ID</th><th>Name</th><th>Started</th></tr></thead><tbody>';
                tasks.forEach(task => {
                    html += `
                        <tr>
                            <td>${task.id}</td>
                            <td>${task.name}</td>
                            <td>${new Date(task.time_start * 1000).toLocaleString()}</td>
                        </tr>
                    `;
                });
                html += '</tbody></table>';
            } else {
                html += '<p>No active tasks</p>';
            }
        });
    }
    
    div.innerHTML = html;
}

function updateHealthChecks(data) {
    const div = document.getElementById('health-checks');
    const checks = data.checks || {};
    
    let html = '';
    Object.entries(checks).forEach(([category, categoryChecks]) => {
        html += `<h3>${category.charAt(0).toUpperCase() + category.slice(1)} Health</h3>`;
        if (Array.isArray(categoryChecks)) {
            categoryChecks.forEach(check => {
                const statusClass = check.status === 'healthy' ? 'healthy' : 
                                  check.status === 'degraded' ? 'degraded' : 'unhealthy';
                html += `
                    <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                        <div><strong>${check.name}</strong> <span class="status-indicator status-${statusClass}"></span>${check.status}</div>
                        <div>${check.message || ''}</div>
                        ${check.details ? '<div><small>Details: ' + JSON.stringify(check.details) + '</small></div>' : ''}
                    </div>
                `;
            });
        }
    });
    
    div.innerHTML = html;
}

function updatePerformanceMetrics(data) {
    const div = document.getElementById('performance-metrics');
    
    let html = '<div class="metrics-grid">';
    Object.entries(data.counters || {}).forEach(([name, value]) => {
        html += `
            <div class="metric-card">
                <div class="metric-value">${value}</div>
                <div class="metric-label">${name}</div>
            </div>
        `;
    });
    html += '</div>';
    
    if (data.timers && Object.keys(data.timers).length > 0) {
        html += '<h3>Performance Timers</h3><div class="metrics-grid">';
        Object.entries(data.timers).forEach(([name, stats]) => {
            html += `
                <div class="metric-card">
                    <div class="metric-value">${stats.avg ? stats.avg.toFixed(2) : 0}ms</div>
                    <div class="metric-label">${name} (avg)</div>
                    <div>Min: ${stats.min || 0}ms</div>
                    <div>Max: ${stats.max || 0}ms</div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    div.innerHTML = html;
}

// Queue management functions
function stopJob(jobId) {
    fetch(`/api/queue/jobs/${jobId}/stop`, {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshQueueData();
            } else {
                alert('Failed to stop job');
            }
        });
}

function pauseJob(jobId) {
    fetch(`/api/queue/jobs/${jobId}/pause`, {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshQueueData();
            } else {
                alert('Failed to pause job');
            }
        });
}

function resumeJob(jobId) {
    fetch(`/api/queue/jobs/${jobId}/resume`, {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                refreshQueueData();
            } else {
                alert('Failed to resume job');
            }
        });
}

function removeJob(jobId) {
    if (confirm('Are you sure you want to remove this job?')) {
        fetch(`/api/queue/jobs/${jobId}/remove`, {method: 'DELETE'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    refreshQueueData();
                } else {
                    alert('Failed to remove job');
                }
            });
    }
}

function triggerVODProcessing() {
    fetch('/api/tasks/trigger_vod_processing', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            alert(data.message || (data.success ? 'Triggered!' : 'Failed: ' + data.error));
        });
}

function showTranscriptionDialog() {
    document.getElementById('transcription-dialog').style.display = 'block';
}

function closeTranscriptionDialog() {
    document.getElementById('transcription-dialog').style.display = 'none';
}

function triggerTranscription() {
    const filePath = document.getElementById('transcription-file-path').value;
    fetch('/api/tasks/trigger_transcription', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_path: filePath})
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || (data.success ? 'Triggered!' : 'Failed: ' + data.error));
        closeTranscriptionDialog();
    });
}

// Initial load
refreshOverviewData();

// Initialize SocketIO for real-time monitoring
initializeSocketIO();

// Auto-refresh every 30 seconds
setInterval(() => refreshTabData(currentTab), 30000); 