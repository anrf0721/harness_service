"""
author: anrf
date:9/19/2026
desc:
"""
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.prompt import  support_prompt
from anrf0911_ai.agent.skills.load import load_skill
from anrf0911_ai.agent.skills.middleware import SkillScopeMiddleware
from anrf0911_ai.agent.skills.state import AgentExecutionState
from anrf0911_ai.agent.tools.catalog import TOOL_CATALOG
from anrf0911_ai.app.schemas.agent import AgentOutput
from anrf0911_ai.common.config import get_settings


def create_model():
    settings = get_settings()
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
        temperature=0,
    )


def create_support_agent():
    return create_agent(
        model=create_model(),
        tools=[load_skill, *TOOL_CATALOG.get_agent_tools()],
        response_format=ToolStrategy(AgentOutput),
        state_schema=AgentExecutionState,
        name="ecommerce-customer-support",
        context_schema=AgentRuntimeContext,
        middleware=[
            support_prompt,
            SkillScopeMiddleware(),
            ToolCallLimitMiddleware(run_limit=8, exit_behavior="error"),
        ],
    )


if __name__ == "__main__":
    import json

    from anrf0911_ai.agent.coordinator import AgentRunCoordinator
    from anrf0911_ai.agent.executor import AgentExecutor
    from anrf0911_ai.app.db import SessionFactory
    from anrf0911_ai.app.schemas.run import AgentRunRequest, CurrentMessage
    from anrf0911_ai.app.services.auth import AuthService, CurrentUser
    from anrf0911_ai.common.utils import get_uid, run_async

    async def main():
        user_id = input("请输入测试用户ID：").strip()
        question = input("请输入问题：").strip()

        user = CurrentUser(user_id=user_id, role="customer")
        token = AuthService().encode_access_token(user)

        # 2. 模拟用户发来一条消息
        request = AgentRunRequest(
            conversation_id="test_agent",
            turn_id=get_uid("test_turn"),
            messages=[
                CurrentMessage(
                    message_id=get_uid("msg"),
                    type="text",
                    content={"text": question},
                )
            ],
        )

        # 3. 创建已经注册查询工具的智能体
        agent = create_support_agent()
        executor = AgentExecutor(agent)

        # 4. 通过协调器启动完整的一轮处理
        async with SessionFactory() as session:
            coordinator = AgentRunCoordinator(session, executor)

            result = await coordinator.start_run(
                user_id=user.user_id,
                request=request,
                access_token=token,
            )

        print(json.dumps(result, ensure_ascii=False, indent=2))

    run_async(main())
