"""SqliteSessionStore 的單元測試(ticket #21/#22)。

一律用 tmp_path 建立真實的 SQLite 檔案,不使用 FakeSessionStore、不 mock sqlite3。
"""

import sqlite3
from pathlib import Path
from typing import Literal

import pytest

from adapters.providers.gemini import GeminiProvider
from adapters.storage.sqlite_store import SqliteSessionStore
from core.exceptions import SessionNotFoundError, SessionStoreError
from core.interfaces.llm_message_model import LlmMessage, TextBlock, ToolResultBlock, ToolUseBlock


def _text_msg(role: Literal["user", "llm"], content: str) -> LlmMessage:
    return LlmMessage(role=role, content_blocks=[TextBlock(type="text", content=content)])


def _db_path(tmp_path: Path) -> str:
    return str(tmp_path / "sessions.db")


class _FakeContextManager:
    def save_config(self) -> dict[str, object]:
        return {"max_context_tokens": 5000}


class _FakeToolRegistry:
    def save_config(self) -> dict[str, object]:
        return {"tool_names": ["add", "subtract"]}


def test_save_then_load_round_trips_plain_text_messages(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        messages = [_text_msg("user", "hello"), _text_msg("llm", "hi there")]

        store.save("sid-1", messages)
        record = store.load("sid-1")

        assert record.session_id == "sid-1"
        assert record.messages == messages


def test_save_then_load_round_trips_all_content_block_variants(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        messages = [
            _text_msg("user", "請幫我算 1+2"),
            LlmMessage(
                role="llm",
                content_blocks=[
                    ToolUseBlock(type="tool_use", id="1", name="add", input={"a": 1, "b": 2})
                ],
            ),
            LlmMessage(
                role="user",
                content_blocks=[
                    ToolResultBlock(
                        type="tool_result", tool_use_id="1", name="add", is_error=False, content=3
                    )
                ],
            ),
            _text_msg("llm", "答案是 3"),
        ]

        store.save("sid-1", messages)
        record = store.load("sid-1")

        assert record.messages == messages


def test_save_overwrites_existing_session_instead_of_appending(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save("sid-1", [_text_msg("user", "a"), _text_msg("llm", "b"), _text_msg("user", "c")])

        store.save("sid-1", [_text_msg("user", "只剩這句")])
        record = store.load("sid-1")

        assert len(record.messages) == 1
        first_block = record.messages[0].content_blocks[0]
        assert isinstance(first_block, TextBlock)
        assert first_block.content == "只剩這句"


def test_save_and_load_multiple_sessions_do_not_interfere(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save("sid-a", [_text_msg("user", "session a")])
        store.save("sid-b", [_text_msg("user", "session b")])

        record_a = store.load("sid-a")
        record_b = store.load("sid-b")

        block_a = record_a.messages[0].content_blocks[0]
        block_b = record_b.messages[0].content_blocks[0]
        assert isinstance(block_a, TextBlock)
        assert isinstance(block_b, TextBlock)
        assert block_a.content == "session a"
        assert block_b.content == "session b"


def test_load_raises_session_not_found_for_unknown_id(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        with pytest.raises(SessionNotFoundError):
            store.load("does-not-exist")


def test_load_without_saved_components_returns_empty_metadata(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save("sid-1", [_text_msg("user", "hi")])
        record = store.load("sid-1")

        assert record.component_metadata == {}


def test_save_captures_component_metadata_keyed_by_class_name(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save(
            "sid-1",
            [_text_msg("user", "hi")],
            components=[_FakeContextManager(), _FakeToolRegistry()],
        )
        record = store.load("sid-1")

        assert record.component_metadata == {
            "_FakeContextManager": {"max_context_tokens": 5000},
            "_FakeToolRegistry": {"tool_names": ["add", "subtract"]},
        }


def test_save_wraps_underlying_sqlite_error_as_session_store_error(tmp_path: Path) -> None:
    store = SqliteSessionStore(db_path=_db_path(tmp_path))
    store.close()

    with pytest.raises(SessionStoreError):
        store.save("sid-1", [_text_msg("user", "hi")])


def test_context_manager_exit_actually_closes_the_connection(tmp_path: Path) -> None:
    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save("sid-1", [_text_msg("user", "hi")])

    with pytest.raises(sqlite3.ProgrammingError):
        store.cursor.execute("SELECT 1")


def test_real_component_save_config_round_trips_and_reconstructs(tmp_path: Path) -> None:
    """驗證 ticket #23 的整合承諾:真正的 production 元件(這裡用 GeminiProvider,

    因為它不需要其他依賴就能建構,也不會打真實 API)存進 SessionStore、
    讀回來後可以直接用 **metadata[...] 展開重新建構出同型的新實例。
    """
    real_provider = GeminiProvider(
        tool_info_list=[], api_key="fake-key-for-testing", model="gemini-3.5-flash"
    )

    with SqliteSessionStore(db_path=_db_path(tmp_path)) as store:
        store.save("sid-1", [_text_msg("user", "hi")], components=[real_provider])
        record = store.load("sid-1")

        rebuilt = GeminiProvider(
            tool_info_list=[],
            api_key="fake-key-for-testing",
            **record.component_metadata["GeminiProvider"],
        )

        assert rebuilt.model == real_provider.model
        assert rebuilt.system_prompt == real_provider.system_prompt
