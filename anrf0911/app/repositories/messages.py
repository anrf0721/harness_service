"""
author: anrf
date:9/12/2026
desc:
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.models.models import Conversation, Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_conversation_messages(self, conversation_id: str) -> list[Message]:
        result = await self.session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id)
        )
        return list(result.all())

    async def find_with_conversation_by_message_id(self, message_id: str):
        result = await self.session.execute(
            select(Message, Conversation)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.message_id == message_id)
        )
        return result.tuples().one_or_none()

    def add(self, message: Message) -> None:
        self.session.add(message)

    async def list_user_messages_in_revision(self,
                                             conversation_id: str,
                                             start_revision: int,
                                             snapshot_revision: int,
                                             ) :
        result = await self.session.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id ,
                Message.role == 'user',
                Message.input_revision >= start_revision,
                Message.input_revision <= snapshot_revision,
            )
            .order_by(Message.id.asc())
        )
        return result.all()

    async def list_history_before(self,
                                  conversation_id: str,
                                  before_id: int,
                                  limit:int = 30,
                                  ):
        result = await self.session.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id ,
                Message.id < before_id,
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
        rows = list(result.all())
        rows.reverse()
        return rows

    async def list_history_for_user(self, user_id: str, after_sequence: int | None = None):
        stmt = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.user_id == user_id)
        )
        if after_sequence is not None:
            stmt = stmt.where(Message.id > after_sequence)
        result = await self.session.scalars(stmt.order_by(Message.id.asc()))
        return list(result.all())

