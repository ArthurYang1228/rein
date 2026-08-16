"""Gemini LLMProvider 實作(adapter)。"""

from core.interfaces.llm_provider import LLMProvider
from core.interfaces.llm_message_model import (
    LlmMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ContentBlock,
)
from core.interfaces.tool_info_model import ToolInfo
from typing import Any, Protocol, runtime_checkable
import json
from google import genai
from core.exceptions import RetryableLLMError, NonRetryableLLMError
from google.genai._gaos.lib.compat_errors import APIError
import uuid

PYTHON_TYPE_TO_JSON_SCHEMA_TYPE = {
    # 基礎型態
    "str": "STRING",
    "int": "INTEGER",
    "float": "NUMBER",
    "bool": "BOOLEAN",
    # 複合與容器型態
    "list": "ARRAY",
    "tuple": "ARRAY",
    "set": "ARRAY",
    "dict": "OBJECT",
}


@runtime_checkable
class HasSteps(Protocol):
    steps: list[Any] | None


class GeminiProvider(LLMProvider):
    """LLMProvider 介面的 Gemini SDK 實作。"""

    def __init__(
        self,
        tool_info_list: list[ToolInfo],
        sys_prompt: str = "",
        api_key: str | None = None,
        model: str = "gemini-3.5-flash",
    ):
        super().__init__(tool_info_list, sys_prompt)
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _get_history(self, messages: list[LlmMessage]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        block_dump: dict[str, Any]

        for msg in messages:
            if msg.provider_data is not None:
                history.extend(msg.provider_data)
                continue

            for content_block in msg.content_blocks:
                block_dump = {}
                if msg.role == "user":
                    if isinstance(content_block, TextBlock):
                        block_dump = {
                            "type": "user_input",
                            "content": [{"type": "text", "text": content_block.content}],
                        }

                    elif isinstance(content_block, ToolResultBlock):
                        block_dump = {
                            "type": "function_result",
                            "name": content_block.name,
                            "error": content_block.is_error,
                            "call_id": content_block.tool_use_id,
                            "result": [{"type": "text", "text": json.dumps(content_block.content)}],
                        }

                if msg.role == "llm":
                    if isinstance(content_block, TextBlock):
                        block_dump = {
                            "type": "model_output",
                            "content": [{"type": "text", "text": content_block.content}],
                        }

                    elif isinstance(content_block, ToolUseBlock):
                        block_dump = {
                            "type": "function_call",
                            "name": content_block.name,
                            "call_id": content_block.id,
                            "arguments": content_block.input,
                        }

                if block_dump:
                    history.append(block_dump)

        return history

    def _process_responce(self, resp: HasSteps) -> tuple[list[ContentBlock], list[dict[str, Any]]]:
        content_blocks: list[ContentBlock] = []
        provider_data: list[dict[str, Any]] = []

        for step in resp.steps or []:
            provider_data.append(step.model_dump())
            if step.type == "model_output":
                for c in step.content:
                    if c.type == "text":
                        content_blocks.append(TextBlock(type="text", content=c.text))

            elif step.type == "function_call":
                tool_use_id = getattr(step, "id", f"fallback-{uuid.uuid4()}")
                content_blocks.append(
                    ToolUseBlock(
                        type="tool_use", id=tool_use_id, name=step.name, input=step.arguments
                    )
                )
        return content_blocks, provider_data

    def call(self, messages: list[LlmMessage]) -> LlmMessage:

        try:
            resp = self.client.interactions.create(
                model=self.model,
                store=False,
                input=self._get_history(messages),
                tools=self.native_tool_list,
            )
        except APIError as e:
            status_code = getattr(e, "status_code", None)
            if status_code is None or status_code == 429 or status_code >= 500:
                raise RetryableLLMError(str(e)) from e
            raise NonRetryableLLMError(str(e)) from e

        if isinstance(resp, HasSteps):
            content_blocks, provider_data = self._process_responce(resp)
        else:
            content_blocks, provider_data = [], []

        return LlmMessage(role="llm", content_blocks=content_blocks, provider_data=provider_data)

    def _process_tool_info(self, tool_info: ToolInfo) -> dict[str, Any]:

        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, parameter in tool_info.input_schema.items():
            properties[name] = {}
            properties[name]["type"] = PYTHON_TYPE_TO_JSON_SCHEMA_TYPE[parameter.type]
            properties[name]["description"] = parameter.description
            if parameter.default == "":
                required.append(name)

        return {
            "type": "function",
            "name": tool_info.name,
            "description": tool_info.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> Any:
        return [self._process_tool_info(tool_info) for tool_info in tool_info_list]
