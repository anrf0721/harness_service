"""
author: anrf
date:9/22/2026
desc:
"""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

class ToolFailureType(StrEnum):
    BUSINESS = "BUSINESS"
    SERVICE_CALL = "SERVICE_CALL"
    CONTRACT = "CONTRACT"


class ToolResult[ResultData](BaseModel):
    success: bool
    code: str
    message: str
    data: ResultData | None = None
    failure_type: ToolFailureType | None = None


class ProductData(BaseModel):
    id: str
    name: str
    category: str
    price: Decimal = Field(ge=0)
    status: str
    description: str
    specs: dict[str, Any]


class ProductStockData(BaseModel):
    product_id: str
    stock: int = Field(ge=0)
    status: str


class OrderItemData(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class OrderData(BaseModel):
    id: str
    status: str
    total_amount: Decimal = Field(ge=0)
    created_at: datetime
    items: list[OrderItemData]


class LogisticsEventData(BaseModel):
    time: str
    description: str


class LogisticsData(BaseModel):
    order_id: str
    company: str
    tracking_number: str
    status: str
    latest_event: str
    events: list[LogisticsEventData]


class AfterSaleData(BaseModel):
    id: str
    order_id: str
    kind: str
    reason: str
    status: str
    created_at: datetime


if __name__ == "__main__":
    print(
        ToolResult[ProductData](
            success=True,
            code="OK",
            message="商品查询成功",
            data={
                "id": "P1",
                "name": "手机",
                "category": "数码",
                "price": "99.00",
                "status": "on_sale",
                "description": "测试",
                "specs": {},
            },
        )
    )
