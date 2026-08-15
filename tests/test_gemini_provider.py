"""GeminiProvider 的單元測試。

interactions.create() 一律用假的 client/response 替換,不打真實 API、
不需要真實 api_key,也不依賴網路。
"""

from typing import Any

import pytest

from adapters.providers.gemini import GeminiProvider
from core.interfaces.llm_message_model import (
    LlmMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from core.interfaces.tool_info_model import ParamInfo, ToolInfo


class FakeContent:
    def __init__(self, type_: str, text: str = "") -> None:
        self.type = type_
        self.text = text


class FakeModelOutputStep:
    def __init__(self, content: list[FakeContent]) -> None:
        self.type = "model_output"
        self.content = content

    def model_dump(self) -> dict[str, Any]:
        return {"type": self.type}


class FakeFunctionCallStep:
    def __init__(self, id_: str, name: str, arguments: dict[str, Any]) -> None:
        self.type = "function_call"
        self.id = id_
        self.name = name
        self.arguments = arguments

    def model_dump(self) -> dict[str, Any]:
        return {"type": self.type, "id": self.id, "name": self.name, "arguments": self.arguments}


class FakeOtherStep:
    """代表 model_output/function_call 以外的其他 step 種類(例如 thought)。"""

    def __init__(self, type_: str = "thought") -> None:
        self.type = type_

    def model_dump(self) -> dict[str, Any]:
        return {"type": self.type}


class FakeResponse:
    """結構上滿足 gemini.HasSteps 這個 Protocol。"""

    def __init__(self, steps: list[Any] | None) -> None:
        self.steps = steps


class FakeResponseWithoutSteps:
    """沒有 steps 屬性,模擬 SDK 回傳非預期型別(例如 streaming)的情境。"""


@pytest.fixture(scope="module")
def provider() -> GeminiProvider:
    tool_info = ToolInfo(
        name="add",
        type="function",
        description="兩數相加",
        input_schema={
            "num1": ParamInfo(name="num1", type="float", description="第一個數", default=""),
            "flag": ParamInfo(name="flag", type="bool", description="選填旗標", default="False"),
        },
    )
    return GeminiProvider(tool_info_list=[tool_info], api_key="fake-key-for-testing")


def test_get_history_passes_through_provider_data(provider: GeminiProvider) -> None:
    msg = LlmMessage(
        role="user",
        content_blocks=[TextBlock(type="text", content="會被忽略")],
        provider_data=[{"type": "user_input", "content": [{"type": "text", "text": "原始資料"}]}],
    )

    history = provider._get_history([msg])

    assert history == [{"type": "user_input", "content": [{"type": "text", "text": "原始資料"}]}]


def test_get_history_user_text_block(provider: GeminiProvider) -> None:
    msg = LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])

    history = provider._get_history([msg])

    assert history == [{"type": "user_input", "content": [{"type": "text", "text": "你好"}]}]


def test_get_history_user_tool_result_block(provider: GeminiProvider) -> None:
    msg = LlmMessage(
        role="user",
        content_blocks=[
            ToolResultBlock(
                type="tool_result",
                tool_use_id="1",
                name="add",
                is_error=False,
                content=3.0,
            )
        ],
    )

    history = provider._get_history([msg])

    assert history == [
        {
            "type": "function_result",
            "name": "add",
            "error": False,
            "call_id": "1",
            "result": [{"type": "text", "text": "3.0"}],
        }
    ]


def test_get_history_llm_text_block(provider: GeminiProvider) -> None:
    msg = LlmMessage(role="llm", content_blocks=[TextBlock(type="text", content="回覆")])

    history = provider._get_history([msg])

    assert history == [{"type": "model_output", "content": [{"type": "text", "text": "回覆"}]}]


def test_get_history_llm_tool_use_block(provider: GeminiProvider) -> None:
    msg = LlmMessage(
        role="llm",
        content_blocks=[ToolUseBlock(type="tool_use", id="1", name="add", input={"num1": 1.0})],
    )

    history = provider._get_history([msg])

    assert history == [
        {"type": "function_call", "name": "add", "call_id": "1", "arguments": {"num1": 1.0}}
    ]


