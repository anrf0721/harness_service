"""
author: anrf
date:9/18/2026
desc:
"""
from time import perf_counter

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.executor import AgentExecutor
from anrf0911_ai.agent.harness.errors import TerminalErrorCode, AgentExecutionError
from anrf0911_ai.app.schemas.run import AgentRunRequest
from anrf0911_ai.common.config import get_settings
from anrf0911_ai.common.utils import get_utcnow
from anrf0911_ai.models.models import AgentRun


def build_run_event(run: AgentRun) -> dict:
    event_data = dict(run.result or {})
    event_data["run_id"] = run.id
    return {
        "event_type": run.state,
        "event_data": event_data,
    }


class AgentRunCoordinator:
    def __init__(self, session: AsyncSession, executor: AgentExecutor):
        self.session = session
        self.executor = executor

    async def start_run(self, user_id: str, request: AgentRunRequest, access_token: str):
        started = perf_counter()
        settings = get_settings()
        run = AgentRun(
            conversation_id=request.conversation_id,
            turn_id=request.turn_id,
            user_id=user_id,
            state="RUNNING",
            input_context=request.model_dump(),
            model_name=settings.llm_model,
            prompt_version=settings.prompt_version,
        )
        self.session.add(run)
        await self.session.commit()

        try:
            context = AgentRuntimeContext(
                access_token=access_token,
                conversation_id=request.conversation_id,
                run_id=run.id,
                user_id=user_id,
            )
            run.state, run.result, usage = await self.executor.execute(request, context)
            run.input_tokens = usage["input_tokens"]
            run.output_tokens = usage["output_tokens"]
        except Exception as exc:
            if isinstance(exc, AgentExecutionError):
                error_code = exc.code
            else:
                error_code = TerminalErrorCode.AGENT_EXECUTION_FAILED
            run.state = "run_failed"
            run.error = str(exc)
            run.result = {
                "code": error_code,
                "message": "AI Service 处理失败",
            }
        run.latency_ms = int((perf_counter() - started) * 1000)
        run.finished_at = get_utcnow()
        await self.session.commit()
        return build_run_event(run)

    async def commit_run(self, user_id: str, run_id: str) -> dict:
        run = await self.session.scalar(
            select(AgentRun)
            .where(AgentRun.id == run_id)
            .with_for_update()
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Run 不存在")
        if run.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权操作该 Run")
        if run.state != "run_decision_prepared":
            raise HTTPException(status_code=409, detail="当前状态不能提交")

        if (run.result or {}).get("outcome_type") == "handoff":
            run.state = "run_handoff_requested"
        else:
            run.state = "run_completed"
        run.finished_at = get_utcnow()
        await self.session.commit()
        return build_run_event(run)

    async def cancel_run(self, user_id: str, run_id: str):
        run = await self.session.get(AgentRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run 不存在")
        if run.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权操作该 Run")
        if run.state == "run_decision_prepared":
            run.state = "SUPERSEDED"
            run.finished_at = get_utcnow()
            await self.session.commit()
