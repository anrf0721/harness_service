"""
author: anrf
date:9/18/2026
desc:
"""
import asyncio
import json

from anrf0911.app.infrastructure.db import SessionFactory
from anrf0911.app.infrastructure.redis import redis_client
from anrf0911.app.repositories.outbox import RealtimeOutboxRepository
from anrf0911.common.event_loop import run_async
from anrf0911.common.utils import get_utcnow


class OutboxWorker:
    async def start(self):
        while True:
            published = await self.publish_next()
            if not published:
                await asyncio.sleep(0.5)

    async def publish_next(self):
        async with SessionFactory() as session:
            repo = RealtimeOutboxRepository(session)
            event = await repo.find_next_unpublished()
            if event is None:
                return False

            payload = json.dumps(
                {
                    'type': event.event_type,
                    'data': event.data,
                    'conversation_id': event.conversation_id,
                },
                ensure_ascii=False,
            )
            await redis_client.publish(event.channel, payload)
            event.published_at = get_utcnow()
            await session.commit()
            return True


if __name__ == '__main__':
    run_async(OutboxWorker().start())
