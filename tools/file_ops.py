"""檔案操作工具。"""

from adapters.tool_kinds.function_tool import register_tool


@register_tool
def open_file(file_name: str) -> str:
    """讀取檔案內容"""
    with open(file_name, encoding="utf-8") as f:
        return f.read()


@register_tool
def write_file(file_name: str, mode: str, content: str) -> None:
    """將內容寫入檔案內容，mode為w則覆寫，mode為a則附加在原檔後面，不可有其他值"""
    if mode not in ("w", "a"):
        raise ValueError("參數: mode 不為指定值: w or a")

    with open(file_name, mode, encoding="utf-8") as f:
        f.write(content)
