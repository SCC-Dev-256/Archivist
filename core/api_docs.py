from flask_restx import Api, Resource, fields, Namespace
from core.models import (
    BrowseRequest, TranscribeRequest, QueueReorderRequest,
    JobStatus, FileItem, ErrorResponse, SuccessResponse
)

# Create API instance
api = Api(
    title='Archivist API',
    version='1.0',
    description='Video transcription and processing API',
    doc='/api/docs'
)

# Create namespace
ns = api.namespace('', description='Video transcription and processing API')

# Define models for documentation
browse_request = ns.model('BrowseRequest', {
    'path': fields.String(description='Path to browse, relative to NAS_PATH', default='')
})

transcribe_request = ns.model('TranscribeRequest', {
    'path': fields.String(required=True, description='Path to video file, relative to /mnt'),
    'position': fields.Integer(description='Optional position in queue')
})

queue_reorder_request = ns.model('QueueReorderRequest', {
    'job_id': fields.String(required=True, description='ID of the job to reorder'),
    'position': fields.Integer(required=True, description='New position in queue (0-based)')
})

job_status = ns.model('JobStatus', {
    'id': fields.String(description='Job ID'),
    'video_path': fields.String(description='Path to video file'),
    'status': fields.String(description='Job status', enum=['queued', 'processing', 'paused', 'completed', 'failed']),
    'progress': fields.Float(description='Progress percentage', min=0, max=100),
    'status_message': fields.String(description='Status message'),
    'error_details': fields.Raw(description='Error details if any'),
    'start_time': fields.Float(description='Job start time'),
    'time_remaining': fields.Float(description='Estimated time remaining'),
    'transcribed_duration': fields.Float(description='Duration transcribed so far'),
    'total_duration': fields.Float(description='Total video duration')
})

file_item = ns.model('FileItem', {
    'name': fields.String(description='File or directory name'),
    'type': fields.String(description='Item type', enum=['directory', 'file']),
    'path': fields.String(description='Relative path'),
    'size': fields.String(description='File size in MB'),
    'mount': fields.Boolean(description='Whether this is a mount point')
})

error_response = ns.model('ErrorResponse', {
    'error': fields.String(description='Error message'),
    'details': fields.Raw(description='Additional error details')
})

success_response = ns.model('SuccessResponse', {
    'status': fields.String(description='Status', enum=['success']),
    'job_id': fields.String(description='Job ID if applicable')
})

# API documentation
@ns.route('/browse')
class Browse(Resource):
    @ns.doc('browse_directory',
             params={'path': 'Path to browse, relative to NAS_PATH'},
             responses={
                 200: ('Success', [file_item]),
                 400: ('Validation Error', error_response),
                 404: ('Path Not Found', error_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def get(self):
        """Browse directory contents"""
        pass

@ns.route('/transcribe')
class Transcribe(Resource):
    @ns.doc('start_transcription',
             body=transcribe_request,
             responses={
                 200: ('Success', success_response),
                 400: ('Validation Error', error_response),
                 404: ('Video Not Found', error_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def post(self):
        """Start video transcription"""
        pass

@ns.route('/queue')
class Queue(Resource):
    @ns.doc('get_queue',
             responses={
                 200: ('Success', [job_status]),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def get(self):
        """Get all jobs in the queue"""
        pass

@ns.route('/queue/reorder')
class QueueReorder(Resource):
    @ns.doc('reorder_queue',
             body=queue_reorder_request,
             responses={
                 200: ('Success', success_response),
                 400: ('Validation Error', error_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def post(self):
        """Reorder a job in the queue"""
        pass

@ns.route('/queue/stop/<job_id>')
class QueueStop(Resource):
    @ns.doc('stop_job',
             params={'job_id': 'Job ID to stop'},
             responses={
                 200: ('Success', success_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def post(self, job_id):
        """Stop a running job"""
        pass

@ns.route('/queue/pause/<job_id>')
class QueuePause(Resource):
    @ns.doc('pause_job',
             params={'job_id': 'Job ID to pause'},
             responses={
                 200: ('Success', success_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def post(self, job_id):
        """Pause a running job"""
        pass

@ns.route('/queue/resume/<job_id>')
class QueueResume(Resource):
    @ns.doc('resume_job',
             params={'job_id': 'Job ID to resume'},
             responses={
                 200: ('Success', success_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def post(self, job_id):
        """Resume a paused job"""
        pass

@ns.route('/status/<job_id>')
class Status(Resource):
    @ns.doc('get_status',
             params={'job_id': 'Job ID to check'},
             responses={
                 200: ('Success', job_status),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def get(self, job_id):
        """Get job status"""
        pass

@ns.route('/download/<path:filepath>')
class Download(Resource):
    @ns.doc('download_file',
             params={'filepath': 'Path to file to download'},
             responses={
                 200: 'File download',
                 400: ('Invalid Path', error_response),
                 404: ('File Not Found', error_response),
                 429: ('Rate Limit Exceeded', error_response),
                 500: ('Server Error', error_response)
             })
    def get(self, filepath):
        """Download a file"""
        pass 