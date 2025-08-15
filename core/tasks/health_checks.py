# PURPOSE: Celery tasks for automated system health checks
# DEPENDENCIES: core.monitoring.health_checks, core.tasks.celery_app
# MODIFICATION NOTES: v1.0 - Initial implementation for automated health monitoring

"""Celery tasks for automated system health checks.

This module provides Celery tasks for automatically monitoring system health,
including storage, API connectivity, and system resources.
"""

from celery import current_task
from loguru import logger
from typing import Dict, Any
import time

from core.tasks import celery_app
from core.monitoring.health_checks import get_health_manager


@celery_app.task(name="health_checks.run_scheduled_health_check", bind=True)
def run_scheduled_health_check(self) -> Dict[str, Any]:
    """
    Run scheduled system health checks.
    
    This task runs comprehensive health checks on all system components
    including storage, API connectivity, and system resources.
    
    Returns:
        Dictionary containing health check results:
        {
            'success': bool,
            'overall_status': str,      # 'healthy', 'degraded', 'unhealthy'
            'summary': Dict,            # Summary of all checks
            'checks': Dict,             # Detailed check results
            'task_id': str              # Celery task ID
        }
    """
    task_id = self.request.id
    logger.info(f"Starting scheduled health check task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Running health checks...'}
        )
        
        # Get health manager and run checks
        health_manager = get_health_manager()
        result = health_manager.run_all_health_checks()
        result['task_id'] = task_id
        result['success'] = True
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        # Log results
        overall_status = result.get('overall_status', 'unknown')
        summary = result.get('summary', {})
        logger.info(f"Health check completed: {overall_status} - {summary.get('healthy', 0)} healthy, {summary.get('degraded', 0)} degraded, {summary.get('unhealthy', 0)} unhealthy")
        
        # Log warnings for degraded/unhealthy components
        if overall_status != 'healthy':
            logger.warning(f"System health check shows {overall_status} status")
            checks = result.get('checks', {})
            for category, category_checks in checks.items():
                for check in category_checks:
                    if check.get('status') in ['degraded', 'unhealthy']:
                        logger.warning(f"Health check issue: {check.get('component')} - {check.get('message')}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error running health checks: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="health_checks.run_storage_check", bind=True)
def run_storage_check(self) -> Dict[str, Any]:
    """
    Run storage-specific health checks.
    
    Returns:
        Dictionary containing storage check results
    """
    task_id = self.request.id
    logger.info(f"Starting storage health check task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking storage...'}
        )
        
        # Get health manager and run storage checks
        health_manager = get_health_manager()
        storage_results = health_manager.storage_checker.check_all_storage()
        
        # Convert to dictionary format
        result = {
            'success': True,
            'task_id': task_id,
            'storage_checks': [r.__dict__ for r in storage_results],
            'summary': {
                'total': len(storage_results),
                'healthy': sum(1 for r in storage_results if r.status == 'healthy'),
                'degraded': sum(1 for r in storage_results if r.status == 'degraded'),
                'unhealthy': sum(1 for r in storage_results if r.status == 'unhealthy'),
            }
        }
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"Storage health check completed: {result['summary']['healthy']} healthy, {result['summary']['degraded']} degraded, {result['summary']['unhealthy']} unhealthy")
        return result
        
    except Exception as e:
        error_msg = f"Error running storage health checks: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="health_checks.run_api_check", bind=True)
def run_api_check(self) -> Dict[str, Any]:
    """
    Run API connectivity health checks.
    
    Returns:
        Dictionary containing API check results
    """
    task_id = self.request.id
    logger.info(f"Starting API health check task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking API connectivity...'}
        )
        
        # Get health manager and run API checks
        health_manager = get_health_manager()
        api_result = health_manager.api_checker.check_cablecast_api()
        
        # Convert to dictionary format
        result = {
            'success': True,
            'task_id': task_id,
            'api_checks': [api_result.__dict__],
            'summary': {
                'total': 1,
                'healthy': 1 if api_result.status == 'healthy' else 0,
                'degraded': 1 if api_result.status == 'degraded' else 0,
                'unhealthy': 1 if api_result.status == 'unhealthy' else 0,
            }
        }
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"API health check completed: {api_result.status} - {api_result.message}")
        return result
        
    except Exception as e:
        error_msg = f"Error running API health checks: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        }


@celery_app.task(name="health_checks.run_system_check", bind=True)
def run_system_check(self) -> Dict[str, Any]:
    """
    Run system resource health checks.
    
    Returns:
        Dictionary containing system check results
    """
    task_id = self.request.id
    logger.info(f"Starting system health check task {task_id}")
    
    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Checking system resources...'}
        )
        
        # Get health manager and run system checks
        health_manager = get_health_manager()
        system_resources = health_manager.system_checker.check_system_resources()
        celery_workers = health_manager.system_checker.check_celery_workers()
        
        # Convert to dictionary format
        system_results = [system_resources, celery_workers]
        result = {
            'success': True,
            'task_id': task_id,
            'system_checks': [r.__dict__ for r in system_results],
            'summary': {
                'total': len(system_results),
                'healthy': sum(1 for r in system_results if r.status == 'healthy'),
                'degraded': sum(1 for r in system_results if r.status == 'degraded'),
                'unhealthy': sum(1 for r in system_results if r.status == 'unhealthy'),
            }
        }
        
        # Update task state with results
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'Completed',
                'result': result
            }
        )
        
        logger.info(f"System health check completed: {result['summary']['healthy']} healthy, {result['summary']['degraded']} degraded, {result['summary']['unhealthy']} unhealthy")
        return result
        
    except Exception as e:
        error_msg = f"Error running system health checks: {str(e)}"
        logger.error(error_msg)
        
        # Update task state with error
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Failed',
                'error': error_msg
            }
        )
        
        return {
            'success': False,
            'error': error_msg,
            'task_id': task_id
        } 