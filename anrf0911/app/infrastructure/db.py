"""
author: anrf
date:9/11/2026
desc:
"""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from anrf0911.common.config import get_settings
from anrf0911.common.event_loop import run_async

db_engine = create_async_engine(
    url = get_settings().database_url,
    echo=False,
)
SessionFactory = async_sessionmaker(
    bind=db_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    """ORM 数据库模型的声明性基类。"""
    pass

async def get_db():
    async with SessionFactory() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise

async def get_db_session_test():
    async for db in get_db():
        result = await db.execute(text('select 1'))
        return result

if __name__ == '__main__':
    res = run_async(get_db_session_test())
    print(res)
