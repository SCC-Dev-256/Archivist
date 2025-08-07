# PURPOSE: Digital file upload API endpoints for Flex server integration
# DEPENDENCIES: flask, flask_restx, pathlib, os
# MODIFICATION NOTES: v1.0 - Initial implementation for PDF upload integration

from flask import Blueprint, jsonify, request, current_app
from flask_restx import Namespace, Resource, fields
from flask_limiter import Limiter
from loguru import logger
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename

from core.security import require_csrf_token
from core.database import db
from core.models import DigitalFileORM, DigitalFileLinkORM

def create_digitalfiles_blueprint(limiter):
    """Create digital files blueprint with routes."""
    bp = Blueprint('digitalfiles', __name__)
    
    # Create namespace for API documentation
    ns = Namespace('digitalfiles', description='Digital file management operations')
    
    # Swagger model definitions
    digital_file_model = ns.model('DigitalFile', {
        'id': fields.String(description='File ID'),
        'filename': fields.String(description='Original filename'),
        'path': fields.String(description='Storage path'),
        'size': fields.Integer(description='File size in bytes'),
        'mime_type': fields.String(description='MIME type'),
        'metadata': fields.Raw(description='File metadata'),
        'created_at': fields.DateTime(description='Creation timestamp'),
        'city': fields.String(description='Associated city'),
        'document_type': fields.String(description='Document type'),
        'flex_server': fields.String(description='Target Flex server')
    })

    @bp.route('/upload', methods=['POST'])
    @limiter.limit('50 per hour')
    @require_csrf_token
    def upload_digital_file():
        """Upload a digital file to the appropriate Flex server."""
        try:
            # Check if file was uploaded
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No file provided'
                }), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            # Get metadata
            metadata_str = request.form.get('metadata', '{}')
            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                metadata = {}
            
            # Extract key metadata
            city = metadata.get('city', 'Unknown')
            document_type = metadata.get('document_type', 'City Document')
            flex_server = metadata.get('flex_server', 'flex-1')
            source_url = metadata.get('source_url', '')
            
            # Validate file type
            allowed_extensions = {'.pdf', '.mp4', '.avi', '.mov', '.mkv', '.mp3', '.wav'}
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return jsonify({
                    'success': False,
                    'error': f'File type {file_ext} not allowed. Allowed: {", ".join(allowed_extensions)}'
                }), 400
            
            # Determine target Flex server path
            flex_mapping = {
                'flex-1': '/mnt/flex-1',  # Birchwood
                'flex-2': '/mnt/flex-2',  # Dellwood, Grant, Willernie
                'flex-3': '/mnt/flex-3',  # Lake Elmo
                'flex-4': '/mnt/flex-4',  # Mahtomedi
                # flex-5 and flex-6 are not allocated
                'flex-7': '/mnt/flex-7',  # Oakdale
                'flex-8': '/mnt/flex-8',  # White Bear Lake
                'flex-9': '/mnt/flex-9'   # White Bear Township
            }
            
            target_mount = flex_mapping.get(flex_server, '/mnt/flex-1')
            
            # Verify mount point exists and is accessible
            if not os.path.exists(target_mount):
                return jsonify({
                    'success': False,
                    'error': f'Flex server {flex_server} not accessible at {target_mount}'
                }), 500
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = secure_filename(file.filename)
            unique_filename = f"{timestamp}_{safe_filename}"
            
            # Create target directory structure
            target_dir = Path(target_mount) / 'city_documents' / city.lower().replace(' ', '_')
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            target_path = target_dir / unique_filename
            file.save(str(target_path))
            
            # Get file size
            file_size = target_path.stat().st_size
            
            # Create database record
            file_id = str(uuid.uuid4())
            digital_file = DigitalFileORM(
                id=file_id,
                filename=safe_filename,
                path=str(target_path),
                size=file_size,
                mime_type=file.content_type or 'application/octet-stream',
                metadata=metadata,
                created_at=datetime.utcnow(),
                city=city,
                document_type=document_type,
                flex_server=flex_server,
                source_url=source_url
            )
            
            db.session.add(digital_file)
            db.session.commit()
            
            logger.info(f"Uploaded file {safe_filename} for {city} to {flex_server}")
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'path': str(target_path),
                'filename': safe_filename,
                'size': file_size,
                'city': city,
                'document_type': document_type,
                'flex_server': flex_server,
                'message': f'File uploaded successfully to {flex_server}'
            })
            
        except Exception as e:
            logger.error(f"Error uploading digital file: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    @bp.route('/<string:file_id>', methods=['GET'])
    @limiter.limit('100 per hour')
    def get_digital_file(file_id):
        """Get information about a specific digital file."""
        try:
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            return jsonify({
                'success': True,
                'data': {
                    'id': digital_file.id,
                    'filename': digital_file.filename,
                    'path': digital_file.path,
                    'size': digital_file.size,
                    'mime_type': digital_file.mime_type,
                    'metadata': digital_file.metadata,
                    'created_at': digital_file.created_at.isoformat(),
                    'city': digital_file.city,
                    'document_type': digital_file.document_type,
                    'flex_server': digital_file.flex_server,
                    'source_url': digital_file.source_url
                }
            })
            
        except Exception as e:
            logger.error(f"Error retrieving digital file {file_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

    @bp.route('/<string:file_id>/link', methods=['GET'])
    @limiter.limit('100 per hour')
    def get_digital_file_link(file_id):
        """Get streaming URL for a digital file."""
        try:
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            # Check if file exists on disk
            if not os.path.exists(digital_file.path):
                return jsonify({
                    'success': False,
                    'error': 'File not found on disk'
                }), 404
            
            # Generate streaming URL
            streaming_url = f"/api/digitalfiles/{file_id}/stream"
            
            return jsonify({
                'success': True,
                'data': {
                    'file_id': file_id,
                    'streaming_url': streaming_url,
                    'filename': digital_file.filename,
                    'mime_type': digital_file.mime_type,
                    'size': digital_file.size
                }
            })
            
        except Exception as e:
            logger.error(f"Error generating link for file {file_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

    @bp.route('/<string:file_id>/stream', methods=['GET'])
    @limiter.limit('200 per hour')
    def stream_digital_file(file_id):
        """Stream a digital file."""
        try:
            from flask import send_file
            
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            # Check if file exists
            if not os.path.exists(digital_file.path):
                return jsonify({
                    'success': False,
                    'error': 'File not found on disk'
                }), 404
            
            # Stream the file
            return send_file(
                digital_file.path,
                as_attachment=False,
                download_name=digital_file.filename,
                mimetype=digital_file.mime_type
            )
            
        except Exception as e:
            logger.error(f"Error streaming file {file_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

    @bp.route('/<string:file_id>', methods=['DELETE'])
    @limiter.limit('10 per hour')
    @require_csrf_token
    def delete_digital_file(file_id):
        """Delete a digital file from disk and database."""
        try:
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            # Delete file from disk
            if os.path.exists(digital_file.path):
                os.remove(digital_file.path)
                logger.info(f"Deleted file from disk: {digital_file.path}")
            
            # Delete from database
            db.session.delete(digital_file)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'File {digital_file.filename} deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to delete file'
            }), 500

    @bp.route('/<string:file_id>/rename', methods=['POST'])
    @limiter.limit('20 per hour')
    @require_csrf_token
    def rename_digital_file(file_id):
        """Rename a digital file."""
        try:
            data = request.get_json()
            new_filename = data.get('new_filename')
            
            if not new_filename:
                return jsonify({
                    'success': False,
                    'error': 'new_filename is required'
                }), 400
            
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            # Generate new path
            old_path = Path(digital_file.path)
            new_path = old_path.parent / secure_filename(new_filename)
            
            # Rename file on disk
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                digital_file.path = str(new_path)
                digital_file.filename = secure_filename(new_filename)
                db.session.commit()
                
                logger.info(f"Renamed file {file_id} to {new_filename}")
                
                return jsonify({
                    'success': True,
                    'message': f'File renamed to {new_filename}',
                    'new_path': str(new_path)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'File not found on disk'
                }), 404
                
        except Exception as e:
            logger.error(f"Error renaming file {file_id}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to rename file'
            }), 500

    @bp.route('/<string:file_id>/reindex', methods=['POST'])
    @limiter.limit('20 per hour')
    @require_csrf_token
    def reindex_digital_file(file_id):
        """Add a digital file to the reindexing queue."""
        try:
            digital_file = DigitalFileORM.query.get_or_404(file_id)
            
            # Add to reindexing queue (placeholder for future implementation)
            # This could trigger OCR, transcription, or other indexing processes
            
            logger.info(f"Added file {file_id} to reindexing queue")
            
            return jsonify({
                'success': True,
                'message': f'File {digital_file.filename} added to reindexing queue',
                'file_id': file_id
            })
            
        except Exception as e:
            logger.error(f"Error adding file {file_id} to reindexing queue: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to add file to reindexing queue'
            }), 500

    @bp.route('/city/<string:city>', methods=['GET'])
    @limiter.limit('50 per hour')
    def get_city_files(city):
        """Get all files for a specific city."""
        try:
            files = DigitalFileORM.query.filter_by(city=city).order_by(DigitalFileORM.created_at.desc()).all()
            
            return jsonify({
                'success': True,
                'data': {
                    'city': city,
                    'files': [{
                        'id': f.id,
                        'filename': f.filename,
                        'document_type': f.document_type,
                        'size': f.size,
                        'created_at': f.created_at.isoformat(),
                        'flex_server': f.flex_server
                    } for f in files],
                    'total_files': len(files)
                }
            })
            
        except Exception as e:
            logger.error(f"Error retrieving files for city {city}: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve city files'
            }), 500

    return bp, ns 