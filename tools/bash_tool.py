"""Bash 指令執行工具。"""

from adapters.tool_kinds.function_tool import register_tool
import subprocess

@register_tool
def bash(command: str) -> str:
    """執行 bash 指令並回傳輸出"""
    resp = subprocess.run(command, capture_output=True, text=True, shell=True)
    return resp.stdout