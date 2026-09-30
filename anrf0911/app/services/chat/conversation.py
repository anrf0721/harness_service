"""
author: anrf
date:9/11/2026
desc:
"""
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from anrf0911.app.repositories.conversation import ConversationRepository
from anrf0911.app.repositories.messages import MessageRepository
from anrf0911.common.config import get_settings
from anrf0911.common.utils import get_utcnow
from anrf0911.models.models import Conversation, Message


class ConversationService:
    def __init__(self, session:AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)

    async def get_current_conversation(self,user_id:str):
        conversation = await self.ensure_activate_conversation(user_id)
        await self.session.commit()
        return {
            'id' : conversation.id,
            'mode' : conversation.mode,
            'is_processing' : False
                }

    async def ensure_activate_conversation(self,user_id):
        """
        职责:1.当前用户已经超期的会话修改状态为[closed] 2.确保当前用户会话存在
        :param user_id:
        :return:
        """
        # 1.修改已经超时的会话
        await self._close_timeout_conversation(user_id)
        # 2.查询当前用户是否有有效会话
        conversation = await self.conversation_repo.find_activate_conversation(user_id)
        # 3.没找到就新建会话
        if conversation is  None:
            conversation = await self._create_conversation(user_id)
        return conversation

    async def _create_conversation(self,user_id):
        conversation = Conversation(user_id=user_id,mode='AI')
        self.conversation_repo.add(conversation)
        await self.session.flush()
        return conversation

    async def _close_timeout_conversation(self, user_id: str):
        conversations = await self.conversation_repo.list_ai_conversation(user_id)
        changed = False
        for conversation in conversations:
            if await self._has_idle_timeout(conversation):
                conversation.mode = 'CLOSED'
                changed = True
                conversation.ended_at = conversation.last_active_at
        if changed:
            await self.session.flush()


    async def _has_idle_timeout(self,conversation: Conversation):
        now = get_utcnow()
        timeout = timedelta(minutes=get_settings().conversation_timeout)
        return now - conversation.last_active_at >= timeout




    async def get_conversation_detail(self,conversation_id: str):
        conversation = await self.conversation_repo.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404,detail='Conversation not found')

        messages = await self.message_repo.get_conversation_messages(conversation_id)
        return {
            "messages": [self._message_payload(message) for message in messages]
        }

    def _message_payload(self, message: Message) -> dict:
        return {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
        }

    async def list_chat_history(self, user_id: str, after_sequence: int | None = None):
        messages = await self.message_repo.list_history_for_user(user_id, after_sequence)
        return [
            {
                "message_id": message.message_id,
                "conversation_id": message.conversation_id,
                "role": message.role,
                "content": message.content,
                "sequence": message.id,
                "created_at": message.created_at,
            }
            for message in messages
        ]

    async def ensure_locked_active_conversation(self,user_id: str):
        conversation = await self.ensure_activate_conversation(user_id)
        return await self.conversation_repo.find_and_lock_by_id(conversation.id)