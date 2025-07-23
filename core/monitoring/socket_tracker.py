"""
Socket.IO connection tracking for monitoring active WebSocket connections.
"""

import threading
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger

class SocketConnectionTracker:
    """Track Socket.IO connections and provide metrics."""
    
    def __init__(self):
        self.active_connections = {}  # sid -> connection_info
        self.connection_history = []  # List of connection events
        self.connection_stats = defaultdict(int)  # Stats by event type
        self.lock = threading.Lock()
    
    def on_connect(self, sid, environ=None):
        """Track new connection."""
        with self.lock:
            connection_info = {
                'sid': sid,
                'connected_at': datetime.now(),
                'ip_address': environ.get('REMOTE_ADDR', 'unknown') if environ else 'unknown',
                'user_agent': environ.get('HTTP_USER_AGENT', 'unknown') if environ else 'unknown',
                'last_activity': datetime.now(),
                'events_sent': 0,
                'events_received': 0
            }
            self.active_connections[sid] = connection_info
            self.connection_history.append({
                'event': 'connect',
                'sid': sid,
                'timestamp': datetime.now(),
                'ip_address': connection_info['ip_address']
            })
            self.connection_stats['connects'] += 1
            
            logger.debug(f"Socket.IO connection established: {sid}")
    
    def on_disconnect(self, sid):
        """Track disconnection."""
        with self.lock:
            if sid in self.active_connections:
                connection_info = self.active_connections[sid]
                duration = datetime.now() - connection_info['connected_at']
                
                self.connection_history.append({
                    'event': 'disconnect',
                    'sid': sid,
                    'timestamp': datetime.now(),
                    'duration': duration.total_seconds(),
                    'events_sent': connection_info['events_sent'],
                    'events_received': connection_info['events_received']
                })
                
                del self.active_connections[sid]
                self.connection_stats['disconnects'] += 1
                
                logger.debug(f"Socket.IO connection closed: {sid} (duration: {duration.total_seconds():.1f}s)")
    
    def on_event_sent(self, sid, event_name):
        """Track event sent to client."""
        with self.lock:
            if sid in self.active_connections:
                self.active_connections[sid]['events_sent'] += 1
                self.active_connections[sid]['last_activity'] = datetime.now()
                self.connection_stats['events_sent'] += 1
    
    def on_event_received(self, sid, event_name):
        """Track event received from client."""
        with self.lock:
            if sid in self.active_connections:
                self.active_connections[sid]['events_received'] += 1
                self.active_connections[sid]['last_activity'] = datetime.now()
                self.connection_stats['events_received'] += 1
    
    def get_connection_metrics(self):
        """Get current connection metrics."""
        with self.lock:
            now = datetime.now()
            
            # Calculate connection durations
            connection_durations = []
            for conn in self.active_connections.values():
                duration = now - conn['connected_at']
                connection_durations.append(duration.total_seconds())
            
            # Calculate recent activity (last 5 minutes)
            five_minutes_ago = now - timedelta(minutes=5)
            recent_connections = [
                conn for conn in self.active_connections.values()
                if conn['last_activity'] > five_minutes_ago
            ]
            
            # Get connection history (last 100 events)
            recent_history = self.connection_history[-100:] if self.connection_history else []
            
            return {
                'active_connections': len(self.active_connections),
                'total_connects': self.connection_stats['connects'],
                'total_disconnects': self.connection_stats['disconnects'],
                'total_events_sent': self.connection_stats['events_sent'],
                'total_events_received': self.connection_stats['events_received'],
                'avg_connection_duration': sum(connection_durations) / len(connection_durations) if connection_durations else 0,
                'max_connection_duration': max(connection_durations) if connection_durations else 0,
                'recent_activity': len(recent_connections),
                'connection_details': [
                    {
                        'sid': conn['sid'],
                        'ip_address': conn['ip_address'],
                        'connected_at': conn['connected_at'].isoformat(),
                        'duration': (now - conn['connected_at']).total_seconds(),
                        'events_sent': conn['events_sent'],
                        'events_received': conn['events_received'],
                        'last_activity': conn['last_activity'].isoformat()
                    }
                    for conn in self.active_connections.values()
                ],
                'recent_events': [
                    {
                        'event': event['event'],
                        'timestamp': event['timestamp'].isoformat(),
                        'duration': event.get('duration', 0)
                    }
                    for event in recent_history
                ]
            }
    
    def cleanup_old_history(self, max_history=1000):
        """Clean up old connection history."""
        with self.lock:
            if len(self.connection_history) > max_history:
                self.connection_history = self.connection_history[-max_history:]

# Global instance
socket_tracker = SocketConnectionTracker() 