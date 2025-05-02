from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import os
import glob
from loguru import logger
from core.config import NAS_PATH, OUTPUT_DIR
from core.transcription import run_whisperx
from core.scc_summarizer import summarize_srt
from core.queue import queue_manager
import json
import time

app = Flask(__name__)

def get_flex_mounts():
    """Get all available flex mount points"""
    mounts = []
    # Check both flex and flex- patterns
    for pattern in ['/mnt/flex/*', '/mnt/flex-*']:
        mounts.extend(glob.glob(pattern))
    return sorted(mounts)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/browse')
def browse():
    path = request.args.get('path', '')
    try:
        # Start from NAS_PATH if no path provided
        current_path = path if path else ''
        full_path = os.path.join('/mnt', current_path) if current_path else NAS_PATH
        
        if not os.path.exists(full_path):
            return jsonify({'error': 'Path not found'}), 404
            
        items = []
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            rel_path = os.path.relpath(item_path, '/mnt')
            
            if os.path.isdir(item_path):
                items.append({
                    'name': item,
                    'type': 'directory',
                    'path': rel_path,
                    'mount': item.startswith('flex')
                })
            else:
                # Only include video files
                if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.mpeg', '.mpg')):
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': rel_path,
                        'size': f"{os.path.getsize(item_path) / (1024*1024):.1f} MB"
                    })
                    
        return jsonify(sorted(items, key=lambda x: (x['type'] != 'directory', x['name'].lower())))
    except Exception as e:
        logger.error(f"Error browsing directory: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """API endpoint for starting transcription"""
    data = request.json
    video_path = os.path.join('/mnt', data['path'])
    position = data.get('position')  # Optional position in queue
    
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found'}), 404
    
    try:
        # Enqueue the processing task
        job_id = queue_manager.enqueue_transcription(video_path, position)
        return jsonify({
            'status': 'success',
            'job_id': job_id
        })
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue')
def get_queue():
    """Get all jobs in the queue"""
    try:
        jobs = queue_manager.get_all_jobs()
        return jsonify(jobs)
    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/reorder', methods=['POST'])
def reorder_queue():
    """Reorder a job in the queue"""
    data = request.json
    job_id = data.get('job_id')
    new_position = data.get('position')
    
    if not job_id or new_position is None:
        return jsonify({'error': 'Missing job_id or position'}), 400
        
    success = queue_manager.reorder_job(job_id, new_position)
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed to reorder job'}), 500

@app.route('/api/queue/stop/<job_id>', methods=['POST'])
def stop_job(job_id):
    """Stop a running job"""
    success = queue_manager.stop_job(job_id)
    if success:
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed to stop job'}), 500

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get the status of a processing job"""
    return jsonify(queue_manager.get_job_status(job_id))

@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    """API endpoint for downloading files"""
    # Security check - prevent directory traversal
    if '..' in filepath or filepath.startswith('/'):
        return jsonify({'error': 'Invalid path'}), 400
        
    full_path = os.path.join('/mnt', filepath)
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    return send_file(full_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 