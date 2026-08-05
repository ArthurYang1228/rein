"""核心 agent 迴圈。"""

from core.interfaces.llm_message_model import LlmMessage, TextBlock, ToolResultBlock
from core.tool_registry import ToolRegistry
from core.interfaces import LLMProvider
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AgentLoop:
    """核心迴圈:LLM 思考 → 工具呼叫 → 結果回填 → 再次思考。

    只依賴 LLMProvider、Tool 等抽象介面,不直接依賴特定 LLM SDK(依賴反轉),
    確保可用 FakeProvider 替換做測試。
    """

    llm: LLMProvider
    messages: list[LlmMessage]
    tool_registry: ToolRegistry
    max_iterations: int = field(default=10)
    total_failure_limit: int = field(default=10)
    result_reviewer: Optional = field(default=None)

    def run(self, user_message: str) -> LlmMessage:

        first_msg = LlmMessage(role='user', content_blocks=[TextBlock(type='text', content=user_message)])
        self.messages.append(first_msg)
        resp = self.llm.call(self.messages)
        self.messages.append(resp)
        tool_uses  = resp.tool_uses
        if tool_uses:
            for tool_use in tool_uses:
                tool = self.tool_registry.get_tool(tool_use.name)
                tool_rst = tool.execute(tool_use.input)
                ToolResultBlock(type='tool_result', tool_use_id=tool_use.id, is_error = False, content = tool_rst)

    


