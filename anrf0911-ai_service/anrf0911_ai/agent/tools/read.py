"""
author: anrf
date:9/22/2026
desc:
"""
from urllib.parse import quote

from langchain.tools import ToolRuntime, tool

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.tools.client import EcommerceClient
from anrf0911_ai.agent.tools.executor import ToolExecutor
from anrf0911_ai.agent.tools.output import (
    AfterSaleData,
    LogisticsData,
    OrderData,
    ProductData,
    ProductStockData,
)


tool_executor = ToolExecutor()


@tool
async def get_order(
    order_id: str,
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """查询当前用户的一条订单详情，包括订单状态、金额和商品信息。
    必须提供明确的订单编号。只查询，不取消订单或退款。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("订单查询缺少工具调用编号")

    # 1. 整理订单编号，例如 order-001 变成 ORDER_001
    order_id = order_id.strip().upper().replace("-", "_")

    # 2. 使用当前用户的令牌创建客户端
    client = EcommerceClient(runtime.context.access_token)

    # 3. 定义真正请求电商接口的函数
    async def request_order():
        return await client.get_json(
            f"/orders/{quote(order_id, safe='')}"
        )

    # 4. 交给执行器记录、查询、校验和保存
    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="get_order",
        arguments={"order_id": order_id},
        operation=request_order,
        output_schema=OrderData,
    )

@tool
async def list_orders(
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """查询当前用户的订单列表。用户没有提供订单编号时使用，仅查询数据。"""

    if runtime.tool_call_id is None:
        raise RuntimeError("订单列表查询缺少工具调用编号")

    client = EcommerceClient(runtime.context.access_token)

    async def request_orders():
        return await client.get_json("/orders")

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="list_orders",
        arguments={},
        operation=request_orders,
        output_schema=list[OrderData],
    )


@tool
async def get_logistics(
    order_id: str,
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """查询一个订单的物流公司、运单号和配送轨迹。
    必须提供明确的订单编号。只查询，不修改配送。
    订单状态和金额请用 get_order。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("物流查询缺少工具调用编号")

    order_id = order_id.strip().upper().replace("-", "_")
    client = EcommerceClient(runtime.context.access_token)

    async def request_logistics():
        return await client.get_json(
            f"/orders/{quote(order_id, safe='')}/logistics"
        )

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="get_logistics",
        arguments={"order_id": order_id},
        operation=request_logistics,
        output_schema=LogisticsData,
    )


@tool
async def list_after_sales(
    runtime: ToolRuntime[AgentRuntimeContext],
    order_id: str = "",
) -> str:
    """查询当前用户的退款、退货或换货记录。
    有订单号就只查这一单，没有就查该用户全部售后。只查询，不申请退款。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("售后查询缺少工具调用编号")

    order_id = (order_id or "").strip().upper().replace("-", "_")
    params = {"order_id": order_id} if order_id else None
    client = EcommerceClient(runtime.context.access_token)

    async def request_after_sales():
        return await client.get_json("/after-sales", params)

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="list_after_sales",
        arguments=params or {},
        operation=request_after_sales,
        output_schema=list[AfterSaleData],
    )


@tool
async def search_products(
    query: str,
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """按名称、类别或购买需求搜索在售商品。
    用户没有商品编号时使用。只查询，不查库存。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("商品搜索缺少工具调用编号")

    query = query.strip()
    client = EcommerceClient(runtime.context.access_token)

    async def request_products():
        return await client.get_json("/products", {"query": query})

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="search_products",
        arguments={"query": query},
        operation=request_products,
        output_schema=list[ProductData],
    )


