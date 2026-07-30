"""FunctionTool / register_tool 的單元測試。"""

import pytest

from adapters.tool_kinds.function_tool import FunctionTool, register_tool
from core.exceptions import ToolExecutionError, ToolRegistrationError
from core.tool_catalog import ToolCatalog


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

    with pytest.raises(ToolRegistrationError, match="no_doc"):
        FunctionTool(no_doc)


def test_missing_type_annotation_raises() -> None:
    def missing_annotation(a) -> float:  # type: ignore[no-untyped-def]
        """缺型別註記。"""
        return a  # type: ignore[no-any-return]

    with pytest.raises(ToolRegistrationError, match="missing_annotation"):
        FunctionTool(missing_annotation)


def test_unsupported_type_raises() -> None:
    class NotSupported:
        """不在支援清單內的型別。"""

    def unsupported(a: NotSupported) -> None:
        """型別不支援。"""

    with pytest.raises(ToolRegistrationError, match="unsupported"):
        FunctionTool(unsupported)


def test_execute_missing_required_argument_raises() -> None:
    calls: list[tuple[float, float]] = []

    def record_add(num1: float, num2: float) -> float:
        """記錄呼叫並相加。"""
        calls.append((num1, num2))
        return num1 + num2

    tool = FunctionTool(record_add)

    with pytest.raises(ToolExecutionError):
        tool.execute(num1=1.0)

    assert calls == []


def test_execute_wrong_type_raises() -> None:
    calls: list[tuple[float, float]] = []

    def record_add(num1: float, num2: float) -> float:
        """記錄呼叫並相加。"""
        calls.append((num1, num2))
        return num1 + num2

    tool = FunctionTool(record_add)

    with pytest.raises(ToolExecutionError):
        tool.execute(num1="2", num2=3.0)

    assert calls == []


def test_execute_extra_unexpected_argument_raises() -> None:
    tool = FunctionTool(add)

    with pytest.raises(ToolExecutionError):
        tool.execute(a=1, b=2, c=3)
