"""
WebSocket Routes for Real-time Updates
"""
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from .manager import websocket_manager, MessageType
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    connection_id: Optional[str] = Query(None)
):
    """Main WebSocket endpoint for real-time updates"""
    
    # Generate connection ID if not provided
    if not connection_id:
        connection_id = str(uuid.uuid4())
    
    await websocket_manager.connect(websocket, connection_id, user_id)
    
    try:
        # Send initial connection success message
        await websocket_manager.send_personal_message({
            'type': 'connection_established',
            'data': {
                'connection_id': connection_id,
                'user_id': user_id,
                'available_topics': [
                    'claims',
                    'repositories', 
                    'dashboard',
                    'activities'
                ]
            }
        }, connection_id)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(message, connection_id)
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message({
                    'type': 'error',
                    'data': {'message': 'Invalid JSON format'}
                }, connection_id)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket_manager.send_personal_message({
                    'type': 'error',
                    'data': {'message': 'Internal server error'}
                }, connection_id)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        websocket_manager.disconnect(connection_id)

async def handle_websocket_message(message: dict, connection_id: str):
    """Handle incoming WebSocket messages from clients"""
    
    message_type = message.get('type')
    data = message.get('data', {})
    
    if message_type == 'subscribe':
        # Subscribe to a topic
        topic = data.get('topic')
        if topic:
            websocket_manager.subscribe(connection_id, topic)
            await websocket_manager.send_personal_message({
                'type': 'subscription_confirmed',
                'data': {'topic': topic}
            }, connection_id)
    
    elif message_type == 'unsubscribe':
        # Unsubscribe from a topic
        topic = data.get('topic')
        if topic:
            websocket_manager.unsubscribe(connection_id, topic)
            await websocket_manager.send_personal_message({
                'type': 'unsubscription_confirmed',
                'data': {'topic': topic}
            }, connection_id)
    
    elif message_type == 'ping':
        # Handle ping messages for connection health check
        await websocket_manager.send_personal_message({
            'type': 'pong',
            'data': data
        }, connection_id)
    
    elif message_type == 'get_stats':
        # Return connection statistics
        stats = websocket_manager.get_stats()
        await websocket_manager.send_personal_message({
            'type': 'stats',
            'data': stats
        }, connection_id)
    
    else:
        await websocket_manager.send_personal_message({
            'type': 'error',
            'data': {'message': f'Unknown message type: {message_type}'}
        }, connection_id)

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return websocket_manager.get_stats()