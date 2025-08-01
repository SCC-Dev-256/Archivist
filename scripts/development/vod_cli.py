#!/usr/bin/env python3
"""VOD CLI tool for managing VOD operations."""

import argparse
import os
import sys

from loguru import logger

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.services import VODService
from core.exceptions import (
    ConnectionError,
    DatabaseError,
    VODError
)


def setup_logging():
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )


def sync_status():
    """Get sync status between Archivist and VOD system"""
    try:
        manager = VODService()
        status = manager.get_sync_status()
        
        logger.info("="*60)
        logger.info("VOD SYNC STATUS")
        logger.info("="*60)
        logger.info(f"Total Transcriptions: {status['total_transcriptions']}")
        logger.info(f"Synced Transcriptions: {status['synced_transcriptions']}")
        logger.info(f"Sync Percentage: {status['sync_percentage']:.1f}%")
        
        if status['recent_syncs']:
            logger.info("Recent Syncs:")
            for sync in status['recent_syncs'][:5]:
                logger.info(f"  • {sync['title']} (ID: {sync['cablecast_id']}) - {sync['synced_at']}")
        
        logger.info("="*60)
        
    except ConnectionError as e:
        logger.error(f"Connection error getting sync status: {e}")
        return 1
    except DatabaseError as e:
        logger.error(f"Database error getting sync status: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error getting sync status: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error getting sync status: {e}")
        return 1
    return 0


def publish_transcription(transcription_id):
    """Publish a single transcription to VOD"""
    try:
        manager = VODService()
        result = manager.process_archivist_content_for_vod(transcription_id)
        
        if result:
            logger.success(f"Successfully published transcription {transcription_id} to VOD")
            logger.info(f"  Show ID: {result['show_id']}")
            logger.info(f"  VOD ID: {result['vod_id']}")
            logger.info(f"  Title: {result['title']}")
        else:
            logger.error(f"Failed to publish transcription {transcription_id} to VOD")
            return 1
            
    except FileNotFoundError as e:
        logger.error(f"Transcription file not found: {e}")
        return 1
    except ConnectionError as e:
        logger.error(f"Connection error publishing transcription: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error publishing transcription: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error publishing transcription: {e}")
        return 1
    return 0


def batch_publish_transcriptions(transcription_ids):
    """Batch publish multiple transcriptions to VOD"""
    try:
        manager = VODService()
        results = manager.batch_process_transcriptions(transcription_ids)
        
        logger.info("="*60)
        logger.info("BATCH PUBLISH RESULTS")
        logger.info("="*60)
        logger.info(f"Processed: {results['processed_count']}")
        logger.info(f"Errors: {results['error_count']}")
        
        if results['results']:
            logger.info("Successful Publications:")
            for result in results['results']:
                logger.info(f"  • {result['title']} (VOD ID: {result['vod_id']})")
        
        if results['errors']:
            logger.error("Errors:")
            for error in results['errors']:
                logger.error(f"  • {error}")
        
        logger.info("="*60)
        
        return 0 if results['error_count'] == 0 else 1
        
    except ConnectionError as e:
        logger.error(f"Connection error batch publishing: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error batch publishing: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error batch publishing: {e}")
        return 1
        return 1


def sync_shows():
    """Sync shows from Cablecast to Archivist database"""
    try:
        manager = VODService()
        synced_count = manager.sync_shows_from_cablecast()
        
        logger.success(f"Synced {synced_count} shows from Cablecast")
        
    except ConnectionError as e:
        logger.error(f"Connection error syncing shows: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error syncing shows: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error syncing shows: {e}")
        return 1
    return 0


def sync_vods():
    """Sync VODs from Cablecast to Archivist database"""
    try:
        manager = VODService()
        synced_count = manager.sync_vods_from_cablecast()
        
        logger.success(f"Synced {synced_count} VODs from Cablecast")
        
    except ConnectionError as e:
        logger.error(f"Connection error syncing VODs: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error syncing VODs: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error syncing VODs: {e}")
        return 1
    return 0


def test_connection():
    """Test connection to Cablecast API"""
    try:
        manager = VODService()
        if manager.test_connection():
            logger.success("Cablecast API connection successful")
        else:
            logger.error("Cablecast API connection failed")
            return 1
            
    except ConnectionError as e:
        logger.error(f"Connection error testing API: {e}")
        return 1
    except VODError as e:
        logger.error(f"VOD service error testing connection: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error testing connection: {e}")
        return 1
    return 0


def list_transcriptions():
    """List available transcriptions"""
    try:
        manager = VODService()
        transcriptions = manager.list_transcriptions()
        
        logger.info("="*80)
        logger.info("AVAILABLE TRANSCRIPTIONS")
        logger.info("="*80)
        logger.info(f"{'ID':<36} {'Title':<30} {'Status':<12} {'Completed'}")
        logger.info("-" * 80)
        
        for transcription in transcriptions:
            status = transcription.get('status', 'unknown')
            completed = transcription.get('completed_at', 'N/A')
            title = transcription.get('title', 'Unknown')[:29] + '...' if len(transcription.get('title', '')) > 30 else transcription.get('title', 'Unknown')
            
            logger.info(f"{transcription['id']:<36} {title:<30} {status:<12} {completed}")
        
        logger.info("="*80)
        
    except ConnectionError as e:
        logger.error(f"Connection error listing transcriptions: {e}")
        return 1
    except DatabaseError as e:
        logger.error(f"Database error listing transcriptions: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error listing transcriptions: {e}")
        return 1
        return 1
    return 0


def main():
    """Main CLI entry point."""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='VOD Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync status command
    subparsers.add_parser('sync-status', help='Get sync status')
    
    # Publish commands
    publish_parser = subparsers.add_parser('publish', help='Publish transcription to VOD')
    publish_parser.add_argument('transcription_id', help='Transcription ID to publish')
    
    batch_parser = subparsers.add_parser('batch-publish', help='Batch publish transcriptions')
    batch_parser.add_argument('transcription_ids', nargs='+', help='Transcription IDs to publish')
    
    # Sync commands
    subparsers.add_parser('sync-shows', help='Sync shows from Cablecast')
    subparsers.add_parser('sync-vods', help='Sync VODs from Cablecast')
    
    # Test commands
    subparsers.add_parser('test-connection', help='Test Cablecast API connection')
    subparsers.add_parser('list', help='List available transcriptions')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'sync-status':
        return sync_status()
    elif args.command == 'publish':
        return publish_transcription(args.transcription_id)
    elif args.command == 'batch-publish':
        return batch_publish_transcriptions(args.transcription_ids)
    elif args.command == 'sync-shows':
        return sync_shows()
    elif args.command == 'sync-vods':
        return sync_vods()
    elif args.command == 'test-connection':
        return test_connection()
    elif args.command == 'list':
        return list_transcriptions()
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 