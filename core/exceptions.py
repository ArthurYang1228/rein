class ToolRegistrationError(Exception):
    """工具因缺乏文件、參數數量或型別錯誤而註冊失敗"""

    pass


class ToolExecutionError(Exception):
    """工具因參數數量或型別錯誤而執行失敗"""

    pass


class UnknownToolError(Exception):
    """嘗試呼叫未知或未註冊工具"""

    pass


class MaxIterationsExceededError(Exception):
    """迴圈執行超過上限"""

    pass
