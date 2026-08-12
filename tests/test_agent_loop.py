"""AgentLoop 的單元測試。"""

import pytest

from core.agent_loop import AgentLoop
from core.exceptions import MaxIterationsExceededError, ToolExecutionError, UnknownToolError
from core.interfaces.llm_message_model import (
    LlmMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from core.interfaces.llm_provider import LLMProvider
from core.interfaces.tool import Tool
from core.interfaces.tool_info_model import ToolInfo
from core.tool_catalog import ToolCatalog
from core.tool_registry import ToolRegistry


class FakeAddTool(Tool):
    name = "add"
    description = "兩數相加"

    def get_info(self) -> ToolInfo:
        return ToolInfo(
            name=self.name, type="function", description=self.description, input_schema={}
        )

    def execute(self, *args: object, **kwargs: object) -> float:
        num1 = kwargs["num1"]
        num2 = kwargs["num2"]
        assert isinstance(num1, int | float)
        assert isinstance(num2, int | float)
        return float(num1) + float(num2)


class FakeFailingTool(Tool):
    """每次呼叫都失敗的假工具,用來測試 TotalFailureLimit。"""

    name = "fail"
    description = "永遠失敗"

    def __init__(self) -> None:
        self.call_count = 0

    def get_info(self) -> ToolInfo:
        return ToolInfo(
            name=self.name, type="function", description=self.description, input_schema={}
        )

    def execute(self, *args: object, **kwargs: object) -> float:
        self.call_count += 1
        raise ToolExecutionError("模擬工具永遠失敗")


class FakeLLMProvider(LLMProvider):
    """依序回放預先寫好的回應,不打真實 LLM API。"""

    def __init__(self, tool_info_list: list[ToolInfo], responses: list[LlmMessage]) -> None:
        self._responses = responses
        self.call_count = 0
        super().__init__(tool_info_list)

    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> list[ToolInfo]:
        return tool_info_list

    def call(self, messages: list[LlmMessage]) -> LlmMessage:
        response = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        return response


def _text_response(content: str) -> LlmMessage:
    return LlmMessage(role="llm", content_blocks=[TextBlock(type="text", content=content)])


def _tool_use_response(
    tool_use_id: str, name: str, input_: dict[str, str | int | float | bool]
) -> LlmMessage:
    return LlmMessage(
        role="llm",
        content_blocks=[ToolUseBlock(type="tool_use", id=tool_use_id, name=name, input=input_)],
    )


def _multi_tool_use_response(
    uses: list[tuple[str, str, dict[str, str | int | float | bool]]],
) -> LlmMessage:
    return LlmMessage(
        role="llm",
        content_blocks=[
            ToolUseBlock(type="tool_use", id=tool_use_id, name=name, input=input_)
            for tool_use_id, name, input_ in uses
        ],
    )


def test_run_returns_text_response_with_single_call() -> None:
    ToolCatalog.register(FakeAddTool())
    registry = ToolRegistry(["add"])
    provider = FakeLLMProvider(registry.get_all_tool_info(), [_text_response("done")])
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry)

    result = loop.run("hello")

    assert provider.call_count == 1
    first_block = result.content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "done"


def test_run_executes_tool_then_returns_final_response() -> None:
    ToolCatalog.register(FakeAddTool())
    registry = ToolRegistry(["add"])
    provider = FakeLLMProvider(
        registry.get_all_tool_info(),
        [
            _tool_use_response("1", "add", {"num1": 1, "num2": 2}),
            _text_response("3"),
        ],
    )
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry)

    result = loop.run("請幫我算 1+2")

    assert provider.call_count == 2
    final_block = result.content_blocks[0]
    assert isinstance(final_block, TextBlock)
    assert final_block.content == "3"

    # messages 應該是: user 提問 -> llm tool_use -> user tool_result -> llm 最終回覆
    assert len(loop.messages) == 4
    tool_result_block = loop.messages[2].content_blocks[0]
    assert isinstance(tool_result_block, ToolResultBlock)
    assert tool_result_block.is_error is False
    assert tool_result_block.content == 3.0


def test_run_raises_when_max_iterations_exceeded() -> None:
    ToolCatalog.register(FakeAddTool())
    registry = ToolRegistry(["add"])
    provider = FakeLLMProvider(
        registry.get_all_tool_info(),
        [_tool_use_response("1", "add", {"num1": 1, "num2": 2})],
    )
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry, max_iterations=3)

    with pytest.raises(MaxIterationsExceededError):
        loop.run("一直呼叫工具")

    assert provider.call_count == 3


def test_run_raises_unknown_tool_error_when_tool_not_registered() -> None:
    ToolCatalog.register(FakeAddTool())
    registry = ToolRegistry(["add"])
    provider = FakeLLMProvider(
        registry.get_all_tool_info(),
        [_tool_use_response("1", "does-not-exist", {})],
    )
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry)

    with pytest.raises(UnknownToolError):
        loop.run("呼叫未註冊的工具")


def test_run_short_circuits_tool_execution_after_total_failure_limit() -> None:
    ToolCatalog.register(FakeFailingTool())
    failing_tool = ToolCatalog.get("fail")
    registry = ToolRegistry(["fail"])
    provider = FakeLLMProvider(
        registry.get_all_tool_info(),
        [
            _tool_use_response("1", "fail", {}),
            _tool_use_response("2", "fail", {}),
            _text_response("done"),
        ],
    )
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry, total_failure_limit=1)

    result = loop.run("一直呼叫會失敗的工具")

    assert isinstance(failing_tool, FakeFailingTool)
    # 第二次呼叫時已經達上限,應該被短路,不再真的執行 tool.execute()
    assert failing_tool.call_count == 1
    final_block = result.content_blocks[0]
    assert isinstance(final_block, TextBlock)
    assert final_block.content == "done"

    second_result_block = loop.messages[4].content_blocks[0]
    assert isinstance(second_result_block, ToolResultBlock)
    assert second_result_block.is_error is True


def test_run_groups_multiple_tool_results_in_one_message_after_limit_reached() -> None:
    ToolCatalog.register(FakeFailingTool())
    ToolCatalog.register(FakeAddTool())
    registry = ToolRegistry(["fail", "add"])
    provider = FakeLLMProvider(
        registry.get_all_tool_info(),
        [
            _tool_use_response("1", "fail", {}),
            _multi_tool_use_response(
                [
                    ("2", "fail", {}),
                    ("3", "add", {"num1": 1, "num2": 2}),
                ]
            ),
            _text_response("done"),
        ],
    )
    loop = AgentLoop(llm=provider, messages=[], tool_registry=registry, total_failure_limit=1)

    loop.run("一次要求呼叫兩個工具,其中一個已經達上限")

    # messages: user提問 -> llm(fail) -> user(結果1) -> llm(fail+add) -> user(結果2,應合併成一則) -> llm(done)
    assert len(loop.messages) == 6
    combined_result_msg = loop.messages[4]
    assert len(combined_result_msg.content_blocks) == 2

    short_circuited, add_result = combined_result_msg.content_blocks
    assert isinstance(short_circuited, ToolResultBlock)
    assert short_circuited.tool_use_id == "2"
    assert short_circuited.is_error is True
    assert isinstance(add_result, ToolResultBlock)
    assert add_result.tool_use_id == "3"
