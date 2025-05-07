import time
from core.task_queue import queue_manager
from loguru import logger

logger.info("Starting failed job cleaner loop...")

while True:
    queue_manager.cleanup_failed_jobs()
    time.sleep(60) 