#!/usr/bin/env python3
"""VOD Sync Monitor Script

This script periodically monitors VOD synchronization status and handles failures.
It uses the transcription log system to track processing status and provides
detailed reporting on VOD integration health.

Features:
- Periodic VOD status checks
- Failure detection and reporting
- Integration with transcription logs
- Configurable monitoring intervals
- Detailed health reporting

Usage:
    python3 scripts/vod_sync_monitor.py [--interval 300] [--log-level INFO]
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from loguru import logger
from core.services import VODService
from core import db

# Add the core directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

def setup_logging(log_level: str = "INFO"):
    """Setup logging for the monitor script"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logging
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'vod_sync_monitor.log')
    logger.add(
        log_file,
        level=log_level,
        rotation="1 day",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

class VODSyncMonitor:
    """Monitor VOD synchronization status and handle failures"""
    
    def __init__(self):
        self.vod_manager = None
        self.cablecast_client = None
        self.stats = {
            'total_checks': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_check': None,
            'last_success': None,
            'last_failure': None,
            'consecutive_failures': 0
        }
    
    def initialize_components(self):
        """Initialize VOD manager and Cablecast client"""
        try:
            self.vod_manager = VODService()
            self.cablecast_client = VODService().client
            logger.info("VOD components initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize VOD components: {e}")
            return False
    
    def check_vod_connection(self) -> bool:
        """Check connection to Cablecast API"""
        try:
            if not self.cablecast_client:
                logger.error("Cablecast client not initialized")
                return False
            
            success = self.cablecast_client.test_connection()
            if success:
                logger.info("✓ Cablecast API connection successful")
                return True
            else:
                logger.warning("⚠ Cablecast API connection failed")
                return False
        except Exception as e:
            logger.error(f"Error checking VOD connection: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status between Archivist and VOD system"""
        try:
            if not self.vod_manager:
                logger.error("VOD manager not initialized")
                return {}
            
            status = self.vod_manager.get_sync_status()
            logger.info(f"Sync status: {status['synced_transcriptions']}/{status['total_transcriptions']} ({status['sync_percentage']:.1f}%)")
            return status
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {}
    
    def check_pending_vods(self) -> List[Dict[str, Any]]:
        """Check for VODs that are still processing"""
        try:
            from core.models import CablecastVODORM
            
            pending_vods = CablecastVODORM.query.filter(
                CablecastVODORM.vod_state.in_(['processing', 'uploading', 'transcoding'])
            ).all()
            
            if pending_vods:
                logger.info(f"Found {len(pending_vods)} pending VODs")
                for vod in pending_vods:
                    logger.debug(f"Pending VOD {vod.id}: {vod.vod_state} ({vod.percent_complete}%)")
            
            return [{
                'id': vod.id,
                'state': vod.vod_state,
                'percent_complete': vod.percent_complete,
                'created_at': vod.created_at.isoformat(),
                'updated_at': vod.updated_at.isoformat()
            } for vod in pending_vods]
        except Exception as e:
            logger.error(f"Error checking pending VODs: {e}")
            return []
    
    def update_vod_status(self, vod_id: int) -> bool:
        """Update status of a specific VOD from Cablecast"""
        try:
            if not self.cablecast_client:
                return False
            
            status = self.cablecast_client.get_vod_status(vod_id)
            if status:
                from core.models import CablecastVODORM
                from core.app import db
                
                vod = CablecastVODORM.query.get(vod_id)
                if vod:
                    vod.vod_state = status.get('vodState', vod.vod_state)
                    vod.percent_complete = status.get('percentComplete', vod.percent_complete)
                    vod.updated_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"Updated VOD {vod_id} status: {vod.vod_state} ({vod.percent_complete}%)")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error updating VOD {vod_id} status: {e}")
            return False
    
    def check_transcription_logs(self) -> Dict[str, Any]:
        """Analyze transcription logs for VOD-related activity"""
        try:
            from core.models import TranscriptionResultORM, CablecastShowORM
            
            # Get recent transcriptions
            recent_transcriptions = TranscriptionResultORM.query.order_by(
                TranscriptionResultORM.completed_at.desc()
            ).limit(50).all()
            
            # Get VOD-related transcriptions
            vod_transcriptions = TranscriptionResultORM.query.join(
                CablecastShowORM
            ).order_by(
                TranscriptionResultORM.completed_at.desc()
            ).limit(20).all()
            
            # Analyze auto-publish activity
            auto_publish_enabled = os.getenv('AUTO_PUBLISH_TO_VOD', 'false').lower() == 'true'
            
            log_analysis = {
                'total_recent_transcriptions': len(recent_transcriptions),
                'vod_transcriptions': len(vod_transcriptions),
                'auto_publish_enabled': auto_publish_enabled,
                'recent_activity': []
            }
            
            # Add recent activity details
            for transcription in recent_transcriptions[:10]:
                vod_show = CablecastShowORM.query.filter_by(
                    transcription_id=transcription.id
                ).first()
                
                log_analysis['recent_activity'].append({
                    'id': transcription.id,
                    'video_path': transcription.video_path,
                    'completed_at': transcription.completed_at.isoformat(),
                    'has_vod': vod_show is not None,
                    'vod_show_id': vod_show.cablecast_id if vod_show else None
                })
            
            logger.info(f"Log analysis: {log_analysis['total_recent_transcriptions']} recent transcriptions, {log_analysis['vod_transcriptions']} with VOD")
            return log_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing transcription logs: {e}")
            return {}
    
    def sync_shows_and_vods(self) -> Dict[str, Any]:
        """Sync shows and VODs from Cablecast"""
        try:
            if not self.vod_manager:
                return {'success': False, 'error': 'VOD manager not initialized'}
            
            # Sync shows
            shows_synced = self.vod_manager.sync_shows_from_cablecast()
            
            # Sync VODs
            vods_synced = self.vod_manager.sync_vods_from_cablecast()
            
            result = {
                'success': True,
                'shows_synced': shows_synced,
                'vods_synced': vods_synced,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Sync completed: {shows_synced} shows, {vods_synced} VODs")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing shows and VODs: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        try:
            # Check connection
            connection_ok = self.check_vod_connection()
            
            # Get sync status
            sync_status = self.get_sync_status()
            
            # Check pending VODs
            pending_vods = self.check_pending_vods()
            
            # Analyze logs
            log_analysis = self.check_transcription_logs()
            
            # Update stats
            self.stats['total_checks'] += 1
            self.stats['last_check'] = datetime.utcnow().isoformat()
            
            if connection_ok and sync_status:
                self.stats['successful_syncs'] += 1
                self.stats['last_success'] = datetime.utcnow().isoformat()
                self.stats['consecutive_failures'] = 0
            else:
                self.stats['failed_syncs'] += 1
                self.stats['last_failure'] = datetime.utcnow().isoformat()
                self.stats['consecutive_failures'] += 1
            
            health_report = {
                'timestamp': datetime.utcnow().isoformat(),
                'connection_status': 'healthy' if connection_ok else 'unhealthy',
                'sync_status': sync_status,
                'pending_vods_count': len(pending_vods),
                'pending_vods': pending_vods,
                'log_analysis': log_analysis,
                'monitor_stats': self.stats,
                'configuration': {
                    'auto_publish_enabled': os.getenv('AUTO_PUBLISH_TO_VOD', 'false').lower() == 'true',
                    'vod_max_retries': os.getenv('VOD_MAX_RETRIES', '3'),
                    'vod_retry_delay': os.getenv('VOD_RETRY_DELAY', '60'),
                    'cablecast_api_url': os.getenv('CABLECAST_API_URL', 'not_set')
                }
            }
            
            # Determine overall health
            if connection_ok and sync_status.get('sync_percentage', 0) > 0:
                health_report['overall_health'] = 'healthy'
            elif self.stats['consecutive_failures'] > 3:
                health_report['overall_health'] = 'critical'
            else:
                health_report['overall_health'] = 'warning'
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_health': 'error',
                'error': str(e)
            }
    
    def run_monitoring_cycle(self) -> bool:
        """Run a complete monitoring cycle"""
        logger.info("Starting VOD monitoring cycle...")
        
        try:
            # Generate health report
            health_report = self.generate_health_report()
            
            # Log health status
            logger.info(f"Health status: {health_report['overall_health']}")
            
            # Handle critical issues
            if health_report['overall_health'] == 'critical':
                logger.error("CRITICAL: VOD system health is poor - consecutive failures detected")
                # Could add alerting here (email, Slack, etc.)
            
            # Save health report to file
            self.save_health_report(health_report)
            
            return health_report['overall_health'] != 'error'
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            return False
    
    def save_health_report(self, report: Dict[str, Any]):
        """Save health report to file"""
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'vod_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = os.path.join(reports_dir, f'vod_health_{timestamp}.json')
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.debug(f"Health report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving health report: {e}")

def main():
    """Main function for the VOD sync monitor"""
    parser = argparse.ArgumentParser(description="VOD Sync Monitor")
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level')
    parser.add_argument('--single-run', action='store_true', help='Run once and exit')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger.info("Starting VOD Sync Monitor")
    logger.info(f"Monitoring interval: {args.interval} seconds")
    logger.info(f"Log level: {args.log_level}")
    
    # Initialize monitor
    monitor = VODSyncMonitor()
    
    if not monitor.initialize_components():
        logger.error("Failed to initialize VOD components")
        sys.exit(1)
    
    try:
        if args.single_run:
            # Run once
            success = monitor.run_monitoring_cycle()
            sys.exit(0 if success else 1)
        else:
            # Run continuously
            logger.info("Starting continuous monitoring...")
            while True:
                try:
                    monitor.run_monitoring_cycle()
                    time.sleep(args.interval)
                except KeyboardInterrupt:
                    logger.info("Monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(args.interval)
    
    except Exception as e:
        logger.error(f"Fatal error in VOD monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 