@tool
async def get_product(
    product_id: str,
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """查询一个商品的名称、价格、描述和规格。
    必须提供商品编号。只查商品资料，不查库存。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("商品详情缺少工具调用编号")

    product_id = product_id.strip().upper().replace("-", "_")
    client = EcommerceClient(runtime.context.access_token)

    async def request_product():
        return await client.get_json(
            f"/products/{quote(product_id, safe='')}"
        )

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="get_product",
        arguments={"product_id": product_id},
        operation=request_product,
        output_schema=ProductData,
    )


@tool
async def get_product_stock(
    product_id: str,
    runtime: ToolRuntime[AgentRuntimeContext],
) -> str:
    """查询一个商品的实时库存和销售状态。
    必须提供商品编号。只查有没有货，不查价格和描述。
    """
    if runtime.tool_call_id is None:
        raise RuntimeError("库存查询缺少工具调用编号")

    product_id = product_id.strip().upper().replace("-", "_")
    client = EcommerceClient(runtime.context.access_token)

    async def request_stock():
        return await client.get_json(
            f"/products/{quote(product_id, safe='')}/stock"
        )

    return await tool_executor.execute(
        runtime_context=runtime.context,
        tool_call_id=runtime.tool_call_id,
        tool_name="get_product_stock",
        arguments={"product_id": product_id},
        operation=request_stock,
        output_schema=ProductStockData,
    )


if __name__ == "__main__":
    from anrf0911_ai.app.db import SessionFactory
    from anrf0911_ai.app.services.auth import AuthService, CurrentUser
    from anrf0911_ai.common.utils import get_uid, run_async
    from anrf0911_ai.models.models import AgentRun

    async def main():
        user_id = input("请输入测试用户ID：").strip()
        choice = input("1订单详情 2订单列表 3物流 4售后 5搜商品 6商品详情 7库存：").strip()
        order_id = ""
        keyword = ""
        product_id = ""
        if choice == "5":
            keyword = input("请输入商品关键词：").strip()
        elif choice in {"6", "7"}:
            product_id = input("请输入商品编号：").strip()
        elif choice in {"1", "3", "4"}:
            order_id = input("请输入订单号，售后可以留空：").strip()

        user = CurrentUser(user_id=user_id, role="customer")
        token = AuthService().encode_access_token(user)

        # 2. 先创建运行记录，工具调用记录需要关联它
        async with SessionFactory() as session:
            run = AgentRun(
                conversation_id="test_order",
                turn_id=get_uid("test_turn"),
                user_id=user.user_id,
                state="TEST",
                input_context={"order_id": order_id},
            )
            session.add(run)
            await session.commit()

        # 3. 准备本次运行的信息
        context = AgentRuntimeContext(
            run_id=run.id,
            conversation_id=run.conversation_id,
            user_id=user.user_id,
            access_token=token,
        )

        # 4. 单独测试时，手动准备工具运行环境
        runtime = ToolRuntime(
            context=context,
            tool_call_id=get_uid("call"),
            state={},
            config={},
            stream_writer=print,
            store=None,
        )

        # 5. 按输入选择要测的工具
        if choice == "2":
            result = await list_orders.ainvoke(
                {
                    "runtime": runtime,
                }
            )
        elif choice == "3":
            result = await get_logistics.ainvoke(
                {
                    "order_id": order_id,
                    "runtime": runtime,
                }
            )
        elif choice == "4":
            result = await list_after_sales.ainvoke(
                {
                    "order_id": order_id,
                    "runtime": runtime,
                }
            )
        elif choice == "5":
            result = await search_products.ainvoke(
                {
                    "query": keyword,
                    "runtime": runtime,
                }
            )
        elif choice == "6":
            result = await get_product.ainvoke(
                {
                    "product_id": product_id,
                    "runtime": runtime,
                }
            )
        elif choice == "7":
            result = await get_product_stock.ainvoke(
                {
                    "product_id": product_id,
                    "runtime": runtime,
                }
            )
        else:
            result = await get_order.ainvoke(
                {
                    "order_id": order_id,
                    "runtime": runtime,
                }
            )

        print("测试运行ID：", run.id)
        print("查询结果：", result)

    run_async(main())