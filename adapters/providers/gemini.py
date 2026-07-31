"""Gemini LLMProvider 實作(adapter)。"""

from core.interfaces.llm_provider import LLMProvider
import inspect
from typing import Any
from collections.abc import Callable

PYTHON_TO_JSON_SCHEMA_TYPE = {
    # 基礎型態
    str: "STRING",
    int: "INTEGER",
    float: "NUMBER",
    bool: "BOOLEAN",
    # 複合與容器型態
    list: "ARRAY",
    tuple: "ARRAY",
    set: "ARRAY",
    dict: "OBJECT",
}


class GeminiProvider(LLMProvider):
    """LLMProvider 介面的 Gemini SDK 實作。"""

    def get_tool(self, func: Callable[..., Any]) -> dict[str, Any]:
        properties = {}
        required = []
        for name, parameter in inspect.signature(func).parameters.items():
            properties[name] = {"type": PYTHON_TO_JSON_SCHEMA_TYPE[parameter.annotation]}

            if parameter.default == inspect.Parameter.empty:
                required.append(name)

        info = {
            "name": func.__name__,
            "description": func.__doc__,
            "properties": properties,
            "required": required,
        }

        return info
