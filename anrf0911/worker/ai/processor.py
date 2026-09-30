"""
author: anrf
date:9/16/2026
desc:
"""
from anrf0911.app.infrastructure.db import SessionFactory
from anrf0911.app.schemas.user import CurrentUser
from anrf0911.app.services.ai.result import AIResultService
from anrf0911.app.services.auth import AuthService
from anrf0911.app.services.chat.turn import TurnService
from anrf0911.models.models import ConversationTurn
from anrf0911.worker.ai.gateway import AIServiceGateway
from anrf0911.worker.ai.parser import parse_event


class TurnProcessor:
    def __init__(self):
        self.auth = AuthService()
        self.gateway = AIServiceGateway()

    async def process_turn(self, turn:ConversationTurn,payload:dict):
        try:
            token = self.auth.encode_access_token(
                CurrentUser(user_id=turn.user_id,role='customer')
            )
            body = await self.gateway.start_run(token,payload)
            event_data = parse_event(body)

            async with SessionFactory() as session:
                result_service = AIResultService(session)
                await result_service.save_ai_reply(turn,event_data)
        except Exception as e:
            async with SessionFactory() as session:
                await TurnService(session).retry_failed_turn(turn.id, e)

