"""
author: anrf
date:9/14/2026
desc:
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.repositories.messages import MessageRepository
from anrf0911.app.schemas.messages import ChatMessageRequest
from anrf0911.app.services.chat.conversation import ConversationService
from anrf0911.app.services.chat.turn import TurnService
from anrf0911.app.services.realtime import RealtimeService
from anrf0911.common.utils import get_utcnow
from anrf0911.models.models import Conversation, Message


class ChatMessageService:
    def __init__(self,session:AsyncSession,conversation_service:ConversationService,turn_service:TurnService):
        self.session = session
        self.conversation_service = conversation_service
        self.turn_service = turn_service
        self.message_repo = MessageRepository(session)
        self.realtime_service = RealtimeService(session)

    def add_message(self
                    ,conversation:Conversation
                    ,content:dict
                    ,message_id: str
                    ,message_type:str = 'text'
                    ):
        message = Message(
            message_id=message_id,
            conversation_id=conversation.id,
            role = 'user',
            message_type=message_type,
            content=content,
        )
        self.message_repo.add(message)
        conversation.last_active_at = get_utcnow()
        return message

    async def accept_user_message(self,user_id:str,chat_message:ChatMessageRequest):
        duplicate = await self.message_repo.find_with_conversation_by_message_id(chat_message.message_id)
        if duplicate is not None:
            msg,conversation = duplicate
            if conversation.user_id != user_id:
                raise HTTPException(status_code=404,detail="会话不存在")
            return {'conversation_id':conversation.id,'mode':conversation.mode}

        conversation = await self.conversation_service.ensure_locked_active_conversation(user_id)
        message = self.add_message(
            conversation,
            chat_message.content,
            chat_message.message_id,
            chat_message.type,
        )
        if conversation.mode == 'AI':
            await self.turn_service.add_message_to_turn(conversation,message)
        elif conversation.mode in ('QUEUED', 'HUMAN'):
            self.realtime_service.emit_message_created(
                'staff',
                conversation.id,
                message,
            )

        await self.session.commit()
        return {'conversation_id':conversation.id,'mode':conversation.mode}