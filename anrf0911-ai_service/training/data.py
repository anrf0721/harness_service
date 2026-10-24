"""把客服协议编成 SFT / GRPO 样本。

每条样本是一次模型调用，而不是一整段会话拼在一条系统提示里。
这和线上一致：动态系统提示、工具消息、最后用 AgentOutput 工具返回结构化结果。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from anrf0911_ai.agent.prompt import build_support_prompt
from anrf0911_ai.agent.skills.catalog import SkillCode
from anrf0911_ai.app.schemas.agent import ReplyType


ANSWER_TOOL = "AgentOutput"
BUSINESS_HINTS = ("订单", "物流", "售后", "库存", "价格", "发货", "退款", "退货")


@dataclass
class Sample:
    sample_id: str
    task: str
    question: str
    messages: list[dict]
    tool_evidence: list[dict]
    completion: str

    def to_row(self) -> dict:
        row = asdict(self)
        row["tool_evidence"] = json.dumps(self.tool_evidence, ensure_ascii=False)
        return row


def output_json(
    reply_type: str,
    reply_content: str,
    handoff_request: dict | None = None,
    page_action_request: dict | None = None,
) -> str:
    return json.dumps(
        {
            "reply_type": reply_type,
            "reply_content": reply_content,
            "handoff_request": handoff_request,
            "page_action_request": page_action_request,
        },
        ensure_ascii=False,
    )


def tool_call(call_id: str, name: str, arguments: dict) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments, ensure_ascii=False),
        },
    }


def assistant_tool_message(call_id: str, name: str, arguments: dict) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [tool_call(call_id, name, arguments)],
    }


def tool_result_message(call_id: str, payload: dict) -> dict:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(payload, ensure_ascii=False),
    }


def system_message(skill: SkillCode | None) -> dict:
    return {"role": "system", "content": build_support_prompt(skill)}


def order_result(order_id: str, status: str, amount: str) -> dict:
    return {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": {
            "id": order_id,
            "status": status,
            "total_amount": amount,
        },
    }


def failed_result(message: str) -> dict:
    return {
        "success": False,
        "code": "TOOL_CALL_FAILED",
        "message": message,
        "failure_type": "SERVICE_CALL",
    }


def evidence(tool_name: str, arguments: dict, result: dict, success: bool) -> dict:
    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "success": success,
    }


def answer_sample(
    sample_id: str,
    question: str,
    skill: SkillCode | None,
    calls: list[tuple[str, str, dict, dict, bool]],
    completion: str,
) -> Sample:
    messages = [system_message(skill), {"role": "user", "content": question}]
    tool_evidence = []
    for call_id, name, arguments, result, success in calls:
        messages.append(assistant_tool_message(call_id, name, arguments))
        messages.append(tool_result_message(call_id, result))
        tool_evidence.append(evidence(name, arguments, result, success))
    arguments = json.loads(completion)
    messages.append(assistant_tool_message("call_out", ANSWER_TOOL, arguments))
    return Sample(
        sample_id=sample_id,
        task="answer",
        question=question,
        messages=messages,
        tool_evidence=tool_evidence,
        completion=completion,
    )


def tool_sample(
    sample_id: str,
    question: str,
    skill: SkillCode | None,
    tool_name: str,
    arguments: dict,
) -> Sample:
    completion = json.dumps(
        {"name": tool_name, "arguments": arguments},
        ensure_ascii=False,
    )
    messages = [
        system_message(skill),
        {"role": "user", "content": question},
        assistant_tool_message("call_tool", tool_name, arguments),
    ]
    return Sample(
        sample_id=sample_id,
        task="tool",
        question=question,
        messages=messages,
        tool_evidence=[],
        completion=completion,
    )


def build_samples() -> list[Sample]:
    decline = (
        "暂时无法取得可靠的订单、商品、物流或售后信息，"
        "因此现在不能确认结果，请稍后重试。"
    )
    samples = [
        tool_sample(
            "tool-load-order",
            "订单 ORDER_001 发货了吗？",
            None,
            "load_skill",
            {"skill_code": SkillCode.ORDER_SERVICE.value},
        ),
        tool_sample(
            "tool-get-order",
            "订单 ORDER_001 发货了吗？",
            SkillCode.ORDER_SERVICE,
            "get_order",
            {"order_id": "ORDER_001"},
        ),
        tool_sample(
            "tool-list-orders",
            "帮我看看我有哪些订单",
            SkillCode.ORDER_SERVICE,
            "list_orders",
            {},
        ),
        tool_sample(
            "tool-load-product",
            "这款手机还有货吗？",
            None,
            "load_skill",
            {"skill_code": SkillCode.PRODUCT_SERVICE.value},
        ),
        tool_sample(
            "tool-search-product",
            "帮我搜一下手机",
            SkillCode.PRODUCT_SERVICE,
            "search_products",
            {"query": "手机"},
        ),
        tool_sample(
            "tool-load-logistics",
            "ORDER_001 到哪了？",
            None,
            "load_skill",
            {"skill_code": SkillCode.LOGISTICS_SERVICE.value},
        ),
        tool_sample(
            "tool-get-logistics",
            "ORDER_001 到哪了？",
            SkillCode.LOGISTICS_SERVICE,
            "get_logistics",
            {"order_id": "ORDER_001"},
        ),
        tool_sample(
            "tool-after-sales",
            "我的售后处理得怎么样了？",
            SkillCode.AFTER_SALES_SERVICE,
            "list_after_sales",
            {},
        ),
        answer_sample(
            "answer-handoff",
            "我要转人工客服",
            None,
            [],
            output_json(
                ReplyType.REQUEST_HANDOFF,
                "已为你转接人工客服。",
                {"reason_code": "USER_REQUESTED", "summary": "用户要求转人工"},
            ),
        ),
        answer_sample(
            "answer-clarify-order",
            "帮我查一下订单",
            SkillCode.ORDER_SERVICE,
            [],
            output_json(ReplyType.CLARIFY, "请提供订单编号，我再帮你查询。"),
        ),
        answer_sample(
            "answer-policy",
            "你们平台规则是什么？",
            SkillCode.POLICY_SERVICE,
            [],
            output_json(ReplyType.CLARIFY, "请说明你想了解的规则，例如发货、退货或售后。"),
        ),
        answer_sample(
            "answer-order-failed",
            "订单 ORDER_001 现在什么状态？",
            SkillCode.ORDER_SERVICE,
            [(
                "call_order",
                "get_order",
                {"order_id": "ORDER_001"},
                failed_result("暂时无法取得可靠的业务数据"),
                False,
            )],
            output_json(ReplyType.DECLINE, decline),
        ),
    ]
    samples.extend(order_answer_samples())
    samples.extend(other_answer_samples())
    return samples


def order_answer_samples() -> list[Sample]:
    rows = []
    cases = (
        ("ORDER_001", "pending_shipment", "899.00", "待发货", "CANCEL_ORDER"),
        ("ORDER_002", "paid", "199.00", "已支付", "EDIT_ADDRESS"),
        ("ORDER_003", "shipped", "399.00", "已发货", "OPEN_ORDER_DETAIL"),
        ("ORDER_004", "completed", "89.00", "已完成", "VIEW_AFTER_SALES"),
    )
    for order_id, status, amount, label, action in cases:
        result = order_result(order_id, status, amount)
        amount_text = amount.removesuffix(".00") if amount.endswith(".00") else amount
        rows.append(
            answer_sample(
                f"answer-{order_id.lower()}-{status}",
                f"订单 {order_id} 现在什么状态？",
                SkillCode.ORDER_SERVICE,
                [("call_order", "get_order", {"order_id": order_id}, result, True)],
                output_json(
                    ReplyType.ANSWER,
                    f"订单 {order_id} 当前{label}，总金额为 {amount_text} 元。",
                    page_action_request={
                        "action_code": action,
                        "resource_id": order_id,
                    },
                ),
            )
        )
    listed = {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": [
            {"id": "ORDER_001", "status": "pending_shipment", "total_amount": "899.00"},
            {"id": "ORDER_002", "status": "paid", "total_amount": "199.00"},
        ],
    }
    rows.append(
        answer_sample(
            "answer-list-orders",
            "帮我看看我有哪些订单",
            SkillCode.ORDER_SERVICE,
            [("call_list", "list_orders", {}, listed, True)],
            output_json(
                ReplyType.ANSWER,
                "你有两笔订单：ORDER_001 当前待发货，总金额为 899 元；ORDER_002 当前已支付，总金额为 199 元。",
                page_action_request={"action_code": "BROWSE_ORDERS"},
            ),
        )
    )
    return rows


def other_answer_samples() -> list[Sample]:
    product = {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": {"id": "PRODUCT_001", "price": "199.00", "name": "手机"},
    }
    stock = {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": {"product_id": "PRODUCT_001", "stock": 5},
    }
    logistics = {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": {"order_id": "ORDER_001", "status": "in_transit", "company": "顺丰"},
    }
    after_sale = {
        "success": True,
        "code": "OK",
        "message": "查询成功",
        "data": [{"id": "AS_001", "order_id": "ORDER_001", "status": "processing"}],
    }
    return [
        answer_sample(
            "answer-product",
            "PRODUCT_001 多少钱，还有货吗？",
            SkillCode.PRODUCT_SERVICE,
            [
                ("call_product", "get_product", {"product_id": "PRODUCT_001"}, product, True),
                ("call_stock", "get_product_stock", {"product_id": "PRODUCT_001"}, stock, True),
            ],
            output_json(
                ReplyType.ANSWER,
                "商品 PRODUCT_001 价格为 199 元，剩余 5 件。",
            ),
        ),
        answer_sample(
            "answer-logistics",
            "ORDER_001 到哪了？",
            SkillCode.LOGISTICS_SERVICE,
            [(
                "call_logistics",
                "get_logistics",
                {"order_id": "ORDER_001"},
                logistics,
                True,
            )],
            output_json(ReplyType.ANSWER, "订单 ORDER_001 的物流状态为运输中。"),
        ),
        answer_sample(
            "answer-after-sale",
            "我的售后处理得怎么样了？",
            SkillCode.AFTER_SALES_SERVICE,
            [("call_after", "list_after_sales", {}, after_sale, True)],
            output_json(ReplyType.ANSWER, "售后 AS_001 当前处理中。"),
        ),
    ]


def write_jsonl(path) -> int:
    rows = [sample.to_row() for sample in build_samples()]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def load_jsonl(path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
