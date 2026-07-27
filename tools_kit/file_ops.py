"""檔案操作工具。"""

from core.interfaces.tool import Tool


class FileOpsTool(Tool):
    """Tool 介面的檔案操作實作,供 agent 讀寫、列出檔案。"""
