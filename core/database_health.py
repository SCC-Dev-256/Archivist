"""
Database health monitoring for PostgreSQL connectivity and performance.
"""

import time
from datetime import datetime
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

class DatabaseHealthChecker:
    """Monitor database health and performance."""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.last_check = None
        self.connection_status = 'unknown'
        self.response_times = []
    
    def check_connectivity(self):
        """Check if database is accessible."""
        try:
            start_time = time.time()
            result = self.db_session.execute(text('SELECT 1'))
            result.fetchone()
            response_time = time.time() - start_time
            
            self.connection_status = 'connected'
            self.last_check = datetime.now()
            
            # Store response time (keep last 100)
            self.response_times.append(response_time)
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
            
            return {
                'status': 'connected',
                'response_time': round(response_time, 3),
                'last_check': self.last_check.isoformat()
            }
            
        except SQLAlchemyError as e:
            self.connection_status = 'disconnected'
            self.last_check = datetime.now()
            logger.error(f"Database connectivity check failed: {e}")
            
            return {
                'status': 'disconnected',
                'error': str(e),
                'last_check': self.last_check.isoformat()
            }
    
    def check_performance(self):
        """Check database performance metrics."""
        try:
            # Check active connections
            result = self.db_session.execute(text("""
                SELECT 
                    count(*) as active_connections,
                    state,
                    application_name
                FROM pg_stat_activity 
                WHERE state = 'active'
                GROUP BY state, application_name
            """))
            active_connections = result.fetchall()
            
            # Check database size
            result = self.db_session.execute(text("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    pg_database_size(current_database()) as db_size_bytes
            """))
            db_size = result.fetchone()
            
            # Check table statistics
            result = self.db_session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables 
                ORDER BY n_live_tup DESC 
                LIMIT 10
            """))
            table_stats = result.fetchall()
            
            return {
                'active_connections': len(active_connections),
                'connection_details': [
                    {
                        'state': row.state,
                        'application': row.application_name,
                        'count': row.active_connections
                    }
                    for row in active_connections
                ],
                'database_size': {
                    'formatted': db_size.db_size,
                    'bytes': db_size.db_size_bytes
                },
                'table_statistics': [
                    {
                        'schema': row.schemaname,
                        'table': row.tablename,
                        'inserts': row.inserts,
                        'updates': row.updates,
                        'deletes': row.deletes,
                        'live_rows': row.live_rows,
                        'dead_rows': row.dead_rows
                    }
                    for row in table_stats
                ]
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database performance check failed: {e}")
            return {
                'error': str(e)
            }
    
    def get_health_status(self):
        """Get comprehensive database health status."""
        connectivity = self.check_connectivity()
        
        if connectivity['status'] == 'connected':
            performance = self.check_performance()
            
            # Calculate average response time
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            return {
                'status': 'healthy' if connectivity['status'] == 'connected' else 'unhealthy',
                'connectivity': connectivity,
                'performance': performance,
                'metrics': {
                    'avg_response_time': round(avg_response_time, 3),
                    'max_response_time': round(max(self.response_times), 3) if self.response_times else 0,
                    'min_response_time': round(min(self.response_times), 3) if self.response_times else 0,
                    'total_checks': len(self.response_times)
                },
                'last_check': self.last_check.isoformat() if self.last_check else None
            }
        else:
            return {
                'status': 'unhealthy',
                'connectivity': connectivity,
                'error': connectivity.get('error', 'Unknown database error'),
                'last_check': self.last_check.isoformat() if self.last_check else None
            }
    
    def run_health_check(self):
        """Run a complete health check and return results."""
        return self.get_health_status()

# Global instance (will be initialized with db session)
db_health_checker = None

def init_db_health_checker(db_session):
    """Initialize the database health checker with a session."""
    global db_health_checker
    db_health_checker = DatabaseHealthChecker(db_session)
    return db_health_checker 