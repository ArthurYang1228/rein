"""ToolCatalog 的單元測試。

查無工具的例外型別尚未實作,先用最廣的 Exception 接住;
等實際的例外型別(例如 ToolNotFoundError)實作完成後,
這裡的 pytest.raises(Exception) 要收斂成對應的具體型別。
"""

import pytest

from core.interfaces.tool import Tool
from core.interfaces.tool_info_model import ToolInfo
from core.ToolCatalog import ToolCatalog


class FakeTool(Tool):
    name = "fake"
    description = "假工具"

    def get_info(self) -> ToolInfo:
        return ToolInfo(name=self.name, description=self.description, input_schema={})

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
    with pytest.raises(Exception):  # noqa: B017 - 例外型別尚未定案
        ToolCatalog.get("does-not-exist")
