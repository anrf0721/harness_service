from time import perf_counter
from typing import Any

from pydantic import TypeAdapter, ValidationError

from anrf0911_ai.agent.context import AgentRuntimeContext
from anrf0911_ai.agent.tools.output import ToolResult, ToolFailureType
from anrf0911_ai.app.db import SessionFactory
from anrf0911_ai.models.models import AgentToolCall


class ToolExecutor:
    """负责业务工具的执行和结果检查。"""

    def validate_result(self, response_data, output_schema):
        """
        response_data：接口返回的数据。
        output_schema：本次查询应该符合的数据模型。
        """
        try:
            # 1. 检查外层格式
            result = ToolResult[Any].model_validate(response_data)

            # 2. 查询失败时，不再检查业务数据
            if not result.success:
                result.failure_type = ToolFailureType.BUSINESS
                return result

            result.failure_type = None

            # 3. 根据本次查询的数据模型，检查 data
            adapter = TypeAdapter(output_schema)
            data = adapter.validate_python(result.data)

            # 4. 转成适合保存和返回的普通数据
            # 只保留业务模型中定义的字段
            result.data = adapter.dump_python(data, mode="json")

            return result

        except ValidationError:
            # 数据不符合规则时，返回统一的失败结果
            return ToolResult[Any](
                success=False,
                code="INVALID_TOOL_RESULT",
                message="业务工具返回的数据不符合约定",
                failure_type=ToolFailureType.CONTRACT,

            )

    async def execute(
        self,
        runtime_context: AgentRuntimeContext,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
        operation,
        output_schema,
    ) -> str:
        # 1. 请求开始前，先保存一条调用记录
        async with SessionFactory() as session:
            record = AgentToolCall(
                run_id=runtime_context.run_id,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                arguments=arguments,
            )
            session.add(record)
            await session.commit()

            # 记住这条记录的主键，后面根据它更新结果
            record_id = record.id

        # 2. 开始计时，执行真正的查询函数
        started = perf_counter()

        try:
            response_data = await operation()
        except Exception:
            # 请求报错时，返回安全的失败说明
            result = ToolResult[Any](
                success=False,
                code="TOOL_CALL_FAILED",
                message="暂时无法取得可靠的业务数据",
                failure_type=ToolFailureType.SERVICE_CALL,

            )
        else:
            # 3. 请求正常返回后，检查数据是否符合规则
            result = self.validate_result(
                response_data,
                output_schema,
            )

        latency_ms = int((perf_counter() - started) * 1000)

        # 4. 查询结束后，更新之前保存的那条记录
        async with SessionFactory() as session:
            record = await session.get(AgentToolCall, record_id)

            if record is None:
                raise RuntimeError("工具调用记录不存在")

            record.result = result.model_dump(mode="json")
            record.success = result.success
            record.latency_ms = latency_ms

            await session.commit()

        # 5. 返回 JSON 字符串，供模型读取
        return result.model_dump_json()





def test_execute():
    import json

    from sqlalchemy import select

    from anrf0911_ai.agent.tools.output import ProductStockData
    from anrf0911_ai.common.utils import run_async
    from anrf0911_ai.models.models import AgentRun

    async def check():
        run_id = None
        try:
            async with SessionFactory() as session:
                run = AgentRun(
                    conversation_id="conv_test",
                    turn_id="turn_test",
                    user_id="user_test",
                    input_context={},
                )
                session.add(run)
                await session.commit()
                run_id = run.id

            context = AgentRuntimeContext(
                run_id=run_id,
                conversation_id="conv_test",
                user_id="user_test",
                access_token="test-token",
            )
            executor = ToolExecutor()

            async def request_ok():
                return {
                    "success": True,
                    "code": "OK",
                    "message": "库存查询成功",
                    "data": {
                        "product_id": "PRODUCT_001",
                        "stock": 10,
                        "status": "on_sale",
                    },
                }

            async def request_down():
                raise TimeoutError("连不上电商")

            ok_text = await executor.execute(
                context,
                "call_ok",
                "get_product_stock",
                {"product_id": "PRODUCT_001"},
                request_ok,
                ProductStockData,
            )
            down_text = await executor.execute(
                context,
                "call_down",
                "get_product_stock",
                {"product_id": "PRODUCT_001"},
                request_down,
                ProductStockData,
            )
            ok_result = json.loads(ok_text)
            down_result = json.loads(down_text)
            print(ok_result["success"], ok_result["failure_type"])
            print(down_result["code"], down_result["failure_type"])
            assert ok_result["success"] is True
            assert ok_result["failure_type"] is None
            assert down_result["code"] == "TOOL_CALL_FAILED"
            assert down_result["failure_type"] == "SERVICE_CALL"
        finally:
            if run_id is None:
                return
            async with SessionFactory() as session:
                calls = (
                    await session.scalars(
                        select(AgentToolCall).where(AgentToolCall.run_id == run_id)
                    )
                ).all()
                for call in calls:
                    await session.delete(call)
                run = await session.get(AgentRun, run_id)
                if run is not None:
                    await session.delete(run)
                await session.commit()

    run_async(check())


if __name__ == "__main__":
    from anrf0911_ai.agent.tools.output import ProductStockData

    response = {
        "success": True,
        "code": "OK",
        "message": "库存查询成功",
        "data": {
            "product_id": "PRODUCT_001",
            "stock": 10,
            "status": "on_sale",
        },
    }
    ok = ToolExecutor().validate_result(response, ProductStockData)
    print(ok.success, ok.failure_type)

    business = ToolExecutor().validate_result(
        {
            "success": False,
            "code": "NO_LOGISTICS",
            "message": "订单尚未产生物流信息",
            "data": None,
        },
        ProductStockData,
    )
    print(business.code, business.failure_type)

    bad = ToolExecutor().validate_result(
        {"success": True, "code": "OK", "message": "坏了", "data": {"stock": "很多"}},
        ProductStockData,
    )
    print(bad.code, bad.failure_type)
    test_execute()