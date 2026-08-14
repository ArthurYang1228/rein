"""LLM 呼叫的抽象介面(port)。"""

from abc import ABC, abstractmethod
from typing import Any

from core.interfaces.llm_message_model import LlmMessage
from core.interfaces.tool_info_model import ToolInfo


class LLMProvider(ABC):
    """呼叫 LLM 的抽象介面。

    AgentLoop 只依賴此介面,不直接依賴 anthropic、gemini 等特定 SDK,
    確保測試時能以 FakeProvider 替換(依賴反轉原則)。
    """

    def __init__(self, tool_info_list: list[ToolInfo], sys_prompt: str = "") -> None:
        self.sys_prompt: str = sys_prompt
        self.tool_info_list: list[ToolInfo] = tool_info_list
        self.native_tool_list: list[Any] = self._process_tool_info_list(tool_info_list)

    @abstractmethod
    def call(self, messages: list[LlmMessage]) -> LlmMessage:
        pass

    @abstractmethod
    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> Any:
        pass
