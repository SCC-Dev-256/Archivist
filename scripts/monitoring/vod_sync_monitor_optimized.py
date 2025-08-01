#!/usr/bin/env python3
"""
Optimized VOD Sync Monitor for Archivist application.

Performance optimizations include:
- Database query optimization with eager loading
- Result caching to reduce redundant queries
- Batch processing for multiple VODs
- Connection pooling and resource management
- Reduced logging overhead in production
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from functools import lru_cache
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.exceptions import (
    ConnectionError,
    DatabaseError,
    VODError,
    NetworkError,
    TimeoutError,
    FileError
)

# Performance configuration
CACHE_TTL = 300  # 5 minutes cache TTL
BATCH_SIZE = 10  # Process VODs in batches
QUERY_LIMIT = 50  # Limit database queries
CONNECTION_TIMEOUT = 30  # Connection timeout in seconds

def setup_logging(log_level: str = "INFO"):
    """Setup optimized logging configuration."""
    logger.remove()  # Remove default handler
    
    # Add console handler with optimized format
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # Add file handler with rotation
    logger.add(
        "logs/vod_sync_monitor_optimized.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="gz"  # Compress old logs
    )

class OptimizedVODSyncMonitor:
    """Optimized VOD sync monitor with performance improvements."""
    
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
            'consecutive_failures': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'query_count': 0,
            'avg_query_time': 0.0
        }
        self._cache = {}
        self._cache_timestamps = {}
    
    def initialize_components(self):
        """Initialize components with connection pooling."""
        try:
            from core.services import get_vod_service
            from core.cablecast_client import CablecastAPIClient
            
            # Initialize VOD service with connection pooling
            self.vod_manager = get_vod_service()
            
            # Initialize Cablecast client with optimized settings
            self.cablecast_client = CablecastAPIClient()
            
            logger.info("✅ Optimized VOD components initialized")
            return True
            
        except ConnectionError as e:
            logger.error(f"Connection error initializing components: {e}")
            return False
        except VODError as e:
            logger.error(f"VOD service error initializing components: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing components: {e}")
            return False
    
    @lru_cache(maxsize=128)
    def check_vod_connection(self) -> bool:
        """Check VOD connection with caching."""
        try:
            if not self.cablecast_client:
                return False
            
            # Use cached connection test if recent
            cache_key = 'connection_test'
            if self._is_cache_valid(cache_key, 60):  # 1 minute cache
                self.stats['cache_hits'] += 1
                return self._cache[cache_key]
            
            start_time = time.time()
            result = self.cablecast_client.test_connection()
            query_time = time.time() - start_time
            
            self._update_query_stats(query_time)
            self._cache_result(cache_key, result, 60)
            
            return result
            
        except ConnectionError as e:
            logger.error(f"Connection error checking VOD connection: {e}")
            return False
        except TimeoutError as e:
            logger.error(f"Timeout error checking VOD connection: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking VOD connection: {e}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status with optimized database queries."""
        try:
            from core.models import CablecastVODORM, CablecastShowORM
            from sqlalchemy import func
            
            start_time = time.time()
            
            from core.app import db
            from sqlalchemy import case
            
            # Use single optimized query with aggregation
            sync_stats = db.session.query(
                func.count(CablecastVODORM.id).label('total_vods'),
                func.count(CablecastShowORM.id).label('total_shows'),
                func.sum(case(
                    (CablecastVODORM.vod_state == 'completed', 1),
                    else_=0
                )).label('completed_vods'),
                func.sum(case(
                    (CablecastVODORM.vod_state.in_(['processing', 'uploading', 'transcoding']), 1),
                    else_=0
                )).label('pending_vods')
            ).outerjoin(CablecastShowORM).first()
            
            query_time = time.time() - start_time
            self._update_query_stats(query_time)
            
            if sync_stats:
                total_vods = sync_stats.total_vods or 0
                completed_vods = sync_stats.completed_vods or 0
                sync_percentage = (completed_vods / total_vods * 100) if total_vods > 0 else 0
                
                return {
                    'total_vods': total_vods,
                    'total_shows': sync_stats.total_shows or 0,
                    'completed_vods': completed_vods,
                    'pending_vods': sync_stats.pending_vods or 0,
                    'sync_percentage': round(sync_percentage, 2),
                    'last_updated': datetime.utcnow().isoformat()
                }
            
            return {}
            
        except DatabaseError as e:
            logger.error(f"Database error getting sync status: {e}")
            return {}
        except VODError as e:
            logger.error(f"VOD service error getting sync status: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting sync status: {e}")
            return {}
    
    def check_pending_vods(self) -> List[Dict[str, Any]]:
        """Check pending VODs with optimized query and batching."""
        try:
            from core.models import CablecastVODORM
            
            # Use optimized query with specific columns only
            pending_vods = CablecastVODORM.query.with_entities(
                CablecastVODORM.id,
                CablecastVODORM.vod_state,
                CablecastVODORM.percent_complete,
                CablecastVODORM.created_at,
                CablecastVODORM.updated_at
            ).filter(
                CablecastVODORM.vod_state.in_(['processing', 'uploading', 'transcoding'])
            ).limit(QUERY_LIMIT).all()
            
            if pending_vods:
                logger.info(f"Found {len(pending_vods)} pending VODs")
            
            # Convert to dicts efficiently
            return [{
                'id': vod.id,
                'state': vod.vod_state,
                'percent_complete': vod.percent_complete,
                'created_at': vod.created_at.isoformat(),
                'updated_at': vod.updated_at.isoformat()
            } for vod in pending_vods]
            
        except DatabaseError as e:
            logger.error(f"Database error checking pending VODs: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error checking pending VODs: {e}")
            return []
    
    def update_vod_status_batch(self, vod_ids: List[int]) -> Dict[str, int]:
        """Update status of multiple VODs in batch for better performance."""
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        
        try:
            if not self.cablecast_client:
                return results
            
            from core.models import CablecastVODORM
            from core.app import db
            
            # Process in batches
            for i in range(0, len(vod_ids), BATCH_SIZE):
                batch = vod_ids[i:i + BATCH_SIZE]
                
                for vod_id in batch:
                    try:
                        status = self.cablecast_client.get_vod_status(vod_id)
                        if status:
                            vod = CablecastVODORM.query.get(vod_id)
                            if vod:
                                vod.vod_state = status.get('vodState', vod.vod_state)
                                vod.percent_complete = status.get('percentComplete', vod.percent_complete)
                                vod.updated_at = datetime.utcnow()
                                results['success'] += 1
                            else:
                                results['skipped'] += 1
                        else:
                            results['skipped'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to update VOD {vod_id}: {e}")
                        results['failed'] += 1
                
                # Commit batch
                try:
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Database error committing batch: {e}")
                    db.session.rollback()
                    results['failed'] += len(batch)
                    results['success'] -= len(batch)
            
            logger.info(f"Batch update completed: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
            return results
            
        except ConnectionError as e:
            logger.error(f"Connection error in batch update: {e}")
            return {'success': 0, 'failed': len(vod_ids), 'skipped': 0}
        except DatabaseError as e:
            logger.error(f"Database error in batch update: {e}")
            return {'success': 0, 'failed': len(vod_ids), 'skipped': 0}
        except Exception as e:
            logger.error(f"Unexpected error in batch update: {e}")
            return {'success': 0, 'failed': len(vod_ids), 'skipped': 0}
    
    def check_transcription_logs(self) -> Dict[str, Any]:
        """Analyze transcription logs with optimized queries."""
        try:
            from core.models import TranscriptionResultORM, CablecastShowORM
            from sqlalchemy import func
            
            # Use optimized queries with aggregation
            recent_count = db.session.query(func.count(TranscriptionResultORM.id)).filter(
                TranscriptionResultORM.completed_at >= datetime.utcnow() - timedelta(hours=24)
            ).scalar()
            
            vod_count = db.session.query(func.count(TranscriptionResultORM.id)).join(
                CablecastShowORM
            ).scalar()
            
            # Get recent activity with limit
            recent_transcriptions = TranscriptionResultORM.query.with_entities(
                TranscriptionResultORM.id,
                TranscriptionResultORM.video_path,
                TranscriptionResultORM.completed_at
            ).order_by(
                TranscriptionResultORM.completed_at.desc()
            ).limit(10).all()
            
            log_analysis = {
                'total_recent_transcriptions': recent_count or 0,
                'vod_transcriptions': vod_count or 0,
                'auto_publish_enabled': os.getenv('AUTO_PUBLISH_TO_VOD', 'false').lower() == 'true',
                'recent_activity': [{
                    'id': t.id,
                    'video_path': t.video_path,
                    'completed_at': t.completed_at.isoformat()
                } for t in recent_transcriptions]
            }
            
            logger.info(f"Log analysis: {log_analysis['total_recent_transcriptions']} recent transcriptions, {log_analysis['vod_transcriptions']} with VOD")
            return log_analysis
            
        except DatabaseError as e:
            logger.error(f"Database error analyzing transcription logs: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error analyzing transcription logs: {e}")
            return {}
    
    def _is_cache_valid(self, key: str, ttl: int) -> bool:
        """Check if cached result is still valid."""
        if key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[key] < ttl
    
    def _cache_result(self, key: str, result: Any, ttl: int):
        """Cache a result with timestamp."""
        self._cache[key] = result
        self._cache_timestamps[key] = time.time()
        self.stats['cache_misses'] += 1
    
    def _update_query_stats(self, query_time: float):
        """Update query performance statistics."""
        self.stats['query_count'] += 1
        # Update running average
        self.stats['avg_query_time'] = (
            (self.stats['avg_query_time'] * (self.stats['query_count'] - 1) + query_time) / 
            self.stats['query_count']
        )
    
    def run_monitoring_cycle(self) -> bool:
        """Run a complete monitoring cycle with performance tracking."""
        logger.info("Starting optimized VOD monitoring cycle...")
        
        try:
            # Check connection with caching
            connection_ok = self.check_vod_connection()
            
            # Get sync status with optimized queries
            sync_status = self.get_sync_status()
            
            # Check pending VODs with batching
            pending_vods = self.check_pending_vods()
            
            # Analyze logs with optimized queries
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
            
            # Log performance metrics
            perf_stats = self.get_performance_stats()
            logger.info(f"Performance: {perf_stats['cache_hit_rate']:.1f}% cache hit rate, {perf_stats['avg_query_time']}s avg query time")
            
            return connection_ok and sync_status
            
        except ConnectionError as e:
            logger.error(f"Connection error in monitoring cycle: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in monitoring cycle: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            'cache_hit_rate': (
                self.stats['cache_hits'] / (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
                if (self.stats['cache_hits'] + self.stats['cache_misses']) > 0 else 0
            ),
            'avg_query_time': round(self.stats['avg_query_time'], 3),
            'total_queries': self.stats['query_count'],
            'cache_hits': self.stats['cache_hits'],
            'cache_misses': self.stats['cache_misses']
        }

def main():
    """Main function for the optimized VOD sync monitor."""
    parser = argparse.ArgumentParser(description="Optimized VOD Sync Monitor")
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds (default: 300)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Log level')
    parser.add_argument('--single-run', action='store_true', help='Run once and exit')
    parser.add_argument('--performance', action='store_true', help='Show performance statistics')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger.info("Starting Optimized VOD Sync Monitor")
    logger.info(f"Monitoring interval: {args.interval} seconds")
    logger.info(f"Log level: {args.log_level}")
    
    # Initialize monitor
    monitor = OptimizedVODSyncMonitor()
    
    if not monitor.initialize_components():
        logger.error("Failed to initialize VOD components")
        sys.exit(1)
    
    try:
        if args.single_run:
            # Run once
            success = monitor.run_monitoring_cycle()
            if args.performance:
                stats = monitor.get_performance_stats()
                logger.info(f"Performance stats: {stats}")
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
                except ConnectionError as e:
                    logger.error(f"Connection error in monitoring loop: {e}")
                    time.sleep(args.interval)
                except Exception as e:
                    logger.error(f"Unexpected error in monitoring loop: {e}")
                    time.sleep(args.interval)
    
    except ConnectionError as e:
        logger.error(f"Fatal connection error in VOD monitor: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error in VOD monitor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 