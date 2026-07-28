"""計算機工具。"""

from adapters.tool_kinds.FunctionTool import register_tool


@register_tool
def add(num1: float, num2: float) -> float:
    """兩數的加法"""
    return num1 + num2
    """Tool 介面的計算機實作,供 agent 執行數學運算。"""
