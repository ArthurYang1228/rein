"""LLM provide 介面和資料model 的單元測試。"""

import pytest


from core.interfaces.llm_provider import LLMProvider
from core.interfaces.llm_message_model import TextBlock, ToolUseBlock, ToolResultBlock, LlmMessage
from pydantic import ValidationError
import json


def test_llm_message_block() -> None:

    with pytest.raises(ValidationError):
        LlmMessage(role="nonligel-role")  # type: ignore[call-arg, arg-type]


def test_text_block() -> None:

    with pytest.raises(ValidationError):
        TextBlock(type="t", content="test")  # type: ignore[arg-type]


def test_tool_use_block() -> None:

    with pytest.raises(ValidationError):
        ToolUseBlock(
            type="tool_use",
            id="1",
            name="add",
            input={"num1": 1, "num2": [2]},  # type: ignore[dict-item]
        )


def test_tool_result_block() -> None:

    with pytest.raises(ValidationError):
        ToolResultBlock(
            type="tool_result",
            tool_use_id="1",
            is_error=1,  # type: ignore[arg-type]
            content="success",
        )


def test_message_serial() -> None:

    tb = TextBlock(type="text", content="test")
    tub = ToolUseBlock(type="tool_use", id="1", name="add", input={"num1": 1, "num2": 2})
    tub2 = ToolUseBlock(type="tool_use", id="2", name="add", input={"num1": 3, "num2": 4})
    trb = ToolResultBlock(type="tool_result", tool_use_id="1", is_error=False, content="success")
    msg = LlmMessage(role="user", content_blocks=[tb, tub, trb, tub2])
    msg_json = msg.model_dump_json()

    try:
        # 解析成功代表格式完全合法
        json.loads(msg_json)
    except json.JSONDecodeError:
        pytest.fail("輸出不是合法的 JSON 格式")

    recover_msg = LlmMessage.model_validate_json(msg_json)
    assert isinstance(recover_msg.content_blocks[0], TextBlock)
    assert isinstance(recover_msg.content_blocks[1], ToolUseBlock)
    assert isinstance(recover_msg.content_blocks[2], ToolResultBlock)
    assert len(recover_msg.tool_uses) == 2
    assert isinstance(recover_msg.tool_uses[0], ToolUseBlock)
    assert isinstance(recover_msg.tool_uses[1], ToolUseBlock)


def test_provider_interface() -> None:
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


# class FakeProvider(LLMProvider):
#
#     def __init__(self):
#         self.tool_info_list = [FakeTool().get_info()]
#
#     def call(self, history, msg) -> LlmMessage:
#         return LlmMessage(role='llm')
#
#     def  process_tool_info_list(self) -> str:
#         all_info = [f"name:{tool_info.name}，info: {tool_info.description}" for tool_info in self.tool_info_list]
#         return "".join(all_info)


# def test_register_and_get_round_trip() -> None:
#     tool = FakeTool()
#     ToolCatalog.register(tool)
#
#     assert ToolCatalog.get("fake") is tool
#
#
# def test_is_registered_reflects_state() -> None:
#     assert ToolCatalog.is_registered("fake") is False
#
#     ToolCatalog.register(FakeTool())
#
#     assert ToolCatalog.is_registered("fake") is True
#
#
# def test_get_missing_tool_raises() -> None:
#     with pytest.raises(UnknownToolError, match="does-not-exist"):
#         ToolCatalog.get("does-not-exist")
