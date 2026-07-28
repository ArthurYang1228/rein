"""FunctionTool / register_tool 的單元測試。

例外處理尚未實作,失敗情境先用最廣的 Exception 接住;
等實際的例外型別(例如 ToolRegistrationError)實作完成後,
這幾個 pytest.raises(Exception) 要收斂成對應的具體型別。
"""

import pytest

from adapters.tool_kinds.FunctionTool import FunctionTool, register_tool
from core.ToolCatalog import ToolCatalog


def add(a: float, b: float) -> float:
    """兩數相加。"""
    return a + b


def test_function_tool_wraps_metadata_from_signature() -> None:
    tool = FunctionTool(add)

    assert tool.name == "add"
    assert tool.description == "兩數相加。"
    assert set(tool.input_schema) == {"a", "b"}
    assert tool.input_schema["a"].type == "float"


def test_function_tool_execute_calls_wrapped_function() -> None:
    tool = FunctionTool(add)

    assert tool.execute(1, 2) == 3


def test_register_tool_returns_original_function() -> None:
    registered = register_tool(add)

    assert registered is add
    assert registered(1, 2) == 3


def test_register_tool_adds_to_catalog() -> None:
    register_tool(add)

    assert ToolCatalog.is_registered("add")
    assert ToolCatalog.get("add").execute(2, 3) == 5


def test_missing_docstring_raises() -> None:
    def no_doc(a: float) -> float:
        return a

    with pytest.raises(Exception):  # noqa: B017 - 例外型別尚未定案
        FunctionTool(no_doc)


def test_missing_type_annotation_raises() -> None:
    def missing_annotation(a) -> float:  # type: ignore[no-untyped-def]
        """缺型別註記。"""
        return a  # type: ignore[no-any-return]

    with pytest.raises(Exception):  # noqa: B017 - 例外型別尚未定案
        FunctionTool(missing_annotation)


def test_unsupported_type_raises() -> None:
    class NotSupported:
        """不在支援清單內的型別。"""

    def unsupported(a: NotSupported) -> None:
        """型別不支援。"""

    with pytest.raises(Exception):  # noqa: B017 - 例外型別尚未定案
        FunctionTool(unsupported)
