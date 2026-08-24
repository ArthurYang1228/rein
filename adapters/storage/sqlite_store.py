"""SQLite SessionStore 實作(adapter)。"""

from core.interfaces.session_store import SessionStore, SupportsSaveConfig
from core.exceptions import SessionNotFoundError, SessionStoreError
from core.interfaces.llm_message_model import LlmMessage
from core.interfaces import SessionRecord
from typing import Self
import sqlite3
import json


class SqliteSessionStore(SessionStore):
    """SessionStore 介面的 SQLite 實作。"""

    def __init__(self, db_path: str = "session_storage/sqlite_session_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY ,
            messages TEXT NOT NULL,
            component_metadata TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _messages_to_str(self, messages: list[LlmMessage]) -> str:
        messages_str = [msg.model_dump() for msg in messages]
        return json.dumps(messages_str)

    def _components_metadata_to_str(self, components: list[SupportsSaveConfig]) -> str:

        component_metadata = {
            type(component).__name__: component.save_config() for component in components
        }

        return json.dumps(component_metadata)

    def save(
        self,
        session_id: str,
        messages: list[LlmMessage],
        components: list[SupportsSaveConfig] | None = None,
    ) -> None:
        """
        儲存Session資訊
        """
        try:
            if components is None:
                components = []
            messages_str = self._messages_to_str(messages)
            component_metadata = self._components_metadata_to_str(components)
            self.cursor.execute(
                "INSERT OR REPLACE INTO sessions (session_id, messages, component_metadata) VALUES (?, ?, ?)",
                (session_id, messages_str, component_metadata),
            )

            self.conn.commit()

        except Exception as e:
            raise SessionStoreError(str(e)) from e

    def load(self, session_id: str) -> SessionRecord:
        """
        載入Session資訊
        """
        self.cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise SessionNotFoundError("ID無搜尋結果")

        try:
            messages = [LlmMessage.model_validate(msg) for msg in json.loads(row["messages"])]
            component_metadata = json.loads(row["component_metadata"])
            return SessionRecord(
                session_id=str(row["session_id"]),
                messages=messages,
                component_metadata=component_metadata,
            )

        except Exception as e:
            raise SessionStoreError(str(e)) from e

        # --------------------------  test --------------------------------------
        # conn = sqlite3.connect("session_storage/sqlite_session_data.db")
        # conn.row_factory = sqlite3.Row
        # cursor = conn.cursor()
        # cursor.execute(
        #     """
        #     DROP TABLE IF EXISTS sessions
        #     """
        # )
        # cursor.execute(
        #     """
        #     CREATE TABLE IF NOT EXISTS sessions (
        #     session_id TEXT PRIMARY KEY ,
        #     messages TEXT NOT NULL,
        #     component_metadata TEXT
        #     );
        #     """
        # )
        # cursor.execute(
        #     "INSERT INTO sessions (session_id, messages, component_metadata) VALUES (?, ?, ?)",
        #     ("aa", "aa", None)
        # )
        # cursor.execute(
        #     "INSERT INTO sessions (session_id, messages, component_metadata) VALUES (?, ?, ?)",
        #     ("cc", "abb", json.dumps({}))
        # )
        # conn.commit()
        # cursor.execute("SELECT * FROM sessions WHERE session_id = ?", ('ee',))
        # row = cursor.fetchall()
        # print(type(row))
        # r = row[0]["component_metadata"]
        # print(json.loads(r))
