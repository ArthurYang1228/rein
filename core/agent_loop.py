"""核心 agent 迴圈。"""


class AgentLoop:
    """核心迴圈:LLM 思考 → 工具呼叫 → 結果回填 → 再次思考。

    只依賴 LLMProvider、Tool 等抽象介面,不直接依賴特定 LLM SDK(依賴反轉),
    確保可用 FakeProvider 替換做測試。
    """
