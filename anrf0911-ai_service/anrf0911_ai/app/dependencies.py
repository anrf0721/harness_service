"""
author: anrf
date:9/18/2026
desc:
"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException,Request
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911_ai.agent.coordinator import AgentRunCoordinator
from anrf0911_ai.agent.executor import AgentExecutor
from anrf0911_ai.app.db import get_db
from anrf0911_ai.app.services.auth import AuthService
from anrf0911_ai.common.config import get_settings

SessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_auth_service():
    return AuthService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def require_internal_service(
        token: Annotated[str | None, Header(alias="X-Internal-Service-Token")] = None,
):
    if token != get_settings().internal_service_token:
        raise HTTPException(status_code=403, detail="内部服务令牌无效")

def get_agent_executor(request: Request):
    return AgentExecutor(agent=request.app.state.agent)

def get_agent_run_coordinator(session: SessionDep,executor: Annotated[AgentExecutor,Depends(get_agent_executor)]):
    return AgentRunCoordinator(session,executor)


AgentRunCoordinatorDep = Annotated[
    AgentRunCoordinator,
    Depends(get_agent_run_coordinator),
]



