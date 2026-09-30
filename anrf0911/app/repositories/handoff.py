"""
author: anrf
date:9/17/2026
desc:
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.models.models import Handoff


class HandoffRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, handoff: Handoff):
        self.session.add(handoff)

    async def find_open_by_user_id(self, user_id: str):
        return await self.session.scalar(
            select(Handoff).where(
                Handoff.user_id == user_id,
                Handoff.status.in_(["waiting", "active"]),
            )
        )

    async def list_open(self):
        result = await self.session.scalars(
            select(Handoff)
            .where(Handoff.status.in_(["waiting", "active"]))
            .order_by(Handoff.created_at)
        )
        return list(result.all())

    async def find_and_lock_by_id(self, handoff_id: str):
        return await self.session.scalar(
            select(Handoff)
            .where(Handoff.id == handoff_id)
            .with_for_update()
        )
