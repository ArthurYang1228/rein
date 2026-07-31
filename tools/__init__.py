"""明確 import 所有工具模組,觸發各自的 @register_tool 裝饋,把 ToolCatalog 填滿。"""

from tools import bash_tool, calculator, file_ops  # noqa: F401
