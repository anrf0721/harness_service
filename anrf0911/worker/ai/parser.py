"""
author: anrf
date:9/15/2026
desc:
"""


def parse_event(body):
    event_type = body.get('event_type')
    data = body.get('event_data') or {}

    if event_type == 'run_completed':
        return data

    if event_type == 'run_failed':
        raise RuntimeError(data.get("message") or 'AI 处理失败')

    if event_type == 'run_handoff_requested':
        return {
            **data,
            'outcome_type': 'handoff',
            'summary': str(data.get('summary') or '用户请求人工客服'),
            'content': {
                'text': str(
                    data.get('message') or '正在为你转接人工客服，请稍候。'
                )
            },
        }

    raise RuntimeError(f'暂不支持的事件: {event_type}')
