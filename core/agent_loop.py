"""核心 agent 迴圈。"""

from core.interfaces.llm_message_model import LlmMessage
from core.tool_registry import ToolRegistry

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AgentLoop:
    """核心迴圈:LLM 思考 → 工具呼叫 → 結果回填 → 再次思考。

    只依賴 LLMProvider、Tool 等抽象介面,不直接依賴特定 LLM SDK(依賴反轉),
    確保可用 FakeProvider 替換做測試。
    """

    messages: list[LlmMessage]
    tool_registry: ToolRegistry
    max_iterations: int = field(default=10)
    total_failure_limit: int = field(default=10)
    result_reviewer: Optional = field(default=None)

    def run(self, user_message: str) -> LlmMessage:
        pass
