"""tools/file_ops.py 的單元測試。"""

from pathlib import Path

import pytest

from core.exceptions import ToolExecutionError
from core.tool_catalog import ToolCatalog
from tools.file_ops import open_file, write_file


def test_open_file_returns_file_content(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello rein")

    assert open_file(str(file_path)) == "hello rein"


def test_open_file_registered_in_catalog(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello rein")

    assert ToolCatalog.is_registered("open_file")
    assert ToolCatalog.get("open_file").execute(str(file_path)) == "hello rein"


def test_open_file_tool_info_matches_signature() -> None:
    info = ToolCatalog.get("open_file").get_info()

    assert info.name == "open_file"
    assert info.description == "讀取檔案內容"
    assert set(info.input_schema) == {"file_name"}
    assert info.input_schema["file_name"].type == "str"


def test_write_file_creates_new_file_with_content(tmp_path: Path) -> None:
    file_path = tmp_path / "new.txt"

    write_file(str(file_path), "w", "hello rein")

    assert file_path.read_text(encoding="utf-8") == "hello rein"


def test_write_file_overwrites_existing_content_in_w_mode(tmp_path: Path) -> None:
    file_path = tmp_path / "existing.txt"
    file_path.write_text("舊內容", encoding="utf-8")

    write_file(str(file_path), "w", "新內容")

    assert file_path.read_text(encoding="utf-8") == "新內容"


def test_write_file_appends_content_in_a_mode(tmp_path: Path) -> None:
    file_path = tmp_path / "existing.txt"
    file_path.write_text("first", encoding="utf-8")

    write_file(str(file_path), "a", "-second")

    assert file_path.read_text(encoding="utf-8") == "first-second"


def test_write_file_raises_on_invalid_mode(tmp_path: Path) -> None:
    file_path = tmp_path / "new.txt"

    with pytest.raises(Exception):  # noqa: B017 - 目前實作丟裸 Exception,見 review 意見
        write_file(str(file_path), "x", "content")

    assert not file_path.exists()


def test_write_file_invalid_mode_wrapped_as_tool_execution_error_via_catalog(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "new.txt"

    with pytest.raises(ToolExecutionError):
        ToolCatalog.get("write_file").execute(file_name=str(file_path), mode="x", content="content")


def test_write_file_registered_in_catalog(tmp_path: Path) -> None:
    file_path = tmp_path / "new.txt"

    assert ToolCatalog.is_registered("write_file")
    ToolCatalog.get("write_file").execute(file_name=str(file_path), mode="w", content="hi")

    assert file_path.read_text(encoding="utf-8") == "hi"


def test_write_file_tool_info_matches_signature() -> None:
    info = ToolCatalog.get("write_file").get_info()

    assert info.name == "write_file"
    assert set(info.input_schema) == {"file_name", "mode", "content"}
    assert info.input_schema["file_name"].type == "str"
    assert info.input_schema["mode"].type == "str"
    assert info.input_schema["content"].type == "str"


def test_write_file_then_open_file_round_trips_non_ascii_content(tmp_path: Path) -> None:
    """已知 bug:open_file 沒有指定 encoding,在非 utf-8 預設編碼的環境下

    (例如這台機器預設 cp950)讀取 write_file(utf-8 寫入)的非 ASCII 內容會壞掉。
    兩邊都明確指定 encoding="utf-8" 之後,這個測試在任何平台都應該通過。
    """
    file_path = tmp_path / "chinese.txt"

    write_file(str(file_path), "w", "你好,Rein")

    assert open_file(str(file_path)) == "你好,Rein"
