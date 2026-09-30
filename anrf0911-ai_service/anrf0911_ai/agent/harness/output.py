"""
author: anrf
date:9/24/2026
desc:
"""
from pydantic import BaseModel

from anrf0911_ai.agent.harness.action import PageAction, ActionValidator, ActionValidationError
from anrf0911_ai.agent.harness.answer import AnswerValidator
from anrf0911_ai.agent.harness.errors import AgentOutputValidationError, CorrectableErrorCode, AgentExecutionError, \
    TerminalErrorCode
from anrf0911_ai.agent.harness.fact import FactValidationError
from anrf0911_ai.app.schemas.agent import AgentOutput


class ValidatedAgentOutput(BaseModel):
    output: AgentOutput
    page_action : PageAction | None = None

class OutputValidator:
    def __init__(self):
        self.answer_validator = AnswerValidator()
        self.action_validator = ActionValidator()

    def validate(self, output: AgentOutput,tool_calls):
        try:
            checked = self.answer_validator.validate(output, tool_calls)
            page_action = self.action_validator.validate(
                checked.page_action_request,
                tool_calls,
            )
            return ValidatedAgentOutput(output=checked, page_action=page_action)
        except FactValidationError as error:
            raise AgentOutputValidationError(
                CorrectableErrorCode.UNSUPPORTED_FACT,
                error.message,
            ) from error
        except ActionValidationError as error:
            raise AgentOutputValidationError(
                CorrectableErrorCode(error.code),
                error.message,
            ) from error
        except Exception as error:
            raise AgentExecutionError(
                TerminalErrorCode.OUTPUT_VALIDATION_FAILED,
                "Agent 输出校验失败",
            ) from error


if __name__ == "__main__":
    from anrf0911_ai.agent.harness.action import PageActionRequest
    from anrf0911_ai.agent.harness.snapshot import ToolCallSnapshot
    from anrf0911_ai.app.schemas.agent import ReplyType

    output = AgentOutput(
        reply_type=ReplyType.ANSWER,
        reply_content="可以取消订单 ORDER_001",
        page_action_request=PageActionRequest(
            action_code="CANCEL_ORDER",
            resource_id="ORDER-001",
        ),
    )
    success = (
        ToolCallSnapshot(
            tool_name="get_order",
            arguments={"order_id": "ORDER_001"},
            result={"success": True, "code": "OK", "data": {"id": "ORDER_001"}},
            success=True,
        ),
    )
    failed = (
        ToolCallSnapshot(
            tool_name="get_logistics",
            arguments={"order_id": "ORDER_001"},
            result={
                "success": False,
                "code": "TOOL_CALL_FAILED",
                "message": "暂时无法取得可靠的业务数据",
            },
            success=False,
        ),
    )
    validator = OutputValidator()
    passed = validator.validate(output, success)
    blocked = validator.validate(output, failed)
    print(passed.page_action.href if passed.page_action else None)
    print(blocked.output.reply_type, blocked.page_action)
    try:
        validator.validate(
            AgentOutput(
                reply_type=ReplyType.ANSWER,
                reply_content="总价是 399 元",
            ),
            success,
        )
    except AgentOutputValidationError as error:
        print(error.code, error)

    try:
        validator.validate(
            AgentOutput(
                reply_type=ReplyType.ANSWER,
                reply_content="可以取消",
                page_action_request=PageActionRequest(
                    action_code="CANCEL_ORDER",
                    resource_id="ORDER-999",
                ),
            ),
            success,
        )
    except AgentOutputValidationError as error:
        print(error.code, error)