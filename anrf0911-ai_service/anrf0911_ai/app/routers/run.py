"""
author: anrf
date:9/18/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Header

from anrf0911_ai.app.dependencies import (
    AgentRunCoordinatorDep,
    AuthServiceDep,
    require_internal_service,
)
from anrf0911_ai.app.schemas.run import AgentRunRequest

router = APIRouter(prefix="/internal/v1/agent", tags=["AI Run"])


@router.post("/runs")
async def start_run(
        request: AgentRunRequest,
        auth_service: AuthServiceDep,
        coordinator: AgentRunCoordinatorDep,
        _: Annotated[None, Depends(require_internal_service)],
        authorization: Annotated[str | None, Header()] = None,
) -> dict:
    current_user = auth_service.get_authorized_user(authorization, "customer")
    token = authorization.split(" ",1)[1]
    return await coordinator.start_run(current_user.user_id, request,token)


@router.post("/runs/{run_id}/commit")
async def commit_run(
        run_id: str,
        auth_service: AuthServiceDep,
        coordinator: AgentRunCoordinatorDep,
        _: Annotated[None, Depends(require_internal_service)],
        authorization: Annotated[str | None, Header()] = None,
) -> dict:
    current_user = auth_service.get_authorized_user(authorization, "customer")
    return await coordinator.commit_run(current_user.user_id, run_id)


@router.post("/runs/{run_id}/cancel", status_code=204)
async def cancel_run(
        run_id: str,
        auth_service: AuthServiceDep,
        coordinator: AgentRunCoordinatorDep,
        _: Annotated[None, Depends(require_internal_service)],
        authorization: Annotated[str | None, Header()] = None,
):
    current_user = auth_service.get_authorized_user(authorization, "customer")
    await coordinator.cancel_run(current_user.user_id, run_id)


if __name__ == "__main__":
    import httpx
    from anrf0911_ai.app.services.auth import AuthService, CurrentUser
    from anrf0911_ai.common.config import get_settings

    settings = get_settings()
    token = AuthService().encode_access_token(CurrentUser(user_id="u1", role="customer"))
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Internal-Service-Token": settings.internal_service_token,
    }

    def call(text):
        r = httpx.post(
            "http://127.0.0.1:8002/internal/v1/agent/runs",
            headers=headers,
            json={
                "conversation_id": "c",
                "turn_id": "t",
                "messages": [
                    {"message_id": "m", "type": "text", "content": {"text": text}}
                ],
            },
            timeout=120,
        )
        print(r.status_code, r.text)

    call("你好")
    call("我要转人工客服")