"""
author: anrf
date:9/22/2026
desc:
"""
from dataclasses import dataclass
from enum import StrEnum

from langchain_core.tools import BaseTool

from anrf0911_ai.agent.tools.read import (
    get_logistics,
    get_order,
    get_product,
    get_product_stock,
    list_after_sales,
    list_orders,
    search_products,
)


class ToolCategory(StrEnum):
    BUSINESS = "BUSINESS"
    KNOWLEDGE = "KNOWLEDGE"


@dataclass(frozen=True)
class ToolDefinition:
    tool: BaseTool
    category: ToolCategory


class ToolCatalog:
    def __init__(self, definitions: tuple[ToolDefinition, ...]):
        names = [item.tool.name for item in definitions]
        if len(names) != len(set(names)):
            raise ValueError("工具名称重复")
        self.definitions = {
            item.tool.name: item
            for item in definitions
        }

    def get_agent_tools(self) -> list[BaseTool]:
        return [item.tool for item in self.definitions.values()]

    def get_tool_definition(self, tool_name: str) -> ToolDefinition:
        return self.definitions[tool_name]

    def get_tool_category(self, tool_name: str) -> ToolCategory:
        return self.get_tool_definition(tool_name).category


TOOL_CATALOG = ToolCatalog(
    (
        ToolDefinition(search_products, ToolCategory.BUSINESS),
        ToolDefinition(get_product, ToolCategory.BUSINESS),
        ToolDefinition(get_product_stock, ToolCategory.BUSINESS),
        ToolDefinition(list_orders, ToolCategory.BUSINESS),
        ToolDefinition(get_order, ToolCategory.BUSINESS),
        ToolDefinition(get_logistics, ToolCategory.BUSINESS),
        ToolDefinition(list_after_sales, ToolCategory.BUSINESS),
    )
)


if __name__ == "__main__":
    for tool in TOOL_CATALOG.get_agent_tools():
        print(tool.name, TOOL_CATALOG.get_tool_category(tool.name))
