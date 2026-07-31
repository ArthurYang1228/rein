"""tools/file_ops.py 的單元測試。"""

from pathlib import Path

from core.tool_catalog import ToolCatalog
from tools.file_ops import open_file


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
