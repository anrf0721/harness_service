"""
author: anrf
date:9/24/2026
desc:
"""
from enum import StrEnum


class CorrectableErrorCode(StrEnum):
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    UNSUPPORTED_FACT = "UNSUPPORTED_FACT"
    UNVERIFIED_ACTION_RESOURCE = "UNVERIFIED_ACTION_RESOURCE"


class TerminalErrorCode(StrEnum):
    MODEL_CALL_FAILED = "MODEL_CALL_FAILED"
    OUTPUT_VALIDATION_FAILED = "OUTPUT_VALIDATION_FAILED"
    AGENT_EXECUTION_FAILED = "AGENT_EXECUTION_FAILED"


class AgentOutputValidationError(ValueError):
    def __init__(self, code: CorrectableErrorCode, message: str):
        self.code = code
        super().__init__(message)


class AgentExecutionError(RuntimeError):
    def __init__(self, code: CorrectableErrorCode | TerminalErrorCode, message: str):
        self.code = code
        super().__init__(message)


if __name__ == "__main__":
    error = AgentOutputValidationError(
        CorrectableErrorCode.UNSUPPORTED_FACT,
        "回复中的业务事实缺少工具支持：399",
    )
    print(error.code)
    print(error)
