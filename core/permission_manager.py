"""審批方式決策。"""


class PermissionManager:
    """依風險等級決定審批方式。

    依 RiskClassifier 給的風險等級,選擇自動核准 / 按鈕核准 / 對話確認 / 禁止。
    """
