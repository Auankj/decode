"""
WebSocket Connection Manager for Real-time Updates
Handles WebSocket connections and broadcasts updates to clients
"""
import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        # Store active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Store subscriptions by topic
        self.subscriptions: Dict[str, Set[str]] = {}
        # Store connection metadata
        self.connection_metadata: Dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'connected_at': datetime.utcnow().isoformat(),
            'subscriptions': set()
        }
        logger.info(f"WebSocket connection {connection_id} established (user: {user_id})")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            # Remove from all subscriptions
            for topic in list(self.subscriptions.keys()):
                self.subscriptions[topic].discard(connection_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
            
            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_metadata[connection_id]
            logger.info(f"WebSocket connection {connection_id} disconnected")
    
    def subscribe(self, connection_id: str, topic: str):
        """Subscribe a connection to a topic"""
        if connection_id in self.active_connections:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(connection_id)
            self.connection_metadata[connection_id]['subscriptions'].add(topic)
            logger.debug(f"Connection {connection_id} subscribed to {topic}")
    
    def unsubscribe(self, connection_id: str, topic: str):
        """Unsubscribe a connection from a topic"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(connection_id)
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
        
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['subscriptions'].discard(topic)
        logger.debug(f"Connection {connection_id} unsubscribed from {topic}")
    
    async def send_personal_message(self, message: dict, connection_id: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def broadcast_to_topic(self, message: dict, topic: str):
        """Broadcast a message to all subscribers of a topic"""
        if topic in self.subscriptions:
            connections_to_remove = []
            
            for connection_id in self.subscriptions[topic]:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        logger.error(f"Error broadcasting to {connection_id}: {e}")
                        connections_to_remove.append(connection_id)
                else:
                    connections_to_remove.append(connection_id)
            
            # Remove failed connections
            for connection_id in connections_to_remove:
                self.disconnect(connection_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections"""
        connections_to_remove = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {connection_id}: {e}")
                connections_to_remove.append(connection_id)
        
        # Remove failed connections
        for connection_id in connections_to_remove:
            self.disconnect(connection_id)
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            'active_connections': len(self.active_connections),
            'topics': list(self.subscriptions.keys()),
            'subscriptions_by_topic': {
                topic: len(connections) 
                for topic, connections in self.subscriptions.items()
            }
        }

# Global connection manager instance
websocket_manager = ConnectionManager()

# Message types for different events
class MessageType:
    # Claim events
    CLAIM_CREATED = "claim_created"
    CLAIM_UPDATED = "claim_updated" 
    CLAIM_RELEASED = "claim_released"
    CLAIM_COMPLETED = "claim_completed"
    
    # Repository events
    REPOSITORY_ADDED = "repository_added"
    REPOSITORY_UPDATED = "repository_updated"
    REPOSITORY_REMOVED = "repository_removed"
    
    # Activity events
    ACTIVITY_CREATED = "activity_created"
    
    # System events
    NUDGE_SENT = "nudge_sent"
    SYSTEM_ALERT = "system_alert"
    
    # Dashboard updates
    DASHBOARD_STATS_UPDATED = "dashboard_stats_updated"

# Helper functions for broadcasting specific events
async def broadcast_claim_update(claim_data: dict, event_type: str):
    """Broadcast claim-related updates"""
    message = {
        'type': event_type,
        'data': claim_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # Broadcast to general claims topic
    await websocket_manager.broadcast_to_topic(message, 'claims')
    
    # Broadcast to specific repository topic if available
    if 'repository_id' in claim_data:
        repo_topic = f"repository_{claim_data['repository_id']}"
        await websocket_manager.broadcast_to_topic(message, repo_topic)

async def broadcast_repository_update(repo_data: dict, event_type: str):
    """Broadcast repository-related updates"""
    message = {
        'type': event_type,
        'data': repo_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await websocket_manager.broadcast_to_topic(message, 'repositories')
    
    # Also broadcast to specific repository topic
    if 'id' in repo_data:
        repo_topic = f"repository_{repo_data['id']}"
        await websocket_manager.broadcast_to_topic(message, repo_topic)

async def broadcast_dashboard_update(stats_data: dict):
    """Broadcast dashboard statistics updates"""
    message = {
        'type': MessageType.DASHBOARD_STATS_UPDATED,
        'data': stats_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await websocket_manager.broadcast_to_topic(message, 'dashboard')

async def broadcast_system_alert(alert_message: str, severity: str = 'info'):
    """Broadcast system alerts"""
    message = {
        'type': MessageType.SYSTEM_ALERT,
        'data': {
            'message': alert_message,
            'severity': severity
        },
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await websocket_manager.broadcast_to_all(message)