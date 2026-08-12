"""ToolRegistry 的單元測試。"""

import pytest

from core.exceptions import UnknownToolError
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
    with pytest.raises(UnknownToolError, match="not-registered"):
        ToolRegistry(["not-registered"])


def test_add_and_remove_tool() -> None:
    _register("gamma")
    registry = ToolRegistry([])

    registry.add_tool("gamma")
    assert registry.get_tool("gamma").execute() == "gamma-executed"

    registry.remove_tool("gamma")
    with pytest.raises(UnknownToolError):
        registry.get_tool("gamma")


def test_multiple_registries_are_independent() -> None:
    _register("delta")
    _register("epsilon")

    registry_a = ToolRegistry(["delta"])
    registry_b = ToolRegistry(["epsilon"])

    assert list(registry_a.tool_dict) == ["delta"]
    assert list(registry_b.tool_dict) == ["epsilon"]

    registry_a.add_tool("epsilon")

    assert list(registry_a.tool_dict) == ["delta", "epsilon"]
    assert list(registry_b.tool_dict) == ["epsilon"]
