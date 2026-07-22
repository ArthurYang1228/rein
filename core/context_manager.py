"""上下文治理。"""


class ContextManager:
    """對話上下文治理。

    追蹤目前 context 用量,超過水位時觸發 compact,避免長對話爆掉。
    """
