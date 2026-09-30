"""
author: anrf
date:9/17/2026
desc:
"""
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.repositories.conversation import ConversationRepository
from anrf0911.app.repositories.handoff import HandoffRepository
from anrf0911.app.repositories.messages import MessageRepository
from anrf0911.app.services.realtime import RealtimeService
from anrf0911.common.utils import get_utcnow, get_uid
from anrf0911.models.models import Conversation, Handoff, Message


class HandoffService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.handoff_repo = HandoffRepository(session)
        self.message_repo = MessageRepository(session)
        self.conversation_repo = ConversationRepository(session)
        self.realtime_service = RealtimeService(session)

    async def get_or_create_open_handoff(self, conversation: Conversation, summary: str):
        handoff = await self.handoff_repo.find_open_by_user_id(conversation.user_id)
        if handoff is not None:
            handoff.summary = summary
            return handoff

        handoff = Handoff(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,
            status='waiting',
        )
        self.handoff_repo.add(handoff)
        await self.session.flush()
        return handoff

    async def list_open_handoffs(self):
        return await self.handoff_repo.list_open()

    async def accept_handoff(self, handoff_id: str, agent_id: str):
        handoff = await self.handoff_repo.find_and_lock_by_id(handoff_id)
        if handoff is None:
            raise HTTPException(status_code=404, detail='工单不存在')
        if handoff.status == 'resolved':
            raise HTTPException(status_code=400, detail='工单已结束')
        if handoff.status == 'active':
            if handoff.assigned_agent_id != agent_id:
                raise HTTPException(status_code=403, detail='工单不属于当前客服')
            return

        conversation = await self.conversation_repo.find_and_lock_by_id(
            handoff.conversation_id
        )
        handoff.status = 'active'
        handoff.assigned_agent_id = agent_id
        handoff.accepted_at = get_utcnow()
        conversation.mode = 'HUMAN'
        self.realtime_service.emit_handoff(
            f'user:{handoff.user_id}',
            'handoff_accepted',
            conversation.id,
            handoff,
        )
        self.realtime_service.emit_handoff(
            'staff',
            'handoff_accepted',
            conversation.id,
            handoff,
        )
        await self.session.commit()

    async def reply_to_handoff(self, handoff_id: str, agent_id: str, message_id: str, text: str):
        handoff = await self.handoff_repo.find_and_lock_by_id(handoff_id)
        if handoff is None:
            raise HTTPException(status_code=404, detail='工单不存在')
        if handoff.status != 'active' or handoff.assigned_agent_id != agent_id:
            raise HTTPException(status_code=403, detail='工单不属于当前客服')

        await self.conversation_repo.find_and_lock_by_id(handoff.conversation_id)

        duplicate = await self.message_repo.find_with_conversation_by_message_id(message_id)
        if duplicate is not None:
            return

        message = Message(
            message_id=message_id,
            conversation_id=handoff.conversation_id,
            role='human',
            message_type='text',
            content={'text': text},
        )
        self.message_repo.add(message)
        self.realtime_service.emit_message_created(
            f'user:{handoff.user_id}',
            handoff.conversation_id,
            message,
        )
        self.realtime_service.emit_message_created(
            'staff',
            handoff.conversation_id,
            message,
        )
        await self.session.commit()

    async def resolve_handoff(self, handoff_id: str, agent_id: str, resolution: str):
        handoff = await self.handoff_repo.find_and_lock_by_id(handoff_id)
        if handoff is None:
            raise HTTPException(status_code=404, detail='工单不存在')
        if handoff.status != 'active' or handoff.assigned_agent_id != agent_id:
            raise HTTPException(status_code=403, detail='工单不属于当前客服')

        conversation = await self.conversation_repo.find_and_lock_by_id(
            handoff.conversation_id
        )
        handoff.status = 'resolved'
        handoff.resolved_at = get_utcnow()
        conversation.mode = 'AI'

        message = Message(
            message_id=get_uid('msg'),
            conversation_id=conversation.id,
            role='human',
            message_type='text',
            content={'text': resolution},
        )
        self.message_repo.add(message)
        self.realtime_service.emit_message_created(
            f'user:{handoff.user_id}',
            conversation.id,
            message,
        )
        self.realtime_service.emit_handoff(
            f'user:{handoff.user_id}',
            'handoff_resolved',
            conversation.id,
            handoff,
        )
        self.realtime_service.emit_handoff(
            'staff',
            'handoff_resolved',
            conversation.id,
            handoff,
        )
        await self.session.commit()
