"""
author: anrf
date:9/15/2026
desc:
"""
import httpx

from anrf0911.common.config import *


class AIServiceGateway:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ai_service_url.rstrip('/')
        self.internal_token = settings.internal_service_token

    async def start_run(self,user_token:str,payload:dict):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f'{self.base_url}/internal/v1/agent/runs',
                json=payload,
                headers={
                    'Authorization': f'Bearer {user_token}',
                    'X-Internal-Service-Token': self.internal_token,
                }
            )
            response.raise_for_status()
            return response.json()

    # async def start_run(self, user_token: str, payload: dict):
    #     texts = []
    #     for item in payload.get('messages') or []:
    #         content = item.get('content') or {}
    #         text = content.get('text') or ''
    #         if text:
    #             texts.append(text)
    #     last_text = texts[-1] if texts else ''
    #
    #     if '转人工' in last_text or last_text.strip() == '人工':
    #         return {
    #             'event_type': 'run_handoff_requested',
    #             'event_data': {
    #                 'run_id': payload.get('request_id'),
    #                 'summary': last_text,
    #                 'message': '已收到您的请求，正在为您安排人工客服，请稍候。',
    #             },
    #         }
    #
    #     return {
    #         'event_type': 'run_completed',
    #         'event_data': {
    #             'run_id': payload.get('request_id'),
    #             'content': {
    #                 'text': '模拟 AI 回复：您好，请问有什么可以帮助您？',
    #             },
    #         },
    #     }
