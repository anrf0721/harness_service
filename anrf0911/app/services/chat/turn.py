"""
author: anrf
date:9/14/2026
desc:
"""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911.app.repositories.conversation import ConversationRepository
from anrf0911.app.repositories.messages import MessageRepository
from anrf0911.app.repositories.turn import ConversationTurnRepository
from anrf0911.common.config import get_settings
from anrf0911.common.utils import get_utcnow
from anrf0911.models.models import Conversation, Message, ConversationTurn


class TurnService:
    def __init__(self,session: AsyncSession):
        self.session = session
        self.turn_repo = ConversationTurnRepository(session)
        self.message_repo = MessageRepository(session)
        self.conversation_repo = ConversationRepository(session)

    async def add_message_to_turn(self,conversation:Conversation,message:Message):
        conversation.input_revision += 1
        message.input_revision = conversation.input_revision

        now = get_utcnow()
        settings = get_settings()
        delay = timedelta(milliseconds=settings.message_merge_delay_ms)
        max_wait = timedelta(milliseconds=settings.message_merge_max_wait_ms)

        turn = await self.turn_repo.find_and_lock_collectin(conversation.id)
        if turn is not None:
            turn.collect_until = min(now+delay,turn.max_collect_until)

        else:
            turn = ConversationTurn(conversation_id=conversation.id,
                                    user_id=conversation.user_id,
                                    start_revision=conversation.answered_revision+1,
                                    collect_until=now+delay,
                                    max_collect_until=now+max_wait,
                                    )
            self.turn_repo.add(turn)
        return turn

    async def claim_turn(self,worker_id):
        turn = await self.turn_repo.find_claimable()
        if turn is None:
            return turn
        conversation = await self.conversation_repo.get_conversation(turn.conversation_id)
        now = get_utcnow()
        settings = get_settings()

        turn.status = 'RUNNING'
        turn.snapshot_revision = conversation.input_revision
        turn.locked_by = worker_id
        turn.locked_until = now + timedelta(seconds=settings.ai_worker_lease_seconds)
        turn.attempts += 1
        if turn.started_at is None:
            turn.started_at = now

        await self.session.commit()
        return turn

    async def build_agent_request(self,turn:ConversationTurn):
        current_messages = await self.message_repo.list_user_messages_in_revision(
            turn.conversation_id,
            turn.start_revision,
            turn.snapshot_revision,
        )
        if not current_messages:
            raise Exception('本轮没有用户消息')

        history = await self.message_repo.list_history_before(turn.conversation_id,current_messages[0].id)

        payload = {
            'conversation_id': turn.conversation_id,
            'user_id': turn.user_id,
            'turn_id': turn.id,
            'request_id': f'{turn.id}:attempt:{turn.attempts}',
            'input_revision': turn.snapshot_revision,
            'messages': [
                {
                    'message_id': m.message_id,
                    'type': m.message_type,
                    'content': m.content,
                }
                for m in current_messages
            ],
            'history':[
                {
                    "message_id": m.message_id,
                    "role": m.role,
                    "type": m.message_type,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in history
            ],
        }
        return payload,current_messages[-1].message_id

    def retry_or_fail(self,turn:ConversationTurn,error:Exception):
        turn.last_error = str(error)
        turn.locked_by = None
        turn.locked_until = None

        settings = get_settings()
        if turn.attempts < settings.ai_worker_max_attempts:
            turn.status = 'COLLECTING'
            turn.collect_until = get_utcnow() + timedelta(seconds=2)
            turn.run_id = None
            # turn.attempts += 1
            return turn

        turn.status = 'FAILED'
        turn.finished_at = get_utcnow()
        return turn

    async def recover_expired(self):
        turns = await self.turn_repo.list_expired_running()
        for turn in turns:
            conversation = await self.conversation_repo.get_conversation(turn.conversation_id)
            if conversation.input_revision != turn.snapshot_revision:
                turn.status = 'SUPERSEDED'
                turn.locked_by = None
                turn.locked_until = None
                turn.run_id = None
                turn.finished_at = get_utcnow()
            else :
                self.retry_or_fail(turn,Exception('租约超时'))
        if turns:
            await self.session.commit()

    async def retry_failed_turn(self, turn_id: str, error: Exception):
        turn = await self.turn_repo.find_and_lock_by_id(turn_id)
        self.retry_or_fail(turn, error)
        await self.session.commit()

