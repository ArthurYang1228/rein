"""測試共用 fixture。"""

from collections.abc import Iterator

import pytest

from core.tool_catalog import ToolCatalog


@pytest.fixture(autouse=True)
def isolated_tool_catalog() -> Iterator[None]:
    """讓每個測試各自隔離 ToolCatalog 的全域狀態,避免測試互相污染。

    ToolCatalog._tools 是 class 屬性、process 範圍共用一份;直接在原地
    增刪會讓後面的測試看到前面測試殘留的註冊內容。這裡在測試前把它換成
    一份複本(保留 import 階段已經註冊好的內容,例如 tools/calculator.py
    的 add),測試結束後再換回原本的物件,復原成乾淨狀態。
    """
    original = ToolCatalog._tools
    ToolCatalog._tools = dict(original)
    yield
    ToolCatalog._tools = original
