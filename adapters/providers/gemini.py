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
        system_prompt: str = "",
        api_key: str | None = None,
        model: str = "gemini-3.5-flash",
    ):
        super().__init__(tool_info_list, system_prompt)
        self.native_tool_list: list[dict[str, Any]]
        if api_key != "" and api_key is not None:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()
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

    def _classify_api_error(self, e: APIError) -> RetryableLLMError | NonRetryableLLMError:
        """把 SDK 的 APIError 分類成可重試或不可重試的例外。

        網路逾時/rate limit/伺服器錯誤(含 status_code 缺失)視為可重試,
        其餘(API key 無效、請求格式錯誤等)視為不可重試。
        """
        status_code = getattr(e, "status_code", None)
        if status_code is None or status_code == 429 or status_code >= 500:
            return RetryableLLMError(str(e))
        return NonRetryableLLMError(str(e))

    def call(
        self,
        messages: list[LlmMessage],
        system_prompt: str | None = None,
        tool_info_list: list[ToolInfo] | None = None,
    ) -> LlmMessage:
        """
        呼叫 LLM 取得回覆
        """

        try:
            resp = self.client.interactions.create(
                model=self.model,
                store=False,
                input=self._get_history(messages),
                tools=self.native_tool_list
                if tool_info_list is None
                else self._process_tool_info_list(tool_info_list),
                system_instruction=self.system_prompt if system_prompt is None else system_prompt,
            )
        except APIError as e:
            raise self._classify_api_error(e) from e

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

    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> list[dict[str, Any]]:
        return [self._process_tool_info(tool_info) for tool_info in tool_info_list]

    def count_tokens(self, messages: list[LlmMessage], only_user_prompt: bool = False) -> int:
        """
        計算歷史訊息使用token數
        """

        contents: list[str | dict[str, Any]] = list(self._get_history(messages))
        if not only_user_prompt:
            contents.append(self.system_prompt)
            contents.extend(self.native_tool_list)

        try:
            resp = self.client.models.count_tokens(model=self.model, contents=json.dumps(contents))
        except APIError as e:
            raise self._classify_api_error(e) from e

        if resp.total_tokens is None:
            raise ValueError("沒有回報 total_tokens")

        return resp.total_tokens

    def get_max_context_tokens(self) -> int:
        """
        取得模型最大token數
        """

        try:
            model_info = self.client.models.get(model=self.model)
        except APIError as e:
            raise self._classify_api_error(e) from e

        if model_info.input_token_limit is None:
            raise ValueError(f"模型 {self.model} 沒有回報 input_token_limit")

        return model_info.input_token_limit
