"""工具註冊與查找。"""

from typing import List

from core import Tool
from core.ToolCatalog import ToolCatalog
from core.interfaces.tool_info_model import ToolInfo


class ToolRegistry:
    """工具的註冊與查找。

    新增工具只需要往這裡註冊,不用改動 AgentLoop 核心迴圈(開放封閉原則)。
    """

    def __init__(self, tool_name_list: List[str]):

        self.tool_dict = {tool_name: ToolCatalog.get(tool_name) for tool_name in tool_name_list}

    def add_tool(self, tool_name: str) -> None:
        self.tool_dict[tool_name] = ToolCatalog.get(tool_name)

    def remove_tool(self, tool_name: str) -> None:
        del self.tool_dict[tool_name]

    def get_tool(self, tool_name: str) -> Tool:
        return self.tool_dict[tool_name]

    def get_all_tool_info(self) -> List[ToolInfo]:
        return [tool.get_info() for tool in self.tool_dict.values()]

    # /grill-me tool 相關的功能我有些想法: 在tool_registry中會匯入並實例化所有的tool，agent_loop 會先呼叫get_all_tool_info得到
    # 所有tool的資訊(名稱、函數名稱、輸入參數、輸出參數)，然後傳給LLM，LLM可以回傳json，其中若包含tool則agent_loop會呼叫get_tool取得工具實例，
    # 然後傳入參數，把結果回傳給LLM，最終LLM會給出包含結果標記和message的格式，這就是最終loop結束的地方，會有一個介面tool，包含一個函數get_info，
    # 會傳傳一個json，舉例如: {tool_name:'caculator', describe:"計算加減乘除", functions:["add":{param:["num1":float, "nums2":float], output:float, describe:"進行加法的函數" }]}
    # 這樣的格式，所有tool會實作這個介面然後放在 rein\tools\ 中，tool_registry 初始化時傳入要用工具的名稱列表，會進去實例所有工具，
    # 生成一個包含 tool_name_list: List[str], tool_list:dict {tool_name: tool_object}, tool_info:{tool_name:tool_object.get_info()}
    # 我這樣對於 agent_loop 、 tool_registry、 tool介面 各自的資料規範設想是否合理並符合原則和業界實務?

    # 工具的操作可以並行節省時間? 對於整個專案哪些部份需要做非同步?
