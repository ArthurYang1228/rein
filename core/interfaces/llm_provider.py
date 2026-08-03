"""LLM 呼叫的抽象介面(port)。"""

from abc import ABC, abstractmethod
from core.interfaces.llm_message_model import LlmMessage
from core.interfaces.tool_info_model import ToolInfo


class LLMProvider(ABC):
    """呼叫 LLM 的抽象介面。

    AgentLoop 只依賴此介面,不直接依賴 anthropic、gemini 等特定 SDK,
    確保測試時能以 FakeProvider 替換(依賴反轉原則)。
    """

    sys_prompt: str = ""
    tool_info_list: list[ToolInfo]

    @abstractmethod
    def call(self, history: list[LlmMessage], msg: LlmMessage) -> LlmMessage:
        pass

    @abstractmethod
    def process_tool_info_list(self) -> str:
        pass
