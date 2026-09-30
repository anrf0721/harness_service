"""
author: anrf
date:9/17/2026
desc:
"""
from pydantic import BaseModel


class HandoffReplyRequest(BaseModel):
    message_id: str
    text: str

class HandoffResolveRequest(BaseModel):
    resolution: str