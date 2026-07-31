"""檔案操作工具。"""

from adapters.tool_kinds.function_tool import register_tool


@register_tool
def open_file(file_name: str) -> str:
    """讀取檔案內容"""
    with open(file_name) as f:
        return f.read()
