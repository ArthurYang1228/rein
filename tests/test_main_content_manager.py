"""MainContextManager 的單元測試。

一律用可控制的 FakeLLMProvider 驅動,不呼叫真實 API、不需要 API key。
"""

from typing import Any

import pytest

from core.content_manage.main_content_manager import MainContextManager
from core.exceptions import NonRetryableLLMError, RetryableLLMError
from core.interfaces.llm_message_model import LlmMessage, TextBlock, ToolResultBlock, ToolUseBlock
from core.interfaces.llm_provider import LLMProvider
from core.interfaces.tool_info_model import ToolInfo


class FakeLLMProvider(LLMProvider):
    """可設定 token 計數、summarize 回應/例外序列的假 provider。"""

    def __init__(
        self,
        max_context_tokens: int = 1000,
        per_message_tokens: int = 100,
        total_tokens: int | None = None,
        call_results: list[LlmMessage | Exception] | None = None,
    ) -> None:
        self._max_context_tokens = max_context_tokens
        self._per_message_tokens = per_message_tokens
        self._total_tokens = total_tokens
        self._call_results = call_results or []
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []
        super().__init__([])

    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> list[ToolInfo]:
        return tool_info_list

    def count_tokens(self, messages: list[LlmMessage], only_user_prompt: bool = False) -> int:
        if only_user_prompt:
            return self._per_message_tokens * len(messages)
        if self._total_tokens is not None:
            return self._total_tokens
        return self._per_message_tokens * len(messages)

    def get_max_context_tokens(self) -> int:
        return self._max_context_tokens

    def call(
        self,
        messages: list[LlmMessage],
        system_prompt: str | None = None,
        tool_info_list: list[ToolInfo] | None = None,
    ) -> LlmMessage:
        self.call_history.append(
            {"messages": messages, "system_prompt": system_prompt, "tool_info_list": tool_info_list}
        )
        result = self._call_results[min(self.call_count, len(self._call_results) - 1)]
        self.call_count += 1
        if isinstance(result, Exception):
            raise result
        return result


def _text_msg(role: str, content: str) -> LlmMessage:
    return LlmMessage(role=role, content_blocks=[TextBlock(type="text", content=content)])  # type: ignore[arg-type]


def _tool_use_msg(tool_use_id: str, name: str) -> LlmMessage:
    return LlmMessage(
        role="llm",
        content_blocks=[ToolUseBlock(type="tool_use", id=tool_use_id, name=name, input={})],
    )


def _multi_tool_use_msg(ids_and_names: list[tuple[str, str]]) -> LlmMessage:
    return LlmMessage(
        role="llm",
        content_blocks=[
            ToolUseBlock(type="tool_use", id=tid, name=name, input={})
            for tid, name in ids_and_names
        ],
    )


def _tool_result_msg(tool_use_id: str, name: str) -> LlmMessage:
    return LlmMessage(
        role="user",
        content_blocks=[
            ToolResultBlock(
                type="tool_result", tool_use_id=tool_use_id, name=name, is_error=False, content="ok"
            )
        ],
    )


def _multi_tool_result_msg(ids_and_names: list[tuple[str, str]]) -> LlmMessage:
    return LlmMessage(
        role="user",
        content_blocks=[
            ToolResultBlock(
                type="tool_result", tool_use_id=tid, name=name, is_error=False, content="ok"
            )
            for tid, name in ids_and_names
        ],
    )


def test_maybe_compact_returns_same_object_when_under_threshold() -> None:
    provider = FakeLLMProvider(max_context_tokens=1000, total_tokens=100)
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [_text_msg("user", "hi")]

    result = cm.maybe_compact(messages)

    assert result is messages
    assert provider.call_count == 0


