from core.interfaces.tool import Tool
import functools
import inspect
from pydantic import BaseModel


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
    dict: "OBJECT"}

class ToolInfoModel(BaseModel):

    name: str
    description: str
    properties: dict
    required: list


class FunctionTool(Tool):

    def __init__(self, func):
        # 1. 初始化時，把被裝飾的函數存起來
        self.func = func
        # 可選：保持被裝飾函數的元數據（如 __name__, __doc__）
        properties = {}
        required = []
        for name, parameter in inspect.signature(func).parameters.items():
            properties[name] = {"type":PYTHON_TO_JSON_SCHEMA_TYPE[parameter.annotation]}

            if parameter.default == inspect.Parameter.empty:
                required.append(name)

        info = {"name" : func.__name__,
                "description": func.__doc__,
                "properties": properties,
                "required": required}

        self.info = ToolInfoModel(**info)

    def get_info(self):
        return self.info


    def execute(self, *args, **kwargs):
        return self.func(*args, **kwargs)