"""
author: anrf
date:9/11/2026
desc:
"""
import anrf0911.models.models  # noqa: F401
from anrf0911.common.event_loop import run_async
from anrf0911.app.infrastructure.db import Base, db_engine


async def init_db():
    async with db_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    run_async(init_db())
