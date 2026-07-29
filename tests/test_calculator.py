"""tools/calculator.py 的單元測試。"""

from core.tool_catalog import ToolCatalog
from tools.calculator import add


def test_add_returns_sum() -> None:
    assert add(1, 2) == 3


def test_add_registered_in_catalog() -> None:
    assert ToolCatalog.is_registered("add")

    tool = ToolCatalog.get("add")
    assert tool.execute(2, 3) == 5


def test_add_tool_info_matches_signature() -> None:
    info = ToolCatalog.get("add").get_info()

    assert info.name == "add"
    assert info.description == "兩數的加法"
    assert set(info.input_schema) == {"num1", "num2"}
    assert info.input_schema["num1"].type == "float"
    assert info.input_schema["num2"].type == "float"
