from redis import Redis
from rq import Queue, Worker
from loguru import logger
from config import REDIS_HOST, REDIS_PORT, REDIS_DB

# Initialize Redis connection
redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Initialize queue
transcription_queue = Queue('transcription', connection=redis_conn)

def get_job_status(job_id: str) -> dict:
    """Get the status of a job by its ID."""
    try:
        job = transcription_queue.fetch_job(job_id)
        if job is None:
            return {"status": "unknown", "error": "Job not found"}
        
        if job.is_failed:
            return {"status": "error", "error": str(job.exc_info)}
        
        if job.is_finished:
            return {"status": "done", "result": job.result}
        
        if job.is_started:
            return {"status": "running"}
        
        return {"status": "queued"}
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return {"status": "error", "error": str(e)}

def enqueue_transcription(video_path: str) -> str:
    """Enqueue a transcription job and return the job ID."""
    try:
        job = transcription_queue.enqueue(
            'core.transcription.run_whisperx',
            video_path,
            job_timeout='1h'
        )
        return job.id
    except Exception as e:
        logger.error(f"Error enqueueing transcription job: {e}")
        raise 