"""
author: anrf
date:9/11/2026
desc:
"""
import uvicorn

from anrf0911.common.config import get_settings
from anrf0911.common.event_loop import run_async


async def serve():
    settings = get_settings()
    server = uvicorn.Server(
        uvicorn.Config(
            app="anrf0911.app.app:app",
            host=settings.api_host,
            port=settings.api_port,
            loop="none",
        )
    )
    await server.serve()


if __name__ == "__main__":
    run_async(serve())
