"""Gemini LLMProvider 實作(adapter)。"""

from core.interfaces.llm_provider import LLMProvider
from core.interfaces.llm_message_model import LlmMessage, TextBlock, ToolUseBlock, ToolResultBlock, ContentBlock
from core.interfaces.tool_info_model import ToolInfo, ParamInfo
import inspect
from typing import Any
import json

from google import genai
from google.genai import types

from collections.abc import Callable

# from google import genai
# import os
# from dotenv import load_dotenv
# load_dotenv()
# api_key = os.getenv("GEMINI_API_KEY")
# client = genai.Client(api_key=api_key)
# history = [
#     {
#         "type": "user_input",
#         "content": [{"type": "text", "text": "寫一則笑話"}]
#     }
# ]
# interaction = client.interactions.create(
#     model="gemini-3.6-flash",
#     store=False,
#     input=history
# )
# for step in interaction.steps:
#     print(step.model_dump())
#
# {'signature': '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', 'type': 'thought'}
# {'content': [{'text': '這裡有一則輕鬆的小笑話：\n\n有一天，小明覺得眼睛不太舒服，於是去看眼科。\n\n醫生問：「你眼睛怎麼啦？哪裡不舒服？」\n\n小明很苦惱地說：「醫生，我最近看任何東西，都會看到『雙重影子』，非常模糊。」\n\n醫生點點頭，指著面前說：「這樣啊……那你先坐到這張椅子上吧。」\n\n小明看了看前面，猶豫地問：\n\n\n\n\n**「……醫生，你說的是哪一張？」**', 'type': 'text'}], 'type': 'model_output'}
# user_input / function_call /  function_result / model_output


PYTHON_TYPE_TO_JSON_SCHEMA_TYPE = {
    # 基礎型態
    "str": "STRING",
    "int": "INTEGER",
    "float": "NUMBER",
    "bool": "BOOLEAN",
    # 複合與容器型態
    "list": "ARRAY",
    "tuple": "ARRAY",
    "set": "ARRAY",
    "dict": "OBJECT"
}


class GeminiProvider(LLMProvider):
    """LLMProvider 介面的 Gemini SDK 實作。"""

    def __init__(self, tool_info_list: list[ToolInfo], sys_prompt: str = "", api_key:str|None=None, model:str="gemini-3.5-flash"):
        super().__init__(tool_info_list, sys_prompt)
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def call(self, messages: list[LlmMessage]) -> LlmMessage:

        history:list[dict[str, Any]] = []
        for msg in messages:
            if msg.provider_data is not None:
                history.extend(msg.provider_data)
                continue

            for content_block in msg.content_blocks:

                if msg.role=="user":
                    if isinstance(content_block, TextBlock):
                        block_dump = {
                            "type": "user_input",
                            "content": [{"type": "text", "text": content_block.content}]
                        }

                    elif  isinstance(content_block, ToolResultBlock):
                        block_dump = {
                            "type": "function_result",
                            "name": content_block.name,
                            "error": content_block.is_error,
                            "call_id": content_block.tool_use_id,
                            "result": [{"type": "text", "text": json.dumps(content_block.content)}]
                        }


                if msg.role=="llm":
                    if isinstance(content_block, TextBlock):
                        block_dump = {
                            "type": "model_output",
                            "content": [{"type": "text", "text": content_block.content}]
                        }

                    elif  isinstance(content_block, ToolUseBlock):
                        block_dump = {
                            "type": "function_call",
                            "name": content_block.name,
                            "call_id": content_block.id,
                            "arguments": content_block.input
                        }

                history.append(block_dump)
                


        resp = self.client.interactions.create(
            model=self.model,
            store=False,
            input=history,
            tools=self.native_tool_list
            )

        content_blocks:list[ContentBlock] = []
        provider_data: list[dict[str, Any]] = []

        for step in resp.steps:
            provider_data.append(step.model_dump())
            if step.type =="model_output":
                for c in step.content:
                    if c.type=="text":
                        content_blocks.append(TextBlock(type="text", content=c.text))

            elif step.type =="function_call":
                content_blocks.append(ToolUseBlock(type="tool_use", id=step.id,name=step.name, input=step.arguments))

        return LlmMessage(role="llm", content_blocks=content_blocks, provider_data=provider_data)

    def _process_tool_info(self, tool_info: ToolInfo) -> dict[str, Any]:

        properties = {}
        required = []
        for name, parameter in tool_info.input_schema.items():
            properties[name] = {}
            properties[name]["type"] = PYTHON_TYPE_TO_JSON_SCHEMA_TYPE[parameter.type]
            properties[name]["description"] = parameter.description
            if parameter.default == "":
                required.append(name)

        return {
            "type": "function",
            "name": tool_info.name,
            "description": tool_info.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


    
    def _process_tool_info_list(self, tool_info_list: list[ToolInfo]) -> Any:
        return [self._process_tool_info(tool_info) for tool_info in tool_info_list]


