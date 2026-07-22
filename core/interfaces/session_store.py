"""Session 持久化的抽象介面(port)。"""

from abc import ABC


class SessionStore(ABC):
    """對話 session 儲存與還原的抽象介面。

    把實際儲存媒介(SQLite、記憶體、JSON 檔)藏在介面後,
    上層邏輯不需要關心用什麼儲存,測試時也能替換成記憶體版本。
    """
