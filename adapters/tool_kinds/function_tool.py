from core.interfaces.tool import Tool
import inspect
from core.interfaces.tool_info_model import ParamInfo, ToolInfo
from core.tool_catalog import ToolCatalog
from core.exceptions import ToolRegistrationError, ToolExecutionError
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

        if func.__doc__ is None:
            raise ToolRegistrationError(f"工具函數:{self.name} 缺少docstring")
        self.description = func.__doc__

        self.input_schema = {}
        param_schema = {}
        self._tool_sig = inspect.signature(func)

        for key, parameter in self._tool_sig.parameters.items():
            if parameter.annotation is inspect.Parameter.empty:
                raise ToolRegistrationError(f"工具函數:{self.name}中，參數: {key} 缺少型別註記")

            try:
                param_info = {
                    "name": key,
                    "type": getattr(parameter.annotation, "__name__", None),
                    "description": "",
                    "default": str(parameter.default)
                    if parameter.default is not inspect.Parameter.empty
                    else "",
                }

                # type 可能是 None(例如 Union 型別沒有 __name__),故意讓它流進
                # ParamInfo 的 Literal 驗證,由下面的 except ValidationError 擋下來
                self.input_schema[key] = ParamInfo(**param_info)  # type: ignore[arg-type]
                param_schema[key] = (
                    (parameter.annotation, parameter.default)
                    if parameter.default is not inspect.Parameter.empty
                    else (parameter.annotation, ...)
                )

            except ValidationError as e:
                raise ToolRegistrationError(
                    f"工具函數:{self.name}中，參數: {key} 使用不支援的型別"
                ) from e

        self.info = ToolInfo(
            name=self.name,
            type="function",
            description=self.description,
            input_schema=self.input_schema,
        )

        # pydantic 的動態 create_model 型別標註無法精確表達這裡的 tuple 形狀,實際執行沒問題
        self._param_validator = create_model("param_validator", **param_schema)  # type: ignore[call-overload]

    def get_info(self) -> ToolInfo:

        return self.info

    def execute(self, *args: Any, **kwargs: Any) -> Any:

        try:
            param_sig = self._tool_sig.bind(*args, **kwargs)
            self._param_validator.model_validate(param_sig.arguments, strict=True)

        except TypeError as e:
            raise ToolExecutionError(str(e)) from e

        except ValidationError as e:
            raise ToolExecutionError(str(e)) from e

        return self.func(**param_sig.arguments)


def register_tool(func: Callable[..., Any]) -> Callable[..., Any]:

    if not ToolCatalog.is_registered(func.__name__):
        tool = FunctionTool(func)
        ToolCatalog.register(tool)

    return func
