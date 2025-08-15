#!/usr/bin/env python3
"""VOD Command Line Interface for Archivist.

This CLI tool provides easy access to VOD integration features for managing
content between Archivist and Cablecast VOD systems.

Usage:
    python3 vod_cli.py sync-status
    python3 vod_cli.py publish <transcription_id>
    python3 vod_cli.py batch-publish <transcription_id1> <transcription_id2> ...
    python3 vod_cli.py sync-shows
    python3 vod_cli.py sync-vods
    python3 vod_cli.py test-connection
"""

import os
import sys
import argparse
import json
from loguru import logger
from core.services import VODService

# Add the core directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

def setup_logging():
    """Setup logging for CLI"""
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def sync_status():
    """Get sync status between Archivist and VOD system"""
    try:
        manager = VODService()
        status = manager.get_sync_status()
        
        print("\n" + "="*60)
        print("VOD SYNC STATUS")
        print("="*60)
        print(f"Total Transcriptions: {status['total_transcriptions']}")
        print(f"Synced Transcriptions: {status['synced_transcriptions']}")
        print(f"Sync Percentage: {status['sync_percentage']:.1f}%")
        
        if status['recent_syncs']:
            print(f"\nRecent Syncs:")
            for sync in status['recent_syncs'][:5]:
                print(f"  • {sync['title']} (ID: {sync['cablecast_id']}) - {sync['synced_at']}")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return 1
    return 0

def publish_transcription(transcription_id):
    """Publish a single transcription to VOD"""
    try:
        manager = VODService()
        result = manager.process_archivist_content_for_vod(transcription_id)
        
        if result:
            print(f"\n✓ Successfully published transcription {transcription_id} to VOD")
            print(f"  Show ID: {result['show_id']}")
            print(f"  VOD ID: {result['vod_id']}")
            print(f"  Title: {result['title']}")
        else:
            print(f"\n✗ Failed to publish transcription {transcription_id} to VOD")
            return 1
            
    except Exception as e:
        logger.error(f"Error publishing transcription: {e}")
        return 1
    return 0

def batch_publish_transcriptions(transcription_ids):
    """Batch publish multiple transcriptions to VOD"""
    try:
        manager = VODService()
        results = manager.batch_process_transcriptions(transcription_ids)
        
        print(f"\n" + "="*60)
        print("BATCH PUBLISH RESULTS")
        print("="*60)
        print(f"Processed: {results['processed_count']}")
        print(f"Errors: {results['error_count']}")
        
        if results['results']:
            print(f"\nSuccessful Publications:")
            for result in results['results']:
                print(f"  • {result['title']} (VOD ID: {result['vod_id']})")
        
        if results['errors']:
            print(f"\nErrors:")
            for error in results['errors']:
                print(f"  • {error}")
        
        print("="*60)
        
        return 0 if results['error_count'] == 0 else 1
        
    except Exception as e:
        logger.error(f"Error batch publishing: {e}")
        return 1

def sync_shows():
    """Sync shows from Cablecast to Archivist database"""
    try:
        manager = VODService()
        synced_count = manager.sync_shows_from_cablecast()
        
        print(f"\n✓ Synced {synced_count} shows from Cablecast")
        
    except Exception as e:
        logger.error(f"Error syncing shows: {e}")
        return 1
    return 0

def sync_vods():
    """Sync VODs from Cablecast to Archivist database"""
    try:
        manager = VODService()
        synced_count = manager.sync_vods_from_cablecast()
        
        print(f"\n✓ Synced {synced_count} VODs from Cablecast")
        
    except Exception as e:
        logger.error(f"Error syncing VODs: {e}")
        return 1
    return 0

def test_connection():
    """Test connection to Cablecast API"""
    try:
        manager = VODService()
        client = manager.client
        success = client.test_connection()
        
        if success:
            print("\n✓ Cablecast API connection successful")
        else:
            print("\n✗ Cablecast API connection failed")
            return 1
            
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return 1
    return 0

def list_transcriptions():
    """List available transcriptions"""
    try:
        from core.models import TranscriptionResultORM
        
        transcriptions = TranscriptionResultORM.query.order_by(
            TranscriptionResultORM.completed_at.desc()
        ).limit(20).all()
        
        print("\n" + "="*80)
        print("AVAILABLE TRANSCRIPTIONS")
        print("="*80)
        print(f"{'ID':<36} {'Title':<30} {'Status':<12} {'Completed'}")
        print("-" * 80)
        
        for t in transcriptions:
            title = os.path.basename(t.video_path)[:28] + ".." if len(os.path.basename(t.video_path)) > 30 else os.path.basename(t.video_path)
            print(f"{t.id:<36} {title:<30} {t.status:<12} {t.completed_at.strftime('%Y-%m-%d %H:%M')}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error listing transcriptions: {e}")
        return 1
    return 0

def main():
    """Main CLI function"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="VOD Command Line Interface for Archivist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 vod_cli.py sync-status
  python3 vod_cli.py publish abc123-def456-ghi789
  python3 vod_cli.py batch-publish abc123 def456 ghi789
  python3 vod_cli.py sync-shows
  python3 vod_cli.py test-connection
  python3 vod_cli.py list-transcriptions
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sync status command
    subparsers.add_parser('sync-status', help='Get sync status between Archivist and VOD system')
    
    # Publish command
    publish_parser = subparsers.add_parser('publish', help='Publish a transcription to VOD')
    publish_parser.add_argument('transcription_id', help='Transcription ID to publish')
    
    # Batch publish command
    batch_parser = subparsers.add_parser('batch-publish', help='Batch publish multiple transcriptions to VOD')
    batch_parser.add_argument('transcription_ids', nargs='+', help='Transcription IDs to publish')
    
    # Sync shows command
    subparsers.add_parser('sync-shows', help='Sync shows from Cablecast to Archivist database')
    
    # Sync VODs command
    subparsers.add_parser('sync-vods', help='Sync VODs from Cablecast to Archivist database')
    
    # Test connection command
    subparsers.add_parser('test-connection', help='Test connection to Cablecast API')
    
    # List transcriptions command
    subparsers.add_parser('list-transcriptions', help='List available transcriptions')
    
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
    elif args.command == 'list-transcriptions':
        return list_transcriptions()
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 