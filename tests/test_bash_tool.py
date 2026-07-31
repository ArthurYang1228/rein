"""tools/bash_tool.py 的單元測試。"""

from core.tool_catalog import ToolCatalog
from tools.bash_tool import bash


def test_bash_returns_command_output() -> None:
    assert bash("echo hello").strip() == "hello"


def test_bash_registered_in_catalog() -> None:
    assert ToolCatalog.is_registered("bash")
    assert ToolCatalog.get("bash").execute("echo hello").strip() == "hello"


def test_bash_tool_info_matches_signature() -> None:
    info = ToolCatalog.get("bash").get_info()

    assert info.name == "bash"
    assert info.description == "執行 bash 指令並回傳輸出"
    assert set(info.input_schema) == {"command"}
    assert info.input_schema["command"].type == "str"
