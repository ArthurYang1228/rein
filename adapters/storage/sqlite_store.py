"""SQLite SessionStore 實作(adapter)。"""

from core.interfaces.session_store import SessionStore


class SqliteSessionStore(SessionStore):
    """SessionStore 介面的 SQLite 實作。"""
