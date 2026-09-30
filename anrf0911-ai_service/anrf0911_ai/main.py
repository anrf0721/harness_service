"""
author: anrf
date:9/18/2026
desc:
"""
import uvicorn

from anrf0911_ai.common.config import get_settings
from anrf0911_ai.common.utils import run_async


async def serve():
    settings = get_settings()
    server = uvicorn.Server(
        uvicorn.Config(
            app="anrf0911_ai.app.app:app",
            host=settings.api_host,
            port=settings.api_port,
            loop="none",
        )
    )
    await server.serve()


if __name__ == "__main__":
    run_async(serve())
