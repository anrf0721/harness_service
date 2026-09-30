"""
author: anrf
date:9/17/2026
desc:
"""
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.repositories.outbox import RealtimeOutboxRepository
from anrf0911.models.models import Message, RealtimeOutbox


class RealtimeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.outbox_repo = RealtimeOutboxRepository(session)

    def emit(self, channel: str, event_type: str, conversation_id: str | None, data: dict):
        self.outbox_repo.add(RealtimeOutbox(
            channel=channel,
            event_type=event_type,
            conversation_id=conversation_id,
            data=data,
        ))

    def emit_message_created(self, channel: str, conversation_id: str, message: Message):
        self.emit(
            channel,
            'message_created',
            conversation_id,
            {
                'message': {
                    'message_id': message.message_id,
                    'role': message.role,
                    'content': message.content,
                }
            },
        )

    def emit_handoff(self, channel: str, event_type: str, conversation_id: str, handoff):
        self.emit(
            channel,
            event_type,
            conversation_id,
            {
                'handoff_id': handoff.id,
                'status': handoff.status,
                'summary': handoff.summary,
                'agent_id': handoff.assigned_agent_id,
            },
        )
