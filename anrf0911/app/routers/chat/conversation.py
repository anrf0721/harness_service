"""
author: anrf
date:9/11/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Header

from anrf0911.app.dependencies import ConversationServiceDep, AuthServiceDep
from anrf0911.app.schemas.conversation import CurrentConversationResponse, ConversationDetailResponse

router = APIRouter(prefix="/api/v1", tags=["聊天会话路由"])


@router.post("/conversations/current", response_model=CurrentConversationResponse)
async def get_current_conversation(
    conversation_service: ConversationServiceDep,
    auth_service: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
):
    current_user = auth_service.get_authorized_user(authorization, "customer")
    return await conversation_service.get_current_conversation(current_user.user_id)

@router.get("/conversations/{conversation_id}",response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: str,
    conversation_service: ConversationServiceDep,
    auth_service: AuthServiceDep,
    authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, "agent",'admin')
    return await conversation_service.get_conversation_detail(conversation_id)