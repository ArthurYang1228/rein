"""GeminiProvider 的單元測試。

interactions.create() 一律用假的 client/response 替換,不打真實 API、
不需要真實 api_key,也不依賴網路。回應相關的物件盡量用真實的 SDK
pydantic model(google.genai._gaos.types.interactions.*)建構,不用手刻
的假物件——這樣 SDK 欄位有變動時,測試會直接建構失敗提醒我們,而不是
永遠只跟自己想像的形狀比對。

FakeFunctionCallStepNoId/FakeResponseWithoutSteps/FakeResponseWithRawSteps 是
例外:它們刻意模擬「這個屬性/型別在真實 SDK 目前的定義裡本來就不可能發生」
的情境(id 是必填欄位、Interaction 一定有 steps 屬性、steps 內容一定會被
pydantic 驗證成真正的 Step),沒辦法用真實物件表達,才維持手刻。
"""

import json
from typing import Any

import httpx
import pytest

from adapters.providers.gemini import GeminiProvider
from core.exceptions import NonRetryableLLMError, RetryableLLMError
from core.interfaces.llm_message_model import (
    LlmMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from core.interfaces.tool_info_model import ParamInfo, ToolInfo
from google.genai._gaos.lib.compat_errors import APIError
from google.genai._gaos.types.interactions.functioncallstep import FunctionCallStep
from google.genai._gaos.types.interactions.interaction import Interaction
from google.genai._gaos.types.interactions.modeloutputstep import ModelOutputStep
from google.genai._gaos.types.interactions.textcontent import TextContent
from google.genai._gaos.types.interactions.thoughtstep import ThoughtStep
from google.genai.types import CountTokensResponse, Model


class FakeFunctionCallStepNoId:
    """故意不設 id 屬性,模擬 SDK 未來把這個屬性整個拿掉的情境(不是值為 None/空字串)。

    真實的 FunctionCallStep.id 是必填欄位,沒辦法建構出一個沒有 id 的
    真實 instance,這裡只能維持手刻。
    """

    def __init__(self, name: str, arguments: dict[str, Any]) -> None:
        self.type = "function_call"
        self.name = name
        self.arguments = arguments

    def model_dump(self) -> dict[str, Any]:
        return {"type": self.type, "name": self.name, "arguments": self.arguments}


class FakeResponseWithoutSteps:
    """沒有 steps 屬性,模擬 SDK 回傳非預期型別(例如 streaming)的情境。

    真實的 Interaction 一定有 steps 屬性,這裡只是要驗證「resp 不滿足
    HasSteps」這個分支,不需要對應到真實的 Stream 型別。
    """


class FakeResponseWithRawSteps:
    """結構上滿足 HasSteps,但 steps 內容不是真實的 Step 物件。

    真實的 Interaction.steps 會被 pydantic 驗證,塞不進
    FakeFunctionCallStepNoId 這種非 Step 型別的假物件,只有在需要驗證
    「不是真的合法回應」這種情境時才維持用這個手刻的 wrapper。
    """

    def __init__(self, steps: list[Any] | None) -> None:
        self.steps = steps


def _fake_api_error(status_code: int | None) -> APIError:
    """建構一個帶指定 status_code 的假 APIError,不需要真的發過 HTTP 請求。"""
    request = httpx.Request("POST", "https://example.com")
    err = APIError("模擬 API 錯誤", request, body=None)
    err.status_code = status_code
    return err


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
    resp = Interaction(
        status="completed", steps=[ModelOutputStep(content=[TextContent(text="你好")])]
    )

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 1
    block = content_blocks[0]
    assert isinstance(block, TextBlock)
    assert block.content == "你好"
    assert provider_data[0]["type"] == "model_output"


def test_process_response_function_call_produces_tool_use_block(
    provider: GeminiProvider,
) -> None:
    resp = Interaction(
        status="completed", steps=[FunctionCallStep(id="1", name="add", arguments={"num1": 1.0})]
    )

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 1
    block = content_blocks[0]
    assert isinstance(block, ToolUseBlock)
    assert block.id == "1"
    assert block.name == "add"
    assert block.input == {"num1": 1.0}


def test_process_response_mixed_steps(provider: GeminiProvider) -> None:
    resp = Interaction(
        status="completed",
        steps=[
            ModelOutputStep(content=[TextContent(text="先說話")]),
            FunctionCallStep(id="1", name="add", arguments={"num1": 1.0}),
        ],
    )

    content_blocks, provider_data = provider._process_responce(resp)

    assert len(content_blocks) == 2
    assert isinstance(content_blocks[0], TextBlock)
    assert isinstance(content_blocks[1], ToolUseBlock)
    assert len(provider_data) == 2


def test_process_response_no_steps_returns_empty(provider: GeminiProvider) -> None:
    resp = Interaction(status="completed", steps=None)

    content_blocks, provider_data = provider._process_responce(resp)

    assert content_blocks == []
    assert provider_data == []


def test_process_response_unhandled_step_type_only_recorded_in_provider_data(
    provider: GeminiProvider,
) -> None:
    resp = Interaction(status="completed", steps=[ThoughtStep()])

    content_blocks, provider_data = provider._process_responce(resp)

    assert content_blocks == []
    assert provider_data[0]["type"] == "thought"


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

    def fake_create(**kwargs: Any) -> Interaction:
        captured_kwargs.update(kwargs)
        return Interaction(
            status="completed", steps=[ModelOutputStep(content=[TextContent(text="回覆內容")])]
        )

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    result = provider.call(messages)

    assert captured_kwargs["input"] == [
        {"type": "user_input", "content": [{"type": "text", "text": "你好"}]}
    ]
    assert captured_kwargs["system_instruction"] == provider.system_prompt
    assert isinstance(result, LlmMessage)
    assert result.role == "llm"
    first_block = result.content_blocks[0]
    assert isinstance(first_block, TextBlock)
    assert first_block.content == "回覆內容"
    assert result.provider_data is not None
    assert result.provider_data[0]["type"] == "model_output"


def test_call_sends_configured_system_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """system_prompt 真的會被帶進 system_instruction,不是永遠固定的空字串。"""
    provider = GeminiProvider(
        tool_info_list=[],
        system_prompt="請用繁體中文回答",
        api_key="fake-key-for-testing",
    )
    captured_kwargs: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> Interaction:
        captured_kwargs.update(kwargs)
        return Interaction(status="completed", steps=[])

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    provider.call([LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="嗨")])])

    assert captured_kwargs["system_instruction"] == "請用繁體中文回答"


