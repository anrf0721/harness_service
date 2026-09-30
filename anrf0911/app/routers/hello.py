"""
author: anrf
date:9/11/2026
desc:
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class User(BaseModel):
    name: str
    age: int

@router.get("/hello",response_model=User)
async def hello_world():
    return {"hello":"world",'name':'hh','age':55}
