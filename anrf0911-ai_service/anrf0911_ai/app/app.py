"""
author: anrf
date:9/18/2026
desc:
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from anrf0911_ai.agent.factory import create_support_agent
from anrf0911_ai.app.routers import observe, run
from anrf0911_ai.common.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = create_support_agent()
    yield

app = FastAPI(description='电商小二 AI',lifespan=lifespan)
app.include_router(run.router)
app.include_router(observe.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
