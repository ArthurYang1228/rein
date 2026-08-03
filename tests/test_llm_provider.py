"""ToolCatalog 的單元測試。"""

import pytest


from core.interfaces.llm_provider import LLMProvider
from core.interfaces.llm_message_model import TextBlock, ToolUseBlock, ToolResultBlock, LlmMessage
from test_tool_catalog import FakeTool
from pydantic import ValidationError


def test_LlmMessage_block() -> None:

    with pytest.raises(ValidationError):
        msg = LlmMessage(role='nonligel-role')


def test_LlmMessage_block() -> None:

    with pytest.raises(ValidationError):
        msg = LlmMessage(role='nonligel-role')



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
