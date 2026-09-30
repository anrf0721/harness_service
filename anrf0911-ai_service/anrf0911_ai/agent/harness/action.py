"""
author: anrf
date:9/23/2026
desc:
"""
from dataclasses import dataclass
from urllib.parse import quote

from pydantic import BaseModel

from anrf0911_ai.agent.harness.snapshot import ToolCallSnapshot


class PageActionRequest(BaseModel):
    action_code: str
    resource_id: str | None = None


class PageAction(BaseModel):
    label: str
    description: str
    href: str


@dataclass(frozen=True)
class ActionDefinition:
    label: str
    description: str
    path_template: str
    needs_order: bool


ACTION_CATALOG = {
    "BROWSE_ORDERS": ActionDefinition(
        "查看我的订单", "进入我的订单列表", "/me", False
    ),
    "OPEN_ORDER_DETAIL": ActionDefinition(
        "查看订单详情", "进入订单详情查看状态与可用操作",
        "/me/orders/{resource_id}", True,
    ),
    "CANCEL_ORDER": ActionDefinition(
        "前往取消订单", "进入订单页面核对状态并确认取消",
        "/me/orders/{resource_id}/cancel", True,
    ),
    "EDIT_ADDRESS": ActionDefinition(
        "前往修改地址", "进入订单页面修改收货地址",
        "/me/orders/{resource_id}/address", True,
    ),
    "APPLY_AFTER_SALE": ActionDefinition(
        "申请售后", "进入订单页面填写售后申请",
        "/me/orders/{resource_id}/after-sale", True,
    ),
    "VIEW_AFTER_SALES": ActionDefinition(
        "查看售后进度", "进入订单页面查看售后记录",
        "/me/orders/{resource_id}?section=after-sales", True,
    ),
}


class ActionValidationError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(self.message)


class ActionValidator:
    def validate(self, request: PageActionRequest | None, tool_calls):
        if request is None:
            return None

        definition = ACTION_CATALOG.get(request.action_code)
        # print(definition)
        if definition is None:
            raise ActionValidationError(
                "MODEL_OUTPUT_INVALID",
                f"不支持的页面动作：{request.action_code}",
            )

        if not definition.needs_order:
            if request.resource_id:
                raise ActionValidationError(
                    "MODEL_OUTPUT_INVALID",
                    "查看订单列表不能携带订单编号",
                )
            return PageAction(
                label=definition.label,
                description=definition.description,
                href=definition.path_template,
            )

        if not request.resource_id:
            raise ActionValidationError(
                "MODEL_OUTPUT_INVALID",
                "这个动作必须提供订单编号",
            )

        order_id = request.resource_id.strip().upper().replace("-", "_")
        confirmed = False
        for call in tool_calls:
            if call.tool_name != "get_order" or call.success is not True:
                continue
            found = str(call.arguments.get("order_id", ""))
            found = found.strip().upper().replace("-", "_")
            if found == order_id:
                confirmed = True
                break

        if not confirmed:
            raise ActionValidationError(
                "UNVERIFIED_ACTION_RESOURCE",
                f"页面动作引用的订单未经工具确认：{order_id}",
            )

        href = definition.path_template.format(
            resource_id=quote(order_id, safe="")
        )
        return PageAction(
            label=definition.label,
            description=definition.description,
            href=href,
        )


if __name__ == "__main__":
    calls = (
        ToolCallSnapshot(
            tool_name="get_order",
            arguments={"order_id": "ORDER-001"},
            result={"data": {"id": "ORDER_001"}},
            success=True,
        ),
    )
    validator = ActionValidator()
    listed = validator.validate(
        PageActionRequest(action_code="BROWSE_ORDERS"),
        calls,
    )
    cancel = validator.validate(
        PageActionRequest(action_code="CANCEL_ORDER", resource_id="order-001"),
        calls,
    )
    print(listed.href)
    print(cancel.href)
    try:
        validator.validate(
            PageActionRequest(action_code="CANCEL_ORDER", resource_id="ORDER-999"),
            calls,
        )
    except ActionValidationError as error:
        print(error.code, error.message)
