"""
author: anrf
date:9/14/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Header, Query

from anrf0911.app.dependencies import ChatMessageServiceDep, AuthServiceDep, ConversationServiceDep
from anrf0911.app.schemas.messages import AcceptUserMessageResponse, ChatMessageRequest

router = APIRouter(prefix='/api/v1/chat',tags=['用户消息'])

@router.post('/messages',response_model=AcceptUserMessageResponse)
async def accept_user_message(
        chat_message:ChatMessageRequest,
        message_service: ChatMessageServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str|None,Header()] = None
):
    current_user = auth_service.get_authorized_user(authorization,'customer')
    return await message_service.accept_user_message(user_id=current_user.user_id,chat_message=chat_message)


@router.get('/history')
async def list_chat_history(
        conversation_service: ConversationServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str | None, Header()] = None,
        after_sequence: Annotated[int | None, Query()] = None,
):
    current_user = auth_service.get_authorized_user(authorization, 'customer')
    return await conversation_service.list_chat_history(current_user.user_id, after_sequence)
