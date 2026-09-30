"""
author: anrf
date:9/18/2026
desc:
"""
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from anrf0911_ai.app.db import Base
from anrf0911_ai.common.utils import get_uid, get_utcnow


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"comment": "一次 Agent 运行"}

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("run"),
        comment="Run ID",
    )
    conversation_id: Mapped[str] = mapped_column(
        String(80),
        index=True,
        comment="所属会话ID",
    )
    turn_id: Mapped[str] = mapped_column(
        String(80),
        index=True,
        comment="对应客服 Turn ID",
    )
    user_id: Mapped[str] = mapped_column(
        String(80),
        index=True,
        comment="用户ID",
    )
    state: Mapped[str] = mapped_column(
        String(30),
        default="RUNNING",
        index=True,
        comment="运行状态，有结果后直接存事件名，如 run_completed",
    )
    input_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        comment="本次固定输入快照",
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="结构化结果：回复/转人工/失败",
    )
    model_name: Mapped[str] = mapped_column(
        String(120),
        default="",
        comment="本次使用的模型",
    )
    prompt_version: Mapped[str] = mapped_column(
        String(80),
        default="",
        comment="本次使用的 Prompt 版本",
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="模型输入 Token 数",
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="模型输出 Token 数",
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="执行耗时毫秒",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="内部错误详情",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utcnow,
        comment="开始时间",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="结束时间",
    )


class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"
    __table_args__ = {"comment": "Agent业务工具调用记录"}

    id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
        default=lambda: get_uid("tool"),
        comment="工具调用记录ID",
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"),
        index=True,
        comment="所属Agent运行ID",
    )

    tool_call_id: Mapped[str] = mapped_column(
        String(120),
        comment="模型生成的工具调用ID",
    )

    tool_name: Mapped[str] = mapped_column(
        String(80),
        comment="工具名称，如get_order",
    )

    arguments: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        comment="工具调用参数，不包含用户令牌",
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="工具返回的统一结果，包含成功状态、结果编码、说明和业务数据",
    )

    success: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="是否调用成功，NULL表示尚未记录结果",
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="工具执行耗时，单位毫秒",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utcnow,
        comment="工具调用记录创建时间",
    )
