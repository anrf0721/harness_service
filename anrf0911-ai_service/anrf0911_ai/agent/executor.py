"""
author: anrf
date:9/19/2026
desc:
"""
import json

from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import ValidationError

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.harness.correction import OutputCorrectionRules
from anrf0911_ai.agent.harness.errors import AgentOutputValidationError, CorrectableErrorCode, AgentExecutionError, \
    TerminalErrorCode
from anrf0911_ai.agent.harness.output import OutputValidator
from anrf0911_ai.agent.harness.snapshot import ToolCallReader
from anrf0911_ai.app.schemas.agent import ReplyType, AgentOutput
from anrf0911_ai.app.schemas.run import HistoryMessage, AgentRunRequest, CurrentMessage
from anrf0911_ai.common.config import get_settings
from anrf0911_ai.common.utils import get_uid


def message_text(item):
    if item.type == 'object':
        return json.dumps(item.content)
    return str(item.content['text'])


def trim_history(history: list[HistoryMessage]):
    settings = get_settings()
    recent = list(history[-settings.history_message_limit:])
    chosen = []
    total = 0
    for item in reversed(recent):
        text = message_text(item)
        if chosen and total + len(text) > settings.history_character_budget:
            break
        chosen.append(item)
        total += len(text)
    chosen.reverse()
    while chosen and chosen[0].role != 'user':
        chosen.pop(0)
    return chosen


def compile_messages(request: AgentRunRequest):
    messages = []
    for item in trim_history(request.history):
        text = message_text(item)
        if item.role == 'user':
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))

    parts = [message_text(item) for item in request.messages]
    if len(parts) == 1:
        current = parts[0]
    else:
        current = '用户连续发送了以下内容，请作为一个整体理解，并以最新表达为准：\n' + '\n'.join(
            f'{index},{text}' for index, text in enumerate(parts)
        )
    messages.append(HumanMessage(content=current))
    return messages


def collect_token_usage(callback):
    items = callback.usage_metadata.values()
    return {
        "input_tokens": sum(item.get("input_tokens", 0) for item in items),
        "output_tokens": sum(item.get("output_tokens", 0) for item in items),
    }


def normalize_output(value):
    structured = (
        value['structured_response'] if isinstance(value, dict) else value
    )
    try:
        if isinstance(structured, AgentOutput):
            return structured
        return AgentOutput.model_validate(structured)
    except ValidationError as error:
        raise AgentOutputValidationError(
            CorrectableErrorCode.MODEL_OUTPUT_INVALID,
            "模型返回的结构化结果不符合约定",
        ) from error


def map_run_result(output: AgentOutput,page_action = None):
    if output.reply_type == ReplyType.REQUEST_HANDOFF:
        handoff = output.handoff_request
        return "run_handoff_requested", {
            "summary": handoff.summary,
            "message_id": get_uid("msg"),
            "message": output.reply_content,
        }
    content = {'text':output.reply_content}
    if page_action is not None:
        content["action"] = {
            "label": page_action.label,
            "description": page_action.description,
            "href": page_action.href,
        }
    return "run_completed", {
        "message_id": get_uid("msg"),
        "content": content,
    }


class AgentExecutor:
    def __init__(self, agent):
        self.agent = agent
        self.output_validator = OutputValidator()
        self.tool_reader = ToolCallReader()

    async def execute(self, request: AgentRunRequest,context:AgentRuntimeContext):
        messages = compile_messages(request)
        usage_callback = UsageMetadataCallbackHandler()
        for used in range(2):
            try:
                raw = await self.agent.ainvoke(
                    {"messages": messages},
                    context=context,
                    config={"callbacks": [usage_callback]},
                )
            except ToolCallLimitExceededError:
                output = AgentOutput(
                    reply_type=ReplyType.DECLINE,
                    reply_content="本次查询调用业务工具次数过多，暂时无法完成查询。",
                )
                state, result = map_run_result(output)
                return state, result, collect_token_usage(usage_callback)

            except Exception as error:
                raise AgentExecutionError(
                    TerminalErrorCode.MODEL_CALL_FAILED,
                    "模型调用失败",
                ) from error

            try:
                output = normalize_output(raw)
                tool_calls = await self.tool_reader.read_by_run_id(context.run_id)
                checked = self.output_validator.validate(output, tool_calls)
                state, result = map_run_result(checked.output, checked.page_action)
                return state, result, collect_token_usage(usage_callback)
            except AgentOutputValidationError as error:
                if used >= 1 or not OutputCorrectionRules.can_correct(error):
                    raise AgentExecutionError(error.code, str(error)) from error
                if isinstance(raw, dict) and raw.get("messages"):
                    messages = list(raw["messages"])
                messages.append(OutputCorrectionRules.build_feedback(error))

if __name__ == "__main__":
    from anrf0911_ai.common.utils import run_async

    class FakeUsage:
        usage_metadata = {
            "first": {"input_tokens": 10, "output_tokens": 2},
            "second": {"input_tokens": 5, "output_tokens": 1},
        }

    print(collect_token_usage(FakeUsage()))

    class FakeAgent:
        async def ainvoke(self, payload, context, config=None):
            raise ToolCallLimitExceededError(0, 8, None, 8)

    request = AgentRunRequest(
        conversation_id="c",
        turn_id="t",
        messages=[
            CurrentMessage(message_id="m", type="text", content={"text": "查一下"})
        ],
    )
    context = AgentRuntimeContext(
        run_id="r",
        conversation_id="c",
        user_id="u1",
        access_token="x",
    )
    output = run_async(AgentExecutor(FakeAgent()).execute(request, context))
    print(output[0], output[1]["content"]["text"])