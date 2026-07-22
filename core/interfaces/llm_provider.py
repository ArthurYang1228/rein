"""LLM 呼叫的抽象介面(port)。"""

from abc import ABC


class LLMProvider(ABC):
    """呼叫 LLM 的抽象介面。

    AgentLoop 只依賴此介面,不直接依賴 anthropic、gemini 等特定 SDK,
    確保測試時能以 FakeProvider 替換(依賴反轉原則)。
    """
