"""Failed job cleanup module for the Archivist application.

This module handles the automatic cleanup of failed jobs in the task queue,
ensuring that failed jobs are properly archived or removed after a
configurable retention period.

Key Features:
- Automatic failed job cleanup
- Configurable retention periods
- Job archiving
- Error logging
- Cleanup scheduling
- Status reporting

Example:
    >>> from core.failed_job_cleaner import cleanup_failed_jobs
    >>> cleanup_failed_jobs()
    >>> print("Failed jobs cleaned up")
"""

import time
from core.task_queue import queue_manager
from loguru import logger

logger.info("Starting failed job cleaner loop...")
 
while True:
    queue_manager.cleanup_failed_jobs()
    time.sleep(60) 