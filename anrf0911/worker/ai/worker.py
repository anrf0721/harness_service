"""
author: anrf
date:9/16/2026
desc:
"""
import asyncio
import os
import socket

from anrf0911.app.infrastructure.db import SessionFactory
from anrf0911.app.services.chat.turn import TurnService
from anrf0911.common.config import get_settings
from anrf0911.common.event_loop import run_async
from anrf0911.worker.ai.processor import TurnProcessor


class AIWorker:
    def __init__(self):
        self.worker_id = f'{socket.gethostname()}:{os.getpid()}'
        self.processor = TurnProcessor()
        self.settings = get_settings()

    async def start(self):
        while True:
            had_work = await self.poll_and_process()
            if not had_work:
                await asyncio.sleep(self.settings.ai_worker_poll_interval_ms / 1000)

    async def poll_and_process(self):
        async with SessionFactory() as session:
            turn_service = TurnService(session)
            await turn_service.recover_expired()
            turn = await turn_service.claim_turn(self.worker_id)
            if turn is None:
                return False
            payload,last_message_id = await turn_service.build_agent_request(turn)
        await self.processor.process_turn(turn, payload)
        return True

if __name__ == '__main__':
    result = run_async(AIWorker().start())