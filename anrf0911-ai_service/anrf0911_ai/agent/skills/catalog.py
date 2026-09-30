"""
author: anrf
date:9/29/2026
desc:
"""
from dataclasses import dataclass
from enum import StrEnum


class SkillCode(StrEnum):
    PRODUCT_SERVICE = "product-service"
    ORDER_SERVICE = "order-service"
    LOGISTICS_SERVICE = "logistics-service"
    POLICY_SERVICE = "policy-service"
    AFTER_SALES_SERVICE = "after-sales-service"


@dataclass(frozen=True)
class SkillDefinition:
    code: SkillCode
    description: str
    guidance: tuple[str, ...]
    tools: tuple[str, ...]


class SkillCatalog:
    def __init__(self, definitions: tuple[SkillDefinition, ...]):
        self.definitions = {
            item.code: item
            for item in definitions
        }

    def get_skill(self, skill_code: SkillCode) -> SkillDefinition:
        return self.definitions[skill_code]

    def render_index(self) -> str:
        return "\n".join(
            f"- {skill.code}: {skill.description}"
            for skill in self.definitions.values()
        )


SKILL_CATALOG = SkillCatalog(
    (
        SkillDefinition(
            code=SkillCode.PRODUCT_SERVICE,
            description="商品搜索、详情、价格和库存",
            guidance=(
                "查询入口：用户没有指明商品时，先使用 search_products。",
                "工具选择：商品详情使用 get_product，库存使用 get_product_stock。",
                "可信依据：价格、库存和商品状态只能来自成功的工具结果。",
                "边界处理：工具失败时不得猜测价格或库存。",
            ),
            tools=("search_products", "get_product", "get_product_stock"),
        ),
        SkillDefinition(
            code=SkillCode.ORDER_SERVICE,
            description="订单列表、详情、状态和金额",
            guidance=(
                "查询入口：用户没有提供订单编号时，先使用 list_orders。",
                "工具选择：某一笔订单的状态和金额使用 get_order。",
                "可信依据：订单状态和金额只能来自成功的工具结果。",
                "边界处理：不能取消订单、退款或修改地址。",
            ),
            tools=("list_orders", "get_order"),
        ),
        SkillDefinition(
            code=SkillCode.LOGISTICS_SERVICE,
            description="具体订单的发货状态、承运公司和物流轨迹",
            guidance=(
                "查询入口：用户没有提供订单编号时，先使用 list_orders。",
                "工具选择：订单基础信息使用 get_order，配送进度使用 get_logistics。",
                "可信依据：物流公司和轨迹只能来自 get_logistics 的成功结果。",
                "边界处理：物流工具失败时不得猜测配送进度。",
            ),
            tools=("list_orders", "get_order", "get_logistics"),
        ),
        SkillDefinition(
            code=SkillCode.POLICY_SERVICE,
            description="平台通用规则和服务政策，不查询用户的实时订单",
            guidance=(
                "查询入口：只解释平台通用规则，不查询某一笔订单。",
                "工具选择：这个领域没有业务查询工具。",
                "可信依据：没有工具结果时，不得编造用户的订单或售后状态。",
                "边界处理：用户要查自己的售后记录时，应切换到售后领域。",
            ),
            tools=(),
        ),
        SkillDefinition(
            code=SkillCode.AFTER_SALES_SERVICE,
            description="用户实际售后记录、状态和进度",
            guidance=(
                "查询入口：使用 list_after_sales 查询当前用户的售后记录。",
                "工具选择：只读取售后记录，不创建或修改售后。",
                "可信依据：售后状态只能来自成功的工具结果。",
                "边界处理：没有记录时不得猜测售后进度。",
            ),
            tools=("list_after_sales",),
        ),
    )
)


if __name__ == "__main__":
    print(SKILL_CATALOG.render_index())
    skill = SKILL_CATALOG.get_skill(SkillCode.LOGISTICS_SERVICE)
    print(skill.tools)
