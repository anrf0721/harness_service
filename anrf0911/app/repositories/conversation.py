"""
author: anrf
date:9/12/2026
desc:
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.models.models import Conversation

ACTIVE_MODES = ('AI','HUMAN','QUEUED')

class ConversationRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_ai_conversation(self, user_id):
        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id,Conversation.mode == 'AI')
        )
        return list(result.scalars().all())


    async def find_activate_conversation(self, user_id: str):
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id,Conversation.mode.in_(ACTIVE_MODES))
            .order_by(Conversation.last_active_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    def add(self, conversation: Conversation):
        """
        不是io操作,只注册会话,同步
        :param conversation:
        :return:
        """
        self.session.add(conversation)

    async def get_conversation(self, conversation_id):
        return await self.session.get(Conversation, conversation_id)

    async def find_and_lock_by_id(self, conversation_id: str):
        return await self.session.get(
            Conversation, conversation_id, with_for_update=True
        )
