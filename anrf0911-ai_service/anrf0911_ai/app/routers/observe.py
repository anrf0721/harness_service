"""
author: anrf
date:9/29/2026
desc:
"""
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import func, select

from anrf0911_ai.app.dependencies import AuthServiceDep, SessionDep
from anrf0911_ai.models.models import AgentRun, AgentToolCall

router = APIRouter(prefix="/api/v1", tags=["观测"])


@router.get("/admin/metrics")
async def admin_metrics(
    auth_service: AuthServiceDep,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, "admin")
    count, avg_latency, input_tokens, output_tokens = (
        await session.execute(
            select(
                func.count(AgentRun.id),
                func.coalesce(func.avg(AgentRun.latency_ms), 0),
                func.coalesce(func.sum(AgentRun.input_tokens), 0),
                func.coalesce(func.sum(AgentRun.output_tokens), 0),
            )
        )
    ).one()
    return {
        "agent_runs": count,
        "average_latency_ms": int(avg_latency),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
    }


@router.get("/runs")
async def list_runs(
    auth_service: AuthServiceDep,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, "admin", "agent")
    rows = (
        await session.scalars(
            select(AgentRun).order_by(AgentRun.started_at.desc()).limit(20)
        )
    ).all()
    return [
        {
            "id": run.id,
            "conversation_id": run.conversation_id,
            "model_name": run.model_name,
            "state": run.state,
            "latency_ms": run.latency_ms or 0,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
        }
        for run in rows
    ]


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    auth_service: AuthServiceDep,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
):
    auth_service.get_authorized_user(authorization, "admin", "agent")
    run = await session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    calls = (
        await session.scalars(
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run_id)
            .order_by(AgentToolCall.created_at)
        )
    ).all()
    return {
        "run": {
            "state": run.state,
            "prompt_version": run.prompt_version,
            "input_revision": (run.input_context or {}).get("input_revision"),
            "outcome": run.result,
            "latency_ms": run.latency_ms or 0,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
        },
        "tool_calls": [
            {
                "tool_call_id": call.tool_call_id,
                "tool_name": call.tool_name,
                "mode": "read",
                "latency_ms": call.latency_ms,
                "arguments": call.arguments,
            }
            for call in calls
        ],
    }
