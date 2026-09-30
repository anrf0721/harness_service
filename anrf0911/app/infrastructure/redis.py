"""
author: anrf
date:9/18/2026
desc:
"""
import redis.asyncio as redis

from anrf0911.common.config import get_settings

redis_client = redis.from_url(
    get_settings().redis_url,
    decode_responses=True,
)
