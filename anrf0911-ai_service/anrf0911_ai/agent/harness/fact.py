"""
author: anrf
date:9/22/2026
desc:
"""
import re
from decimal import Decimal
from enum import StrEnum

from pydantic.dataclasses import dataclass

from anrf0911_ai.agent.harness.snapshot import ToolCallSnapshot


class FactCategory(StrEnum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STATUS = "STATUS"

STATUS_CODE_MAP = {
    "已支付": "paid",
    "待发货": "pending_shipment",
    "已发货": "shipped",
    "已完成": "completed",
    "已取消": "cancelled",
    "已退款": "refunded",
    "运输中": "in_transit",
    "已签收": "delivered",
    "待处理": "pending",
    "已通过": "approved",
    "处理中": "processing",
    "已拒绝": "rejected",
}

@dataclass(frozen=True)
class BusinessFact:
    category: FactCategory
    value: str

class FactExtractor:
    resource_id_pattern = re.compile(
        r"\b(?:ORDER|PRODUCT|AS)[_-][A-Z0-9_-]+\b",
        re.IGNORECASE,
    )
    labeled_number_pattern = re.compile(
        r"(?:金额|总价|价格|库存|数量)"
        r"(?:为|是|有|剩余|还剩|：|:)?\s*"
        r"[¥￥]?\s*(\d+(?:\.\d+)?)"
    )
    unit_number_pattern = re.compile(
        r"(?:[¥￥]\s*(\d+(?:\.\d+)?)|"
        r"(\d+(?:\.\d+)?)\s*(?:元|件|个|台|套))"
    )

    @classmethod
    def extract(cls,reply_content:str):
        facts: dict[BusinessFact, None] = {}

        for resource_id in cls.resource_id_pattern.findall(reply_content):
            normalized_id = resource_id.upper().replace("-", "_")
            facts[BusinessFact(FactCategory.IDENTIFIER,normalized_id)] = None

        for number in cls.labeled_number_pattern.findall(reply_content):
            facts[BusinessFact(FactCategory.NUMBER,number)] = None

        for first_number, second_number in cls.unit_number_pattern.findall(reply_content):
            number = first_number or second_number
            facts[BusinessFact(FactCategory.NUMBER,number)] = None

        for status_label in STATUS_CODE_MAP:
            if status_label in reply_content:
                facts[BusinessFact(FactCategory.STATUS,status_label)] = None

        return tuple(facts.keys())


class FactValidationError(Exception):
    def __init__(self, facts):
        self.code = "UNSUPPORTED_FACT"
        values = "、".join(fact.value for fact in facts)
        self.message = f"回复中的业务事实缺少工具支持：{values}"
        super().__init__(self.message)


class FactChecker:
    def get_unsupported_facts(self, reply_content, tool_calls:tuple[ToolCallSnapshot, ...]):
        facts = FactExtractor.extract(reply_content)
        evidence = []

        for tool_call in tool_calls:
            if tool_call.success is not True or not tool_call.result:
                continue
            evidence.extend(self.flat(tool_call.arguments))
            if "data" in tool_call.result:
                evidence.extend(self.flat(tool_call.result["data"]))

        unsupported = []
        for fact in facts:
            if not self.matches(fact, evidence):
                unsupported.append(fact)
        return tuple(unsupported)

    def flat(self, value):
        if isinstance(value, dict):
            found = []
            for item in value.values():
                found.extend(self.flat(item))
            return found
        if isinstance(value, list):
            found = []
            for item in value:
                found.extend(self.flat(item))
            return found
        return [value]

    def matches(self, fact, evidence):
        if fact.category == FactCategory.NUMBER:
            wanted = Decimal(fact.value)
            for value in evidence:
                text = str(value).strip()
                if text.replace(".", "", 1).isdigit() and Decimal(text) == wanted:
                    return True
            return False

        wanted = str(fact.value).strip().upper().replace("-", "_")
        words = [
            str(value).strip().upper().replace("-", "_")
            for value in evidence
        ]
        if fact.category == FactCategory.STATUS:
            code = STATUS_CODE_MAP[fact.value].upper()
            return wanted in words or code in words
        return wanted in words

    def check(self,reply_content,tool_calls):
        unsupported = self.get_unsupported_facts(reply_content,tool_calls)
        if unsupported:
            raise FactValidationError(unsupported)

if __name__ == "__main__":
    calls = (
        ToolCallSnapshot(
            tool_name="get_order",
            arguments={"order_id": "ORDER_001"},
            result={
                "success": True,
                "code": "OK",
                "data": {
                    "id": "ORDER_001",
                    "status": "pending_shipment",
                    "total_amount": "899.00",
                },
            },
            success=True,
        ),
    )
    checker = FactChecker()
    good = "订单 ORDER_001 当前待发货，总金额为 899 元。"
    bad = "订单 ORDER_001 当前已发货，总金额为 399 元。"

    checker.check(good, calls)
    print("通过")

    try:
        checker.check(bad, calls)
    except FactValidationError as error:
        print(error.code)
        print(error.message)

