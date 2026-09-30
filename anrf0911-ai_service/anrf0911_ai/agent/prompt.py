"""
author: anrf
date:9/19/2026
desc:
"""
from langchain.agents.middleware import ModelRequest, dynamic_prompt

from anrf0911_ai.agent.harness.action import ACTION_CATALOG
from anrf0911_ai.agent.skills.catalog import SKILL_CATALOG, SkillCode

BASE_PROMPT = """是电商平台的只读智能客服。用可信数据回答，不要编造订单或库存。
不能改订单、退款或改地址，这些引导用户去页面操作。

必须输出结构化结果，reply_type 只能是：
ANSWER：正常回答
CLARIFY：信息不够，请用户补充
DECLINE：非电商或没有依据，拒绝回答
REQUEST_HANDOFF：用户明确要人工，或投诉/风险需要人工
只有 REQUEST_HANDOFF 时才填 handoff_request。
不知道答案不要转人工，用 DECLINE 或 CLARIFY。

需要引导用户去页面时，只在 ANSWER 里填写 page_action_request。
只填 action_code，具体订单再填 resource_id，不要写网址。
BROWSE_ORDERS 不填 resource_id。
OPEN_ORDER_DETAIL、CANCEL_ORDER、EDIT_ADDRESS、APPLY_AFTER_SALE、VIEW_AFTER_SALES 必须填 get_order 已经查成功的订单号。
查单没成功就不要填动作。
DECLINE、CLARIFY、REQUEST_HANDOFF 不要填 page_action_request。
"""


def render_skill_section(active_skill_code: SkillCode | None) -> str:
    if active_skill_code is None:
        return "当前还没有领域。先调用 load_skill，只能选择：\n" + SKILL_CATALOG.render_index()
    skill = SKILL_CATALOG.get_skill(active_skill_code)
    return "\n".join((f"当前领域：{skill.code}", *skill.guidance))


def render_action_section() -> str:
    lines = ["可用页面动作："]
    for code, definition in ACTION_CATALOG.items():
        if definition.needs_order:
            lines.append(f"- {code}：填写 get_order 已确认的订单号")
        else:
            lines.append(f"- {code}：不填 resource_id")
    return "\n".join(lines)


def build_support_prompt(active_skill_code: SkillCode | None) -> str:
    return "\n\n".join((
        BASE_PROMPT,
        render_skill_section(active_skill_code),
        render_action_section(),
    ))


@dynamic_prompt
def support_prompt(request: ModelRequest) -> str:
    return build_support_prompt(request.state.get("active_skill_code"))


if __name__ == "__main__":
    empty = build_support_prompt(None)
    order = build_support_prompt(SkillCode.ORDER_SERVICE)
    print("order-service" in empty, "load_skill" in empty)
    print("当前领域：order-service" in order, "list_orders" in order, "search_products" in order)
    print("CANCEL_ORDER" in order, "BROWSE_ORDERS" in order)
