from core.interfaces.tool import Tool
from core.exceptions import UnknownToolError


class ToolCatalog:
    """process 範圍、只在 import 階段填一次的全域工具集合。"""

    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, tool_name: str) -> Tool:
        try:
            return cls._tools[tool_name]
        except KeyError:
            raise UnknownToolError(f"tool {tool_name} not found")

    @classmethod
    def is_registered(cls, tool_name: str) -> bool:
        return tool_name in cls._tools
        # raise ToolRegistrationError(f"ToolCatalog 找不到工具:{name}") from None
