"""
author: anrf
date:9/15/2026
desc:
"""
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.repositories.conversation import ConversationRepository
from anrf0911.app.repositories.messages import MessageRepository
from anrf0911.app.repositories.turn import ConversationTurnRepository
from anrf0911.app.services.handoff import HandoffService
from anrf0911.app.services.realtime import RealtimeService
from anrf0911.common.utils import get_utcnow, get_uid
from anrf0911.models.models import ConversationTurn, Message


class AIResultService:
    def __init__(self,session:AsyncSession):
        self.session = session
        self.message_repo = MessageRepository(session)
        self.turn_repo = ConversationTurnRepository(session)
        self.conversation_repo = ConversationRepository(session)
        self.handoff_service = HandoffService(session)
        self.realtime_service = RealtimeService(session)


    async def save_ai_reply(self,turn:ConversationTurn,event_data:dict):
        turn = await self.turn_repo.find_and_lock_by_id(turn.id)
        conversation = await self.conversation_repo.find_and_lock_by_id(
            turn.conversation_id
        )
        now = get_utcnow()
        turn.locked_by = None
        turn.locked_until = None
        turn.finished_at = now

        if conversation.input_revision != turn.snapshot_revision:
            turn.status = 'SUPERSEDED'
            await  self.session.commit()
            return turn

        turn.status = 'COMPLETED'
        turn.run_id = event_data.get("run_id")

        if event_data.get('outcome_type') == 'handoff':
            handoff = await self.handoff_service.get_or_create_open_handoff(
                conversation,
                event_data['summary'],
            )
            conversation.mode = (
                'HUMAN' if handoff.status == 'active' else 'QUEUED'
            )

        message = Message(
            message_id=event_data.get("message_id") or get_uid('msg'),
            conversation_id=conversation.id,
            role='ai',
            message_type='text',
            content=event_data.get("content") or {'text':''},
            agent_run_id=turn.run_id,
            agent_outcome_seq=1,
        )

        self.message_repo.add(message)
        conversation.answered_revision = turn.snapshot_revision

        self.realtime_service.emit_message_created(
            f'user:{conversation.user_id}',
            conversation.id,
            message,
        )
        if event_data.get('outcome_type') == 'handoff' and conversation.mode == 'QUEUED':
            self.realtime_service.emit_handoff(
                f'user:{conversation.user_id}',
                'handoff_requested',
                conversation.id,
                handoff,
            )
            self.realtime_service.emit_handoff(
                'staff',
                'handoff_created',
                conversation.id,
                handoff,
            )


        await self.session.commit()
        return message