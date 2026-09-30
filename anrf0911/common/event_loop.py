"""
author: anrf
date:9/11/2026
desc:
"""
import asyncio
import selectors

def run_async(coroutine):
    return asyncio.run(
        coroutine,
        loop_factory=lambda: asyncio.SelectorEventLoop(
            selectors.SelectSelector()
        ),
    )