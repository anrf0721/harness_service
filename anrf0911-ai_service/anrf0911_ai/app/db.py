"""
author: anrf
date:9/18/2026
desc: 数据库连接、会话和 ORM 基类，不负责加载模型或建表。
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from anrf0911_ai.common.config import get_settings

db_engine = create_async_engine(
    url=get_settings().database_url,
    echo=True,
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
