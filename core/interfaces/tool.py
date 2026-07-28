"""單一工具的抽象介面(port)。"""

from abc import ABC, abstractmethod
from typing import Any
from core.interfaces.tool_info_model import ParamInfo, ToolInfo


class Tool(ABC):
    """agent 可呼叫的單一工具的抽象介面。

    每個工具(calculator、file_ops、bash_tool 等)都實作這個介面,
    讓 ToolRegistry 能以一致的方式註冊、查找與呼叫,彼此可互相替換。
    """

    name: str
    description: str
    input_schema: dict[str, ParamInfo]

    # 預設回傳是json但先不強制指定
    @abstractmethod
    def get_info(self) -> ToolInfo:
        pass

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        pass
