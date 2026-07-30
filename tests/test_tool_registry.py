"""ToolRegistry 的單元測試。

查無工具的例外型別尚未實作,先用最廣的 Exception 接住;
等實際的例外型別實作完成後,這裡的 pytest.raises(Exception)
要收斂成對應的具體型別。
"""

import pytest

from core.interfaces.tool import Tool
from core.interfaces.tool_info_model import ToolInfo
from core.tool_catalog import ToolCatalog
from core.tool_registry import ToolRegistry


class FakeTool(Tool):
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"{name} 假工具"

    def get_info(self) -> ToolInfo:
        return ToolInfo(
            name=self.name, type="function", description=self.description, input_schema={}
        )

    def execute(self, *args: object, **kwargs: object) -> str:
        return f"{self.name}-executed"


def _register(name: str) -> FakeTool:
    tool = FakeTool(name)
    ToolCatalog.register(tool)
    return tool


def test_init_builds_subset_from_catalog() -> None:
    _register("alpha")
    _register("beta")

    registry = ToolRegistry(["alpha", "beta"])

    assert registry.get_tool("alpha").execute() == "alpha-executed"
    assert len(registry.get_all_tool_info()) == 2


def test_init_raises_for_unknown_tool_name() -> None:
    with pytest.raises(Exception):  # noqa: B017 - 例外型別尚未定案
        ToolRegistry(["not-registered"])


def test_add_and_remove_tool() -> None:
    _register("gamma")
    registry = ToolRegistry([])

    registry.add_tool("gamma")
    assert registry.get_tool("gamma").execute() == "gamma-executed"

    registry.remove_tool("gamma")
    with pytest.raises(KeyError):
        registry.get_tool("gamma")
