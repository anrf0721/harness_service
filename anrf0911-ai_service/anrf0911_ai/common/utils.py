"""
author: anrf
date:9/18/2026
desc:
"""
import asyncio
import selectors
from datetime import datetime, UTC
from uuid import uuid4


def get_utcnow() -> datetime:
    return datetime.now(UTC)


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def run_async(coroutine):
    return asyncio.run(
        coroutine,
        loop_factory=lambda: asyncio.SelectorEventLoop(
            selectors.SelectSelector()
        ),
    )
