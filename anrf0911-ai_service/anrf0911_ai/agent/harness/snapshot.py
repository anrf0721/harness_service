"""
author: anrf
date:9/22/2026
desc:
"""
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from anrf0911_ai.app.db import SessionFactory
from anrf0911_ai.models.models import AgentToolCall


@dataclass(frozen=True)
class ToolCallSnapshot:
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    success: bool | None

    @classmethod
    def from_tool_call(cls, tool_call: AgentToolCall) -> "ToolCallSnapshot":
        return cls(
            tool_name=tool_call.tool_name,
            arguments=dict(tool_call.arguments),
            result=dict(tool_call.result) if tool_call.result is not None else None,
            success=tool_call.success,
        )


class ToolCallReader:
    async def read_by_run_id(self, run_id: str) -> tuple[ToolCallSnapshot, ...]:
        async with SessionFactory() as session:
            rows = await session.scalars(
                select(AgentToolCall)
                .where(AgentToolCall.run_id == run_id)
                .order_by(AgentToolCall.created_at)
            )
            calls = rows.all()
        return tuple(ToolCallSnapshot.from_tool_call(call) for call in calls)


if __name__ == "__main__":
    from anrf0911_ai.common.utils import run_async

    run_id = input("请输入运行ID：").strip()
    snapshots = run_async(ToolCallReader().read_by_run_id(run_id))
    for item in snapshots:
        print(item.tool_name, item.success, item.arguments)
