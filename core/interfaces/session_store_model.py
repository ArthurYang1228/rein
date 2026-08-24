from pydantic import BaseModel, Field
from typing import Any
from core.interfaces.llm_message_model import LlmMessage


class SessionRecord(BaseModel):
    session_id: str
    messages: list[LlmMessage]
    component_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
