"""
author: anrf
date:9/11/2026
desc:
"""
from pydantic import BaseModel
from typing import Literal


class CurrentUser(BaseModel):
    user_id: str
    role:Literal['customer','agent','admin'] = 'customer'