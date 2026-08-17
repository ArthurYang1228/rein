"""Rein 進入點(骨架階段,尚未串接 AgentLoop)。"""


def main() -> None:
    """啟動 Rein。

    骨架階段的預留進入點;待 AgentLoop 等核心模組完成後,
    這裡會改為組裝 LLMProvider / ToolRegistry / PermissionManager 並啟動主迴圈。
    """
    print("Rein — agent runtime skeleton")


if __name__ == "__main__":
    main()
