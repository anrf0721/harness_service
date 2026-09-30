"""加载模型并创建数据库表，在 IDE 中直接运行这个文件。"""

from anrf0911_ai.app.db import Base, db_engine
from anrf0911_ai.common.utils import run_async


async def init_db():
    """把模型登记到 Base，再创建数据库中缺少的表。"""
    import anrf0911_ai.models.models  # noqa: F401

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    run_async(init_db())
    print("建表完成")
