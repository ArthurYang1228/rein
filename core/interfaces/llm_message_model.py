from pydantic import BaseModel, Field, StrictBool
from typing import Any, Literal, Union, Annotated


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
    name: str
    is_error: StrictBool
    content: Any


ContentBlock = Annotated[
    Union[TextBlock, ToolUseBlock, ToolResultBlock], Field(discriminator="type")
]


class LlmMessage(BaseModel):
    role: Literal["user", "llm"]
    content_blocks: list[ContentBlock]
    provider_data: list[dict[str, Any]] | None = Field(default=None)

    @property
    def tool_uses(self) -> list[ToolUseBlock]:
        return [block for block in self.content_blocks if isinstance(block, ToolUseBlock)]
