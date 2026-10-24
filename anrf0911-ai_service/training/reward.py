"""用线上同一套事实校验和页面动作校验给 GRPO 打分。"""

from __future__ import annotations

import json

from pydantic import ValidationError

from anrf0911_ai.agent.harness.action import ActionValidationError, ActionValidator
from anrf0911_ai.agent.harness.fact import FactChecker, FactValidationError
from anrf0911_ai.agent.harness.snapshot import ToolCallSnapshot
from anrf0911_ai.app.schemas.agent import AgentOutput, ReplyType
from training.data import BUSINESS_HINTS
from training.format import TOOL_CALL_PATTERN, extract_payload


FORMAT_SCORE = 0.15
REJECT_SCORE = 0.1
PASS_SCORE = 1.0


def parse_output(text: str) -> AgentOutput | None:
    payload = extract_payload(completion_text(text))
    if not isinstance(payload, dict):
        return None
    if "reply_type" not in payload and "arguments" in payload:
        payload = payload["arguments"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict) or "reply_type" not in payload:
        return None
    try:
        return AgentOutput.model_validate(payload)
    except ValidationError:
        return None


def completion_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("content"):
            return str(value["content"])
        calls = value.get("tool_calls") or []
        if calls:
            function = calls[0].get("function", {})
            return json.dumps(
                {
                    "name": function.get("name"),
                    "arguments": function.get("arguments"),
                },
                ensure_ascii=False,
            )
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list) and value:
        return completion_text(value[-1])
    return str(value)


def snapshots_from_evidence(raw) -> tuple[ToolCallSnapshot, ...]:
    items = raw
    if isinstance(raw, str):
        items = json.loads(raw) if raw else []
    if not isinstance(items, list):
        return ()
    return tuple(
        ToolCallSnapshot(
            tool_name=item["tool_name"],
            arguments=dict(item.get("arguments") or {}),
            result=item.get("result"),
            success=item.get("success"),
        )
        for item in items
    )


def protocol_ok(output: AgentOutput) -> bool:
    if not output.reply_content.strip():
        return False
    if output.reply_type == ReplyType.REQUEST_HANDOFF:
        return output.handoff_request is not None and output.page_action_request is None
    if output.handoff_request is not None:
        return False
    if output.reply_type != ReplyType.ANSWER and output.page_action_request is not None:
        return False
    return True


def business_question_without_evidence(question: str, calls: tuple[ToolCallSnapshot, ...]) -> bool:
    if any(call.success is True for call in calls):
        return False
    return any(hint in question for hint in BUSINESS_HINTS)


def score_output(output: AgentOutput, calls: tuple[ToolCallSnapshot, ...], question: str) -> float:
    if not protocol_ok(output):
        return FORMAT_SCORE
    successful = tuple(call for call in calls if call.success is True)
    if business_question_without_evidence(question, calls):
        if output.reply_type == ReplyType.ANSWER or output.page_action_request is not None:
            return REJECT_SCORE
        return PASS_SCORE
    try:
        FactChecker().check(output.reply_content, successful)
        ActionValidator().validate(output.page_action_request, calls)
    except (FactValidationError, ActionValidationError):
        return REJECT_SCORE
    return PASS_SCORE


def score_text(text: str, tool_evidence, question: str = "") -> float:
    output = parse_output(text)
    if output is None:
        return 0.0
    return score_output(output, snapshots_from_evidence(tool_evidence), question)


def _align(value, size: int):
    if value is None:
        return [None] * size
    if isinstance(value, str):
        return [value] * size
    value = list(value)
    if len(value) == size:
        return value
    if len(value) == 1:
        return value * size
    raise ValueError("奖励列长度和生成结果不一致")


def support_reward(completions, tool_evidence=None, question=None, **kwargs) -> list[float]:
    evidence = tool_evidence if tool_evidence is not None else kwargs.get("tool_evidence")
    questions = question if question is not None else kwargs.get("question")
    evidence = _align(evidence, len(completions))
    questions = _align(questions, len(completions))
    return [
        score_text(completion, item, questions[index] or "")
        for index, (completion, item) in enumerate(zip(completions, evidence))
    ]


if __name__ == "__main__":
    from training.data import build_samples

    failed = 0
    for sample in build_samples():
        if sample.task != "answer":
            continue
        score = score_text(sample.completion, sample.tool_evidence, sample.question)
        print(f"{sample.sample_id}: {score}")
        if score != PASS_SCORE:
            failed += 1
    invented = score_text(
        '{"reply_type":"ANSWER","reply_content":"订单 ORDER_001 当前已发货，总金额为 399 元。"}',
        [{
            "tool_name": "get_order",
            "arguments": {"order_id": "ORDER_001"},
            "result": {"success": True, "data": {"id": "ORDER_001", "status": "pending_shipment", "total_amount": "899.00"}},
            "success": True,
        }],
        "订单 ORDER_001 现在什么状态？",
    )
    print("invented:", invented)
    if invented >= PASS_SCORE:
        failed += 1
    if failed:
        raise SystemExit(f"{failed} 条奖励不符合预期")
    print("reward ok")
