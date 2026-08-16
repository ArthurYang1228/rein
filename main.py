"""Rein 進入點(骨架階段,尚未串接 AgentLoop)。"""

from adapters import GeminiProvider
from core.tool_registry import ToolRegistry
from core.agent_loop import AgentLoop
from core.interfaces.llm_message_model import LlmMessage, TextBlock


def main() -> None:
    """啟動 Rein。

    骨架階段的預留進入點;待 AgentLoop 等核心模組完成後,
    這裡會改為組裝 LLMProvider / ToolRegistry / PermissionManager 並啟動主迴圈。
    """
    # load_dotenv()
    # api_key = os.getenv("GEMINI_API_KEY")

    api_key = "aaaaa"
    tool_registry = ToolRegistry(["add", "subtract"])
    provider = GeminiProvider(tool_registry.get_all_tool_info(), api_key=api_key)
    messages = [
        LlmMessage(
    role="user",
            content_blocks=[TextBlock(type="text", content="說一個笑話，並用工具計算2+2的答案")],
        )
    ]
    resp = provider.call(messages)
    messages.append(resp)
    messages.append(
        LlmMessage(
            role="user",
            content_blocks=[TextBlock(type="text", content="你沒有給我講笑話?只有呼叫工具?")],
        )
    )
    provider.call(messages)
    print(resp)

    agent = AgentLoop(provider, tool_registry)
    resp_agent = agent.run("說一個笑話，並用工具計算2+2的答案")
    print(resp_agent)


if __name__ == "__main__":
    main()
