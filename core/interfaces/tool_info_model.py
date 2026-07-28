from pydantic import BaseModel
from typing import Literal


class ParamInfo(BaseModel):
    name: str
    type: Literal["str", "int", "float", "bool"]
    description: str
    default: str


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict[str, ParamInfo]
