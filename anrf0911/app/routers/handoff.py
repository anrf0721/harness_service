"""
author: anrf
date:9/17/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Header, status

from anrf0911.app.dependencies import AuthServiceDep, HandoffServiceDep
from anrf0911.app.schemas.handoff import HandoffReplyRequest, HandoffResolveRequest

router = APIRouter(prefix='/api/v1/handoffs', tags=['人工工单'])

@router.get('')
async def list_handoffs(
        handoff_service: HandoffServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, 'agent')
    items = await handoff_service.list_open_handoffs()
    return [
        {
            'id': item.id,
            'conversation_id': item.conversation_id,
            'user_id': item.user_id,
            'summary': item.summary,
            'status': item.status,
            'assigned_agent_id': item.assigned_agent_id,
            'created_at': item.created_at,
        }
        for item in items
    ]


@router.post('/{handoff_id}/accept', status_code=status.HTTP_204_NO_CONTENT)
async def accept_handoff(
        handoff_id: str,
        handoff_service: HandoffServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str | None, Header()] = None,
):
    agent = auth_service.get_authorized_user(authorization, 'agent')
    await handoff_service.accept_handoff(handoff_id, agent.user_id)

@router.post('/{handoff_id}/messages', status_code=status.HTTP_204_NO_CONTENT)
async def reply_to_handoff(
        handoff_id: str,
        body: HandoffReplyRequest,
        handoff_service: HandoffServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str | None, Header()] = None,
):
    agent = auth_service.get_authorized_user(authorization, 'agent')
    await handoff_service.reply_to_handoff(
        handoff_id,
        agent.user_id,
        body.message_id,
        body.text,
    )

@router.post('/{handoff_id}/resolve', status_code=status.HTTP_204_NO_CONTENT)
async def resolve_handoff(
        handoff_id: str,
        body: HandoffResolveRequest,
        handoff_service: HandoffServiceDep,
        auth_service: AuthServiceDep,
        authorization: Annotated[str | None, Header()] = None,
):
    agent = auth_service.get_authorized_user(authorization, 'agent')
    await handoff_service.resolve_handoff(
        handoff_id,
        agent.user_id,
        body.resolution,
    )