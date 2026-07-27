"""Bash 指令執行工具。"""

from core.interfaces.tool import Tool


class BashTool(Tool):
    """Tool 介面的 bash 指令執行實作,是 RiskClassifier 重點審查的高風險工具。"""
