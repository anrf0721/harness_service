"""
author: anrf
date:9/20/2026
desc:
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class AgentRuntimeContext:
    run_id : str
    conversation_id : str
    user_id : str
    access_token : str