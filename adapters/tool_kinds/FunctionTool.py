from core.interfaces.tool import Tool
import inspect
from core.interfaces.tool_info_model import ParamInfo, ToolInfo
from core.ToolCatalog import ToolCatalog
from typing import Any, cast
from collections.abc import Callable


class FunctionTool(Tool):
    def __init__(self, func: Callable[..., Any]):
        # 1. 初始化時，把被裝飾的函數存起來
        self.func = func
        # 可選：保持被裝飾函數的元數據（如 __name__, __doc__）
        self.name = func.__name__
        # func.__doc__ 型別是 str | None,這裡先照原行為交給下面 ToolInfo
        # 的 pydantic 驗證去擋 None,只用 cast 讓 mypy 認得型別
        self.description = cast(str, func.__doc__)
        self.input_schema = {}

        for key, parameter in inspect.signature(func).parameters.items():
            param_info = {
                "name": key,
                "type": parameter.annotation.__name__,
                "description": "",
                "default": str(parameter.default),
            }
            self.input_schema[key] = ParamInfo(**param_info)

        self.info = ToolInfo(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )

    def get_info(self) -> ToolInfo:

        return self.info

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def register_tool(func: Callable[..., Any]) -> Callable[..., Any]:

    if not ToolCatalog.is_registered(func.__name__):
        tool = FunctionTool(func)
        ToolCatalog.register(tool)
    return func
