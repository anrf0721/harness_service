"""
author: anrf
date:9/12/2026
desc:
"""
from datetime import datetime
from typing import Literal, Any

from pydantic import BaseModel

class CurrentConversationResponse(BaseModel):
    id : str
    mode : str
    is_processing: bool

class ConversationMessageResponse(BaseModel):
    message_id: str
    role: Literal['user','ai','human']
    content: dict[str,Any]
    created_at: datetime

class ConversationDetailResponse(BaseModel):
    messages : list[ConversationMessageResponse]


