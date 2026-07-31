"""tools/calculator.py 的單元測試。"""

import pytest

from core.tool_catalog import ToolCatalog
from tools.calculator import add, divide, multiply, subtract


def test_add_returns_sum() -> None:
    assert add(1, 2) == 3


def test_subtract_returns_difference() -> None:
    assert subtract(5, 2) == 3


def test_multiply_returns_product() -> None:
    assert multiply(3, 4) == 12


def test_divide_returns_float_division_by_default() -> None:
    assert divide(7, 2, False) == 3.5


def test_divide_returns_integer_division_when_requested() -> None:
    assert divide(7, 2, True) == 3


@pytest.mark.parametrize(
    ("tool_name", "num1", "num2", "expected"),
    [
        ("add", 2, 3, 5),
        ("subtract", 5, 2, 3),
        ("multiply", 3, 4, 12),
    ],
)
def test_registered_in_catalog_and_executes(
    tool_name: str, num1: float, num2: float, expected: float
) -> None:
    assert ToolCatalog.is_registered(tool_name)
    assert ToolCatalog.get(tool_name).execute(num1, num2) == expected


def test_divide_registered_in_catalog_and_executes() -> None:
    assert ToolCatalog.is_registered("divide")
    assert ToolCatalog.get("divide").execute(7, 2, False) == 3.5


@pytest.mark.parametrize(
    ("tool_name", "description", "param_names"),
    [
        ("add", "兩數的加法", {"num1", "num2"}),
        ("subtract", "兩數的減法", {"num1", "num2"}),
        ("multiply", "兩數的乘法", {"num1", "num2"}),
        ("divide", "兩數的除法", {"num1", "num2", "int_division"}),
    ],
)
def test_tool_info_matches_signature(
    tool_name: str, description: str, param_names: set[str]
) -> None:
    info = ToolCatalog.get(tool_name).get_info()

    assert info.name == tool_name
    assert info.description == description
    assert set(info.input_schema) == param_names
