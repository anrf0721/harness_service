"""
author: anrf
date:9/12/2026
desc:
"""
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from anrf0911.common.utils import get_utcnow
from anrf0911.models.models import ConversationTurn, Conversation




class ConversationTurnRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_and_lock_collectin(self, conversation_id: str) :
        return await self.session.scalar(
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id == conversation_id,
                ConversationTurn.status == 'COLLECTING',
            )
            .with_for_update()
        )

    def add(self,turn: ConversationTurn):
        self.session.add(turn)

    async def find_claimable(self):
        now = get_utcnow()
        running = aliased(ConversationTurn)
        result = await self.session.scalar(
            select(ConversationTurn).join(
                Conversation,
                ConversationTurn.conversation_id == Conversation.id,
            )
            .where(
                ConversationTurn.status == 'COLLECTING',
                ConversationTurn.collect_until <= now,
                Conversation.mode == 'AI',
                ~exists(
                    select(1).where(
                        ConversationTurn.conversation_id == running.conversation_id,
                        running.status == 'RUNNING',
                        #同一张表必须用别名
                    )
                )
            )
            .order_by(
                ConversationTurn.collect_until.asc(),
            )
            .limit(1)
            .with_for_update()
        )
        return result

    async def list_expired_running(self):
        now = get_utcnow()
        result = await self.session.scalars(
            select(ConversationTurn).where(
                ConversationTurn.status == 'RUNNING',
                ConversationTurn.locked_until <= now,
            )
        )
        return list(result.all())

    async def find_and_lock_by_id(self, turn_id: str):
        return await self.session.get(
            ConversationTurn, turn_id, with_for_update=True
        )