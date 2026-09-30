"""
author: anrf
date:9/18/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.dependencies import AuthServiceDep
from anrf0911.app.infrastructure.db import get_db
from anrf0911.app.repositories.metrics import MetricsRepository

router = APIRouter(prefix='/api/v1/admin', tags=['管理员'])


@router.get('/metrics')
async def get_admin_metrics(
        auth_service: AuthServiceDep,
        session: Annotated[AsyncSession, Depends(get_db)],
        authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, 'admin')
    return await MetricsRepository(session).get_metrics()
