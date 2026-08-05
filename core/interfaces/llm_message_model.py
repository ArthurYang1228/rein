from mypy.types import Any
from pydantic import BaseModel, Field, StrictBool
from typing import Literal, Union, Annotated


class TextBlock(BaseModel):
    type: Literal["text"]
    content: str


class ToolUseBlock(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, str | int | float | bool]


class ToolResultBlock(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    is_error: StrictBool
    content: Any


# class ContentBlock(BaseModel):
#     content_block: Union[TextBlock, ToolUseBlock, ToolResultBlock] = Field(..., discriminator="type")

ContentBlock = Annotated[
    Union[TextBlock, ToolUseBlock, ToolResultBlock], Field(discriminator="type")
]


class LlmMessage(BaseModel):
    role: Literal["user", "llm"]
    content_blocks: list[ContentBlock]

    @property
    def tool_uses(self) -> list[ToolUseBlock]:
        return [block for block in self.content_blocks if isinstance(block, ToolUseBlock)]
