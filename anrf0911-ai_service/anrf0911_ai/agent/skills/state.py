"""
author: anrf
date:9/29/2026
desc:
"""
from typing import NotRequired

from langchain.agents import AgentState

from anrf0911_ai.agent.skills.catalog import SkillCode
from anrf0911_ai.app.schemas.agent import AgentOutput


class AgentExecutionState(AgentState[AgentOutput]):
    active_skill_code: NotRequired[SkillCode]