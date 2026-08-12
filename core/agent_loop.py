"""核心 agent 迴圈。"""

from core.interfaces.llm_message_model import LlmMessage, TextBlock, ToolResultBlock, ContentBlock
from core.tool_registry import ToolRegistry
from core.interfaces import LLMProvider
from typing import Optional
from dataclasses import dataclass, field
from core.exceptions import MaxIterationsExceededError, ToolExecutionError


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
    result_reviewer: Optional[object] = field(default=None)

    def run(self, user_message: str) -> LlmMessage:

        first_msg = LlmMessage(
            role="user", content_blocks=[TextBlock(type="text", content=user_message)]
        )
        self.messages.append(first_msg)
        iter_count = 0
        tool_failure_count = 0
        while iter_count < self.max_iterations:
            iter_count += 1
            resp = self.llm.call(self.messages)
            self.messages.append(resp)
            tool_uses = resp.tool_uses
            tool_rst_list: list[ContentBlock] = []
            if tool_uses:
                for tool_use in tool_uses:
                    tool = self.tool_registry.get_tool(tool_use.name)
                    try:
                        tool_rst = tool.execute(**tool_use.input)
                        rst_block = ToolResultBlock(
                            type="tool_result",
                            tool_use_id=tool_use.id,
                            is_error=False,
                            content=tool_rst,
                        )

                    except ToolExecutionError as e:
                        rst_block = ToolResultBlock(
                            type="tool_result",
                            tool_use_id=tool_use.id,
                            is_error=True,
                            content=str(e),
                        )
                        tool_failure_count += 1

                    tool_rst_list.append(rst_block)

                tool_rst_msg = LlmMessage(role="user", content_blocks=tool_rst_list)
                self.messages.append(tool_rst_msg)
                if tool_failure_count >= self.total_failure_limit:
                    fail_msg = [
                        ToolResultBlock(
                            type="tool_result",
                            tool_use_id="all",
                            is_error=True,
                            content=f"Tool執行錯誤次數已達上限{self.total_failure_limit}次，迴圈中斷",
                        )
                    ]
                    return LlmMessage(role="llm", content_blocks=fail_msg)
            else:
                return resp
        raise MaxIterationsExceededError(f"超出執行迴圈上限:{self.max_iterations}次")
