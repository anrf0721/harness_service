"""
author: anrf
date:9/29/2026
desc:
"""
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.skills.catalog import SKILL_CATALOG, SkillCode
from anrf0911_ai.agent.skills.state import AgentExecutionState


@tool
async def load_skill(
    skill_code: SkillCode,
    runtime: ToolRuntime[AgentRuntimeContext, AgentExecutionState],
) -> Command:
    """加载与当前问题最匹配的客服领域。只切换领域，不查询订单或商品。"""
    skill = SKILL_CATALOG.get_skill(skill_code)
    tool_names = "、".join(skill.tools) if skill.tools else "无"
    content = "\n".join(
        (
            f"已加载领域：{skill.code}",
            *skill.guidance,
            f"当前可用工具：{tool_names}",
        )
    )
    return Command(
        update={
            "active_skill_code": skill.code,
            "messages": [
                ToolMessage(
                    content=content,
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )


if __name__ == "__main__":
    from anrf0911_ai.common.utils import run_async

    runtime = ToolRuntime(
        state={},
        context=AgentRuntimeContext(
            run_id="r",
            conversation_id="c",
            user_id="u1",
            access_token="token",
        ),
        config={},
        stream_writer=lambda _: None,
        tool_call_id="call_1",
        store=None,
    )
    command = run_async(load_skill.coroutine(SkillCode.ORDER_SERVICE, runtime))
    print(command.update["active_skill_code"])
    print(command.update["messages"][0].content)
