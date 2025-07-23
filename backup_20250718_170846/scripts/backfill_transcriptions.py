#!/usr/bin/env python3
"""Script to backfill existing transcriptions into the database."""

import os
import sys
import glob
from datetime import datetime
import uuid
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from core.app import create_app, db
from core.models import TranscriptionResultORM
from core.config import OUTPUT_DIR
from loguru import logger

def backfill_transcriptions():
    """Backfill existing transcriptions into the database."""
    app = create_app()
    
    with app.app_context():
        try:
            # Find all .srt files in the output directory
            srt_files = glob.glob(os.path.join(OUTPUT_DIR, "*.srt"))
            logger.info(f"Found {len(srt_files)} SRT files to backfill")
            
            for srt_path in srt_files:
                try:
                    # Check if this transcription is already in the database
                    existing = TranscriptionResultORM.query.filter_by(output_path=srt_path).first()
                    if existing:
                        logger.info(f"Transcription already exists in database: {srt_path}")
                        continue
                    
                    # Get the video path from the SRT filename
                    video_name = os.path.splitext(os.path.basename(srt_path))[0]
                    video_path = os.path.join("/mnt", video_name)
                    
                    # Create new transcription result
                    result = TranscriptionResultORM(
                        id=str(uuid.uuid4()),
                        video_path=video_path,
                        output_path=srt_path,
                        status='completed',
                        completed_at=datetime.utcnow()
                    )
                    db.session.add(result)
                    logger.info(f"Added transcription to database: {srt_path}")
                    
                except Exception as e:
                    logger.error(f"Error processing {srt_path}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            logger.info("Successfully backfilled transcriptions")
            
        except Exception as e:
            logger.error(f"Error backfilling transcriptions: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    backfill_transcriptions() 