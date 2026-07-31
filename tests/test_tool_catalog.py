"""ToolCatalog 的單元測試。"""

import pytest

from core.exceptions import UnknownToolError
from core.interfaces.tool import Tool
from core.interfaces.tool_info_model import ToolInfo
from core.tool_catalog import ToolCatalog


class FakeTool(Tool):
    name = "fake"
    description = "假工具"

    def get_info(self) -> ToolInfo:
        return ToolInfo(
            name=self.name, type="function", description=self.description, input_schema={}
        )

    def execute(self, *args: object, **kwargs: object) -> str:
        return "ok"


def test_register_and_get_round_trip() -> None:
    tool = FakeTool()
    ToolCatalog.register(tool)

    assert ToolCatalog.get("fake") is tool


def test_is_registered_reflects_state() -> None:
    assert ToolCatalog.is_registered("fake") is False

    ToolCatalog.register(FakeTool())

    assert ToolCatalog.is_registered("fake") is True


def test_get_missing_tool_raises() -> None:
    with pytest.raises(UnknownToolError, match="does-not-exist"):
        ToolCatalog.get("does-not-exist")
