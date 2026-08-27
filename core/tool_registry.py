"""工具註冊與查找。"""

from core.interfaces.tool import Tool
from core.tool_catalog import ToolCatalog
from core.interfaces.tool_info_model import ToolInfo
from core.exceptions import UnknownToolError
from typing import Any


class ToolRegistry:
    """工具的註冊與查找。

    新增工具只需要往這裡註冊,不用改動 AgentLoop 核心迴圈(開放封閉原則)。
    """

    def __init__(self, tool_name_list: list[str]):

        self.tool_dict = {tool_name: ToolCatalog.get(tool_name) for tool_name in tool_name_list}

    def add_tool(self, tool_name: str) -> None:
        self.tool_dict[tool_name] = ToolCatalog.get(tool_name)

    def remove_tool(self, tool_name: str) -> None:

        if tool_name in self.tool_dict:
            del self.tool_dict[tool_name]

    def get_tool(self, tool_name: str) -> Tool:

        try:
            return self.tool_dict[tool_name]
        except KeyError as e:
            raise UnknownToolError(f"tool {tool_name} not found") from e

    def get_all_tool_info(self) -> list[ToolInfo]:
        return [tool.get_info() for tool in self.tool_dict.values()]

    def save_config(self) -> dict[str, Any]:
        return {"tool_name_list": list(self.tool_dict.keys())}
