"""
author: anrf
date:9/11/2026
desc:
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.services.auth import AuthService
from anrf0911.app.services.chat.conversation import ConversationService
from anrf0911.app.infrastructure.db import get_db
from anrf0911.app.services.chat.message import ChatMessageService
from anrf0911.app.services.chat.turn import TurnService
from anrf0911.app.services.handoff import HandoffService


def get_auth_service():
    return AuthService()

def get_conversation_service(session: Annotated[AsyncSession,Depends(get_db)]):
    return ConversationService(session)



AuthServiceDep = Annotated[AuthService,Depends(get_auth_service)]
ConversationServiceDep = Annotated[ConversationService,Depends(get_conversation_service)]

def get_chat_message_service(conversation_service: ConversationServiceDep,session: Annotated[AsyncSession,Depends(get_db)]):
    return ChatMessageService(session,conversation_service,TurnService(session))


ChatMessageServiceDep = Annotated[ChatMessageService,Depends(get_chat_message_service)]

def get_handoff_service(session: Annotated[AsyncSession, Depends(get_db)]):
    return HandoffService(session)


HandoffServiceDep = Annotated[HandoffService, Depends(get_handoff_service)]