"""
author: anrf
date:9/18/2026
desc:
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from anrf0911.app.infrastructure.redis import redis_client
from anrf0911.app.services.auth import AuthService

router = APIRouter()
auth_service = AuthService()

@router.websocket('/api/v1/realtime')
async def realtime_socket(websocket: WebSocket):
    await websocket.accept()

    auth_message = await websocket.receive_json()
    current_user = auth_service.get_current_user(
        f'Bearer {auth_message["token"]}'
    )

    channel = (
        f'user:{current_user.user_id}'
        if current_user.role == 'customer'
        else 'staff'
    )

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    await websocket.send_json({'type': 'connected'})

    async def forward_events():
        async for item in pubsub.listen():
            if item['type'] == 'message':
                await websocket.send_text(item['data'])

    asyncio.create_task(forward_events())

    while True:
        message = await websocket.receive_json()
        if message.get('type') == 'ping':
            await websocket.send_json({'type': 'pong'})