"""
author: anrf
date:9/18/2026
desc:
"""
from enum import StrEnum

from pydantic import BaseModel

from anrf0911_ai.agent.harness.action import PageActionRequest


class ReplyType(StrEnum):
    ANSWER = "ANSWER"
    CLARIFY = "CLARIFY"
    DECLINE = "DECLINE"
    REQUEST_HANDOFF = "REQUEST_HANDOFF"


class HandoffRequest(BaseModel):
    reason_code: str
    summary: str


class AgentOutput(BaseModel):
    reply_type: ReplyType
    reply_content: str
    handoff_request: HandoffRequest | None = None
    page_action_request: PageActionRequest | None = None


if __name__ == "__main__":
    print(AgentOutput(reply_type="ANSWER", reply_content="你好"))
