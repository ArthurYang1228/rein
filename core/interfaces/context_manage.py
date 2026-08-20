from abc import ABC, abstractmethod
from core.interfaces.llm_message_model import LlmMessage
from core.interfaces import LLMProvider


class ContextManager(ABC):
    """上下文管理 的抽象介面。
    監測和壓縮過多的上下文
    """

    llm: LLMProvider
    max_context_tokens: int
    max_llm_retries: int
    retry_wait_second: int

    @abstractmethod
    def maybe_compact(self, messages: list[LlmMessage]) -> list[LlmMessage]:
        """
        確認是否需要壓縮，若token量不達上限則回傳原始訊息列，若達上限則進行壓縮
        """
        pass