def test_init_falls_back_to_default_client_when_api_key_is_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """api_key 是空字串時,視同沒提供,退回 genai.Client() 無參數建構。"""
    captured_kwargs: dict[str, Any] = {}

    def fake_client(**kwargs: Any) -> object:
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.setattr("adapters.providers.gemini.genai.Client", fake_client)

    GeminiProvider(tool_info_list=[], api_key="")

    assert captured_kwargs == {}


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


def test_process_response_generates_fallback_id_when_step_missing_id_attr(
    provider: GeminiProvider,
) -> None:
    """step 上根本沒有 id 這個屬性時(不是 None/空字串),要補一個 fallback id。"""
    resp = FakeResponseWithRawSteps(
        steps=[FakeFunctionCallStepNoId(name="add", arguments={"num1": 1.0})]
    )

    content_blocks, _ = provider._process_responce(resp)

    assert len(content_blocks) == 1
    block = content_blocks[0]
    assert isinstance(block, ToolUseBlock)
    assert block.id.startswith("fallback-")


@pytest.mark.parametrize("status_code", [429, 500, 503, None])
def test_call_classifies_as_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int | None
) -> None:
    def fake_create(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(RetryableLLMError):
        provider.call(messages)


@pytest.mark.parametrize("status_code", [400, 401, 404, 422])
def test_call_classifies_as_non_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    def fake_create(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(NonRetryableLLMError):
        provider.call(messages)


def test_call_classification_preserves_original_message(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_create(**kwargs: Any) -> Any:
        raise _fake_api_error(429)

    monkeypatch.setattr(provider.client.interactions, "create", fake_create)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(RetryableLLMError, match="模擬 API 錯誤"):
        provider.call(messages)


def test_count_tokens_returns_total_tokens(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_count_tokens(**kwargs: Any) -> CountTokensResponse:
        return CountTokensResponse(total_tokens=42)

    monkeypatch.setattr(provider.client.models, "count_tokens", fake_count_tokens)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    assert provider.count_tokens(messages) == 42


def test_count_tokens_payload_includes_system_prompt_history_and_tools(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_kwargs: dict[str, Any] = {}

    def fake_count_tokens(**kwargs: Any) -> CountTokensResponse:
        captured_kwargs.update(kwargs)
        return CountTokensResponse(total_tokens=1)

    monkeypatch.setattr(provider.client.models, "count_tokens", fake_count_tokens)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    provider.count_tokens(messages)

    payload = captured_kwargs["contents"]
    assert isinstance(payload, str)
    # json.dumps 預設會把非 ASCII 字元轉義成 \uXXXX,解析回來再用 ensure_ascii=False
    # 重新序列化,才能用中文字面比對,不會被逃逸序列誤判成「找不到」。
    parsed = json.loads(payload)
    flattened = json.dumps(parsed, ensure_ascii=False)
    assert "你好" in flattened
    assert "add" in flattened  # 來自 provider fixture 註冊的工具名稱


def test_count_tokens_raises_when_total_tokens_missing(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_count_tokens(**kwargs: Any) -> CountTokensResponse:
        return CountTokensResponse(total_tokens=None)

    monkeypatch.setattr(provider.client.models, "count_tokens", fake_count_tokens)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(ValueError):
        provider.count_tokens(messages)


def test_get_max_context_tokens_returns_input_token_limit(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(**kwargs: Any) -> Model:
        return Model(input_token_limit=1_000_000)

    monkeypatch.setattr(provider.client.models, "get", fake_get)

    assert provider.get_max_context_tokens() == 1_000_000


def test_get_max_context_tokens_raises_when_input_token_limit_missing(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(**kwargs: Any) -> Model:
        return Model()

    monkeypatch.setattr(provider.client.models, "get", fake_get)

    with pytest.raises(ValueError):
        provider.get_max_context_tokens()


@pytest.mark.parametrize("status_code", [429, 500, None])
def test_count_tokens_classifies_as_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int | None
) -> None:
    def fake_count_tokens(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.models, "count_tokens", fake_count_tokens)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(RetryableLLMError):
        provider.count_tokens(messages)


@pytest.mark.parametrize("status_code", [400, 401])
def test_count_tokens_classifies_as_non_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    def fake_count_tokens(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.models, "count_tokens", fake_count_tokens)

    messages = [LlmMessage(role="user", content_blocks=[TextBlock(type="text", content="你好")])]
    with pytest.raises(NonRetryableLLMError):
        provider.count_tokens(messages)


@pytest.mark.parametrize("status_code", [429, 500, None])
def test_get_max_context_tokens_classifies_as_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int | None
) -> None:
    def fake_get(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.models, "get", fake_get)

    with pytest.raises(RetryableLLMError):
        provider.get_max_context_tokens()


@pytest.mark.parametrize("status_code", [400, 401])
def test_get_max_context_tokens_classifies_as_non_retryable(
    provider: GeminiProvider, monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    def fake_get(**kwargs: Any) -> Any:
        raise _fake_api_error(status_code)

    monkeypatch.setattr(provider.client.models, "get", fake_get)

    with pytest.raises(NonRetryableLLMError):
        provider.get_max_context_tokens()
