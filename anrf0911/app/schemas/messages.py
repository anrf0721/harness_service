"""
author: anrf
date:9/14/2026
desc:
"""
from typing import Any

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message_id: str
    type: str = "text"
    content: dict[str, Any]


class AcceptUserMessageResponse(BaseModel):
    conversation_id: str
    mode: str