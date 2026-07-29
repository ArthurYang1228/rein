"""計算機工具。"""

from adapters.tool_kinds.function_tool import register_tool


@register_tool
def add(num1: float, num2: float) -> float:
    """兩數的加法"""
    return num1 + num2


@register_tool
def subtract(num1: float, num2: float) -> float:
    """兩數的減法"""
    return num1 - num2


@register_tool
def multiply(num1: float, num2: float) -> float:
    """兩數的乘法"""
    return num1 * num2


@register_tool
def divide(num1: float, num2: float, int_division: bool) -> float:
    """兩數的除法"""
    if int_division:
        return num1 // num2
    else:
        return num1 / num2
