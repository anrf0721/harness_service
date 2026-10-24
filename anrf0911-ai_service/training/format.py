"""训练和本地服务共用同一套对话渲染，避免两边提示格式不一致。"""

from __future__ import annotations

import json
import re

AGENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reply_type": {
            "type": "string",
            "enum": ["ANSWER", "CLARIFY", "DECLINE", "REQUEST_HANDOFF"],
        },
        "reply_content": {"type": "string"},
        "handoff_request": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "reason_code": {"type": "string"},
                        "summary": {"type": "string"},
                    },
                    "required": ["reason_code", "summary"],
                },
                {"type": "null"},
            ]
        },
        "page_action_request": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "action_code": {"type": "string"},
                        "resource_id": {"type": "string"},
                    },
                    "required": ["action_code"],
                },
                {"type": "null"},
            ]
        },
    },
    "required": ["reply_type", "reply_content"],
}


def openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "加载与当前问题最匹配的客服领域。只切换领域，不查询订单或商品。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_code": {
                            "type": "string",
                            "enum": [
                                "product-service",
                                "order-service",
                                "logistics-service",
                                "policy-service",
                                "after-sales-service",
                            ],
                        }
                    },
                    "required": ["skill_code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_order",
                "description": "查询当前用户的一条订单详情。必须提供订单编号。只查询。",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_orders",
                "description": "查询当前用户的订单列表。",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_logistics",
                "description": "查询一个订单的物流公司和配送轨迹。",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_after_sales",
                "description": "查询当前用户的售后记录。只查询。",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "按名称或需求搜索在售商品。",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_product",
                "description": "查询一个商品的名称、价格和规格。",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "string"}},
                    "required": ["product_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_stock",
                "description": "查询一个商品的库存。",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "string"}},
                    "required": ["product_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "AgentOutput",
                "description": "返回给客服服务的结构化结果。",
                "parameters": AGENT_OUTPUT_SCHEMA,
            },
        },
    ]


def render_messages(messages: list[dict], add_generation_prompt: bool = False, tokenizer=None) -> str:
    cleaned = [clean_message(message) for message in messages]
    if tokenizer is not None:
        try:
            return tokenizer.apply_chat_template(
                cleaned,
                tools=openai_tools(),
                add_generation_prompt=add_generation_prompt,
                tokenize=False,
            )
        except (TypeError, ValueError):
            try:
                return tokenizer.apply_chat_template(
                    cleaned,
                    add_generation_prompt=add_generation_prompt,
                    tokenize=False,
                )
            except (TypeError, ValueError):
                pass
    return render_qwen(cleaned, add_generation_prompt)


def clean_message(message: dict) -> dict:
    cleaned = {"role": message["role"], "content": message.get("content") or ""}
    if message.get("tool_calls"):
        cleaned["tool_calls"] = message["tool_calls"]
    if message.get("tool_call_id"):
        cleaned["tool_call_id"] = message["tool_call_id"]
    return cleaned


def render_qwen(messages: list[dict], add_generation_prompt: bool) -> str:
    chunks = [render_qwen_message(message) for message in messages]
    text = "\n".join(chunks)
    if add_generation_prompt:
        text += "\n<|im_start|>assistant\n"
    return text


TOOL_CALL_PATTERN = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def extract_payload(text: str):
    raw = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    matched = TOOL_CALL_PATTERN.search(raw)
    if matched:
        raw = matched.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None


def render_qwen_message(message: dict) -> str:
    role = message["role"]
    if role == "tool":
        content = message.get("content") or ""
        return (
            "<|im_start|>user\n"
            f"<tool_response>\n{content}\n</tool_response><|im_end|>"
        )
    calls = message.get("tool_calls") or []
    if calls:
        bodies = []
        for call in calls:
            function = call["function"]
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"raw": arguments}
            payload = json.dumps(
                {"name": function["name"], "arguments": arguments},
                ensure_ascii=False,
            )
            bodies.append(f"<tool_call>\n{payload}\n</tool_call>")
        return "<|im_start|>assistant\n" + "\n".join(bodies) + "<|im_end|>"
    content = message.get("content") or ""
    return f"<|im_start|>{role}\n{content}<|im_end|>"
