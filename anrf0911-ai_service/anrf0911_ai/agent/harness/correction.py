"""
author: anrf
date:9/28/2026
desc:
"""
from langchain_core.messages import SystemMessage

from anrf0911_ai.agent.harness.errors import CorrectableErrorCode


class OutputCorrectionRules:
    @staticmethod
    def can_correct(error):
        return isinstance(error.code,CorrectableErrorCode)

    @staticmethod
    def build_feedback(error):
        return SystemMessage(
            content=(
                "上一次回复没有通过校验："
                f"{error}。"
                "请只根据成功的工具结果重新生成；"
                "没有证据的事实不要写，未经工具确认的订单不要生成按钮。"
            )
        )

if __name__ == "__main__":
    from anrf0911_ai.agent.harness.errors import (
        AgentExecutionError,
        AgentOutputValidationError,
        TerminalErrorCode,
    )

    fact_error = AgentOutputValidationError(
        CorrectableErrorCode.UNSUPPORTED_FACT,
        "回复中的业务事实缺少工具支持：399",
    )
    stop_error = AgentExecutionError(
        TerminalErrorCode.OUTPUT_VALIDATION_FAILED,
        "Agent 输出校验失败",
    )
    print(OutputCorrectionRules.can_correct(fact_error))
    print(OutputCorrectionRules.build_feedback(fact_error).content)
    print(OutputCorrectionRules.can_correct(stop_error))