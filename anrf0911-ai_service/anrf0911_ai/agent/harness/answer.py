"""
author: anrf
date:9/23/2026
desc:
"""
from anrf0911_ai.agent.harness.fact import FactChecker
from anrf0911_ai.agent.harness.snapshot import ToolCallSnapshot
from anrf0911_ai.agent.tools.catalog import TOOL_CATALOG, ToolCategory
from anrf0911_ai.agent.tools.output import ToolFailureType
from anrf0911_ai.app.schemas.agent import AgentOutput, ReplyType


class AnswerValidator:
    decline_text = (
        "暂时无法取得可靠的订单、商品、物流或售后信息，"
        "因此现在不能确认结果，请稍后重试。"
    )
    # technical_codes = {"TOOL_CALL_FAILED", "INVALID_TOOL_RESULT"}

    def __init__(self):
        self.fact_checker = FactChecker()

    def safe_reply(self,business_calls):
        for call in business_calls:
            failure_type = None
            if call.result:
                failure_type = call.result.get("failure_type")
            if failure_type != ToolFailureType.BUSINESS:
                return AgentOutput(
                    reply_type=ReplyType.DECLINE,
                    reply_content=self.decline_text,
                )
        message = business_calls[-1].result["message"]
        return AgentOutput(reply_type=ReplyType.ANSWER,reply_content=message)


    def validate(self,output:AgentOutput,tool_calls:tuple[ToolCallSnapshot,...]):
        business_calls = [call for call in tool_calls if TOOL_CATALOG.get_tool_category(call.tool_name) == ToolCategory.BUSINESS]
        successful_calls = [call for call in business_calls if call.success is True]

        if business_calls and not successful_calls:
            return self.safe_reply(business_calls)

        self.fact_checker.check(output.reply_content,tuple(successful_calls))
        return output

if __name__ == "__main__":
    from anrf0911_ai.app.schemas.agent import HandoffRequest

    output = AgentOutput(
        reply_type=ReplyType.ANSWER,
        reply_content="已经发货了",
        handoff_request=HandoffRequest(reason_code="x", summary="帮我查物流"),
    )
    no_logistics = (
        ToolCallSnapshot(
            tool_name="get_logistics",
            arguments={"order_id": "ORDER_001"},
            result={
                "success": False,
                "code": "NO_LOGISTICS",
                "message": "订单尚未产生物流信息",
                "failure_type": "BUSINESS",
            },
            success=False,
        ),
    )
    offline = (
        ToolCallSnapshot(
            tool_name="get_logistics",
            arguments={"order_id": "ORDER_001"},
            result={
                "success": False,
                "code": "TOOL_CALL_FAILED",
                "message": "暂时无法取得可靠的业务数据",
                "failure_type": "SERVICE_CALL",

            },
            success=False,
        ),
    )
    validator = AnswerValidator()
    first = validator.validate(output, no_logistics)
    second = validator.validate(output, offline)
    print(first.reply_type, first.reply_content, first.handoff_request)
    print(second.reply_type, second.reply_content, second.handoff_request)