from core.interfaces.tool import Tool
import inspect
from core.interfaces.tool_info_model import ParamInfo, ToolInfo
from core.tool_catalog import ToolCatalog
from core.exceptions import ToolRegistrationError
from typing import Any
from collections.abc import Callable
from pydantic import create_model, ValidationError


class FunctionTool(Tool):
    def __init__(self, func: Callable[..., Any]):
        # 1. 初始化時，把被裝飾的函數存起來
        self.func = func
        # 可選：保持被裝飾函數的元數據（如 __name__, __doc__）
        self.name = func.__name__
        # func.__doc__ 型別是 str | None,這裡先照原行為交給下面 ToolInfo
        # 的 pydantic 驗證去擋 None,只用 cast 讓 mypy 認得型別

        self.description = func.__doc__
        if self.description is None:
            raise ToolRegistrationError("工具函數:{self.name} 缺少docstring")

        self.input_schema = {}
        param_schema = {}
        self._tool_sig = inspect.signature(func)

        for key, parameter in self._tool_sig.parameters.items():
            if parameter.annotation is None:
                raise ToolRegistrationError("工具函數:{self.name}中，參數: {key} 缺少型別註記")

            param_info = {
                "name": key,
                "type": parameter.annotation.__name__,
                "description": "",
                "default": str(parameter.default),
            }

            try:
                self.input_schema[key] = ParamInfo(**param_info)
                param_schema[key] = (parameter.annotation, parameter.default)

            except ValidationError:
                raise ToolRegistrationError("工具函數:{self.name}中，參數: {key} 使用不支援的型別")

        self.info = ToolInfo(
            name=self.name,
            type="function",
            description=self.description,
            input_schema=self.input_schema,
        )

        self._param_validator = create_model("param_validator", **param_schema)

    def get_info(self) -> ToolInfo:

        return self.info

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        param_sig = self._tool_sig.bind(*args, **kwargs)
        self._param_validator.model_validate(param_sig)

        return self.func(*args, **kwargs)


def register_tool(func: Callable[..., Any]) -> Callable[..., Any]:

    if not ToolCatalog.is_registered(func.__name__):
        tool = FunctionTool(func)
        ToolCatalog.register(tool)

    return func
