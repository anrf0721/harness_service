"""
author: anrf
date:9/18/2026
desc:
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.models.models import Conversation, Handoff, Message


class MetricsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_metrics(self):
        conversation_count = await self.session.scalar(
            select(func.count(Conversation.id))
        )
        message_count = await self.session.scalar(
            select(func.count(Message.id))
        )
        handoff_count = await self.session.scalar(
            select(func.count(Handoff.id))
        )
        queued_count = await self.session.scalar(
            select(func.count(Conversation.id))
            .where(Conversation.mode == 'QUEUED')
        )
        human_count = await self.session.scalar(
            select(func.count(Conversation.id))
            .where(Conversation.mode == 'HUMAN')
        )
        return {
            'conversations': conversation_count or 0,
            'messages': message_count or 0,
            'handoffs': handoff_count or 0,
            'queued': queued_count or 0,
            'human': human_count or 0,
        }
