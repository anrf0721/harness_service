"""
author: anrf
date:9/11/2026
desc:
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from anrf0911.app.routers import hello, handoff, realtime, admin
from anrf0911.app.routers.chat import conversation, messages

from anrf0911.common.config import get_settings

ARCHITECTURE_DIR = Path(__file__).resolve().parents[1] / "architecture"

app = FastAPI(description='电商小二客服')
app.include_router(hello.router)
app.include_router(conversation.router)
app.include_router(messages.router)

app.include_router(realtime.router)
app.include_router(handoff.router)
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.mount(
    "/architecture",
    StaticFiles(directory=ARCHITECTURE_DIR, html=True),
    name="architecture",
)