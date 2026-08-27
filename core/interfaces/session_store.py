"""Session 持久化的抽象介面(port)。"""

from abc import ABC, abstractmethod
from core.interfaces.llm_message_model import LlmMessage
from core.interfaces.session_store_model import SessionRecord
from typing import Protocol, Any


class SupportsSaveConfig(Protocol):
    def save_config(self) -> dict[str, Any]: ...


class SessionStore(ABC):
    """對話 session 儲存與還原的抽象介面。

    把實際儲存媒介(SQLite、記憶體、JSON 檔)藏在介面後,
    上層邏輯不需要關心用什麼儲存,測試時也能替換成記憶體版本。
    """

    @abstractmethod
    def save(
        self,
        session_id: str,
        messages: list[LlmMessage],
        components: list[SupportsSaveConfig] | None = None,
    ) -> None:
        """
        儲存Session資訊
        """
        pass

    @abstractmethod
    def load(self, session_id: str) -> SessionRecord:
        """
        載入Session資訊
        """
        pass
