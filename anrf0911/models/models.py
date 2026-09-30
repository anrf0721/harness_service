from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    Identity,
    String,
    Text,
    UniqueConstraint,
    text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from anrf0911.common.utils import get_utcnow, get_uid
from anrf0911.app.infrastructure.db import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "uq_open_conversation_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("mode IN ('AI', 'QUEUED', 'HUMAN')")
        ),
        {"comment": "客服会话"},
    )

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("conv"),
        comment="会话ID",
    )
    user_id: Mapped[str] = mapped_column(String(40), index=True, comment="用户ID")
    mode: Mapped[str] = mapped_column(
        String(20),
        default="AI",
        index=True,
        comment="会话模式：AI/QUEUED/HUMAN/CLOSED",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utcnow, comment="开始时间"
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utcnow,
        onupdate=get_utcnow,
        comment="最后活跃时间",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="结束时间"
    )
    input_revision: Mapped[int] = mapped_column(
        Integer, default=0, comment="用户输入版本号"
    )
    answered_revision: Mapped[int] = mapped_column(
        Integer, default=0, comment="已应答版本号"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    __table_args__ = (
        Index(
            "uq_collecting_turn_per_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status = 'COLLECTING'"),
        ),
        Index(
            "uq_executing_turn_per_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status = 'RUNNING'"),
        ),
        {"comment": "智能处理轮次"},
    )

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("turn"),
        comment="轮次ID",
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True, comment="会话ID"
    )
    user_id: Mapped[str] = mapped_column(String(40), index=True, comment="用户ID")
    status: Mapped[str] = mapped_column(
        String(30),
        default="COLLECTING",
        index=True,
        comment="轮次状态：COLLECTING/RUNNING/COMPLETED/FAILED/SUPERSEDED",
    )
    start_revision: Mapped[int] = mapped_column(Integer, comment="起始输入版本号")
    snapshot_revision: Mapped[int | None] = mapped_column(
        Integer, comment="领取快照版本号"
    )
    collect_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="消息合并截止时间"
    )
    max_collect_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="消息合并最长等待时间"
    )
    run_id: Mapped[str | None] = mapped_column(
        String(80), index=True, comment="AI运行ID"
    )
    locked_by: Mapped[str | None] = mapped_column(
        String(120), index=True, comment="租约持有者"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, comment="租约到期时间"
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, comment="处理次数")
    last_error: Mapped[str | None] = mapped_column(Text, comment="最近失败原因")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utcnow, comment="创建时间"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="开始执行时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="结束时间"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("message_id", name="uq_message_id"),
        UniqueConstraint(
            "conversation_id", "input_revision", name="uq_conversation_input_revision"
        ),
        UniqueConstraint("agent_run_id", "agent_outcome_seq", name="uq_agent_run_outcome_message"),
        {"comment": "会话消息"},
    )

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="消息序号"
    )
    message_id: Mapped[str] = mapped_column(
        String(80), index=True, comment="业务消息ID"
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True, comment="会话ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), comment="发送方角色：user/ai/human"
    )
    message_type: Mapped[str] = mapped_column(
        String(20), default="text", comment="消息类型"
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, comment="消息内容")
    input_revision: Mapped[int | None] = mapped_column(
        Integer, comment="对应用户输入版本号"
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        String(80), index=True, comment="AI运行ID"
    )
    agent_outcome_seq: Mapped[int | None] = mapped_column(
        Integer, comment="同一运行内的结果序号"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utcnow, comment="创建时间"
    )
    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Handoff(Base):
    __tablename__ = "handoffs"
    __table_args__ = (
        Index(
            "uq_open_handoff_per_conversation",
            "conversation_id",
            unique=True,
            postgresql_where=text("status IN ('waiting', 'active')"),
        ),
        Index(
            "uq_open_handoff_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('waiting', 'active')"),
        ),
        {"comment": "人工客服工单"},
    )

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("handoff"),
        comment="工单ID",
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True, comment="会话ID"
    )
    user_id: Mapped[str] = mapped_column(String(40), index=True, comment="用户ID")
    summary: Mapped[str] = mapped_column(Text, comment="转接摘要")
    status: Mapped[str] = mapped_column(
        String(20),
        default="waiting",
        index=True,
        comment="工单状态：waiting/active/resolved",
    )
    assigned_agent_id: Mapped[str | None] = mapped_column(
        String(40), index=True, comment="接单客服ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utcnow, comment="创建时间"
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="接单时间"
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="完结时间"
    )


class RealtimeOutbox(Base):
    __tablename__ = "realtime_outbox"
    __table_args__ = {"comment": "实时事件发件箱"}

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("evt"),
        comment="事件ID",
    )
    sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        unique=True,
        index=True,
        comment="发布序号",
    )
    channel: Mapped[str] = mapped_column(
        String(160), index=True, comment="推送通道"
    )
    event_type: Mapped[str] = mapped_column(
        String(80), index=True, comment="事件类型"
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(80), index=True, comment="会话ID"
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, comment="事件载荷")
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, comment="发布重试次数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utcnow, comment="创建时间"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, comment="发布时间"
    )
