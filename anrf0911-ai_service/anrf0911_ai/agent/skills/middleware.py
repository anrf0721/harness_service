"""
author: anrf
date:9/29/2026
desc:
"""
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.skills.catalog import SKILL_CATALOG, SkillCode
from anrf0911_ai.agent.skills.state import AgentExecutionState
from anrf0911_ai.app.schemas.agent import AgentOutput


def select_tools(tools, active_skill_code: SkillCode | None):
    allowed = {"load_skill"}
    if active_skill_code is not None:
        skill = SKILL_CATALOG.get_skill(active_skill_code)
        allowed.update(skill.tools)
    return [tool for tool in tools if tool.name in allowed]


class SkillScopeMiddleware(
    AgentMiddleware[AgentExecutionState, AgentRuntimeContext, AgentOutput]
):
    async def awrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        visible = select_tools(
            request.tools,
            request.state.get("active_skill_code"),
        )
        request = request.override(
            tools=visible,
            model_settings={
                **request.model_settings,
                "parallel_tool_calls": False,
            },
        )
        return await handler(request)


if __name__ == "__main__":
    class FakeTool:
        def __init__(self, name):
            self.name = name

    tools = [
        FakeTool("load_skill"),
        FakeTool("list_orders"),
        FakeTool("get_order"),
        FakeTool("search_products"),
    ]
    print([tool.name for tool in select_tools(tools, None)])
    print([tool.name for tool in select_tools(tools, SkillCode.ORDER_SERVICE)])