def test_get_history_skips_role_content_combo_with_no_matching_branch(
    provider: GeminiProvider,
) -> None:
    """role="user" 搭配 ToolUseBlock 目前沒有任何分支處理,應被靜靜跳過而非報錯。"""
    msg = LlmMessage(
        role="user",
        content_blocks=[ToolUseBlock(type="tool_use", id="1", name="add", input={})],
    )

    history = provider._get_history([msg])

    assert history == []


def test_process_response_model_output_produces_text_block(provider: GeminiProvider) -> None:
    resp = FakeResponse(steps=[FakeModelOutputStep(content=[FakeContent("text", "你好")])])

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 1
    block = content_blocks[0]
    assert isinstance(block, TextBlock)
    assert block.content == "你好"
    assert provider_data == [{"type": "model_output"}]


def test_process_response_function_call_produces_tool_use_block(
    provider: GeminiProvider,
) -> None:
    resp = FakeResponse(steps=[FakeFunctionCallStep(id_="1", name="add", arguments={"num1": 1.0})])

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 1
    block = content_blocks[0]
    assert isinstance(block, ToolUseBlock)
    assert block.id == "1"
    assert block.name == "add"
    assert block.input == {"num1": 1.0}


def test_process_response_mixed_steps(provider: GeminiProvider) -> None:
    resp = FakeResponse(
        steps=[
            FakeModelOutputStep(content=[FakeContent("text", "先說話")]),
            FakeFunctionCallStep(id_="1", name="add", arguments={"num1": 1.0}),
        ]
    )

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 2
    assert isinstance(content_blocks[0], TextBlock)
    assert isinstance(content_blocks[1], ToolUseBlock)
    assert len(provider_data) == 2


def test_process_response_no_steps_returns_empty(provider: GeminiProvider) -> None:
    resp = FakeResponse(steps=None)

    content_blocks, provider_data = provider._process_responce(resp)

    assert content_blocks == []
    assert provider_data == []


def test_process_response_unhandled_step_type_only_recorded_in_provider_data(
    provider: GeminiProvider,
) -> None:
    resp = FakeResponse(steps=[FakeOtherStep(type_="thought")])

    content_blocks, provider_data = provider._process_responce(resp)

    assert content_blocks == []
    assert provider_data == [{"type": "thought"}]


def test_process_tool_info_maps_types_and_required(provider: GeminiProvider) -> None:
    tool_info = ToolInfo(
        name="add",
        type="function",
        description="兩數相加",
        input_schema={
            "num1": ParamInfo(name="num1", type="float", description="必填", default=""),
            "flag": ParamInfo(name="flag", type="bool", description="選填", default="False"),
        },
    )

    schema = provider._process_tool_info(tool_info)

    assert schema["type"] == "function"
    assert schema["name"] == "add"
    assert schema["description"] == "兩數相加"
    properties = schema["parameters"]["properties"]
    assert properties["num1"] == {"type": "NUMBER", "description": "必填"}
    assert properties["flag"] == {"type": "BOOLEAN", "description": "選填"}
    assert schema["parameters"]["required"] == ["num1"]


def test_process_tool_info_list_maps_each_tool(provider: GeminiProvider) -> None:
    tool_infos = [
        ToolInfo(name="add", type="function", description="加法", input_schema={}),
        ToolInfo(name="sub", type="function", description="減法", input_schema={}),
    ]

    schemas = provider._process_tool_info_list(tool_infos)

    assert [schema["name"] for schema in schemas] == ["add", "sub"]


def test_call_sends_history_and_parses_response(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_kwargs: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> FakeResponse:
        captured_kwargs.update(kwargs)
        return FakeResponse(steps=[FakeModelOutputStep(content=[FakeContent("text", "回覆內容")])])

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    result = provider.call(messages)

    assert captured_kwargs["input"] == [
        {"type": "user_input", "content": [{"type": "text", "text": "你好"}]}
    ]
    assert isinstance(result, LlmMessage)
    assert result.role == "llm"
    first_block = result.content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "回覆內容"
    assert result.provider_data == [{"type": "model_output"}]


def test_call_with_response_missing_steps_returns_empty_message(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """resp 不滿足 HasSteps(例如真的收到 Stream)時,目前是靜默回傳空訊息。"""

    def fake_create(**kwargs: Any) -> FakeResponseWithoutSteps:
        return FakeResponseWithoutSteps()

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    result = provider.call(messages)

    assert result.content_blocks == []
    assert result.provider_data == []