def test_maybe_compact_replaces_oldest_messages_with_summary_when_over_threshold() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        per_message_tokens=200,
        call_results=[_text_msg("llm", "摘要內容")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [
        _text_msg("user", "第一句"),
        _text_msg("llm", "第二句"),
        _text_msg("user", "第三句"),
        _text_msg("llm", "第四句"),
    ]

    result = cm.maybe_compact(messages)

    # 200*len 累加到 >= 500(目標比例 0.5*1000)需要收 3 則(200,400,600 停在第 3 則)
    assert len(result) == 1 + (len(messages) - 3)
    summary = result[0]
    assert summary.role == "user"
    assert summary.provider_data is None
    first_block = summary.content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "摘要內容"
    assert result[1:] == messages[3:]


def test_compact_never_splits_tool_use_from_its_tool_result() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        per_message_tokens=300,
        call_results=[_text_msg("llm", "摘要")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [
        _text_msg("user", "任務指令"),
        _tool_use_msg("1", "add"),
        _tool_result_msg("1", "add"),
        _text_msg("llm", "最終結論"),
    ]

    result = cm.maybe_compact(messages)

    # 邊界理論上落在第 2 則(300*2=600 >= 500)之後,但第 2 則帶 ToolUseBlock,
    # 必須連第 3 則(對應的 ToolResultBlock)一起收進壓縮範圍。
    assert len(result) == 2
    assert result[1] == messages[3]


def test_compact_groups_multiple_tool_uses_in_one_message_with_their_results() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        per_message_tokens=300,
        call_results=[_text_msg("llm", "摘要")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [
        _text_msg("user", "任務指令"),
        _multi_tool_use_msg([("1", "add"), ("2", "subtract")]),
        _multi_tool_result_msg([("1", "add"), ("2", "subtract")]),
        _text_msg("llm", "最終結論"),
    ]

    result = cm.maybe_compact(messages)

    assert len(result) == 2
    assert result[1] == messages[3]


def test_compact_call_suppresses_tools_during_summarization() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        call_results=[_text_msg("llm", "摘要")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [_text_msg("user", "hi"), _text_msg("llm", "hello"), _text_msg("user", "hi2")]

    cm.maybe_compact(messages)

    assert provider.call_history[0]["tool_info_list"] == []


def test_compact_retries_on_retryable_error_then_succeeds() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        call_results=[RetryableLLMError("暫時失敗"), _text_msg("llm", "摘要成功")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000, retry_wait_second=0)
    messages = [_text_msg("user", "hi"), _text_msg("llm", "hello"), _text_msg("user", "hi2")]

    result = cm.maybe_compact(messages)

    assert provider.call_count == 2
    first_block = result[0].content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "摘要成功"


def test_compact_raises_after_exhausting_retries() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        call_results=[RetryableLLMError("一直失敗")],
    )
    cm = MainContextManager(
        provider, max_context_tokens=1000, max_llm_retries=2, retry_wait_second=0
    )
    messages = [_text_msg("user", "hi"), _text_msg("llm", "hello"), _text_msg("user", "hi2")]

    with pytest.raises(RetryableLLMError):
        cm.maybe_compact(messages)

    assert provider.call_count == 3  # 原始呼叫 + 2 次重試


def test_compact_propagates_non_retryable_error_immediately() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        call_results=[NonRetryableLLMError("格式錯誤")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)
    messages = [_text_msg("user", "hi"), _text_msg("llm", "hello"), _text_msg("user", "hi2")]

    with pytest.raises(NonRetryableLLMError):
        cm.maybe_compact(messages)

    assert provider.call_count == 1


def test_init_uses_provided_max_context_tokens_without_querying_provider() -> None:
    class ExplodingProvider(FakeLLMProvider):
        def get_max_context_tokens(self) -> int:
            raise AssertionError("不該被呼叫,因為 max_context_tokens 已經明確提供")

    cm = MainContextManager(ExplodingProvider(), max_context_tokens=500)

    assert cm.max_context_tokens == 500


def test_init_defaults_max_context_tokens_to_80_percent_of_provider_limit() -> None:
    provider = FakeLLMProvider(max_context_tokens=1000)
    cm = MainContextManager(provider)

    assert cm.max_context_tokens == 800


def test_maybe_compact_does_not_crash_on_empty_messages_when_over_threshold() -> None:
    provider = FakeLLMProvider(
        max_context_tokens=1000,
        total_tokens=2000,
        call_results=[_text_msg("llm", "空歷史摘要")],
    )
    cm = MainContextManager(provider, max_context_tokens=1000)

    result = cm.maybe_compact([])

    assert len(result) == 1
    first_block = result[0].content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "空歷史摘要"
