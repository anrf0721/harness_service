"""
author: anrf
date:9/17/2026
desc:
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.models.models import RealtimeOutbox


class RealtimeOutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, event: RealtimeOutbox):
        self.session.add(event)

    async def find_next_unpublished(self):
        return await self.session.scalar(
            select(RealtimeOutbox)
            .where(RealtimeOutbox.published_at.is_(None))
            .order_by(RealtimeOutbox.sequence)
            .limit(1)
        )