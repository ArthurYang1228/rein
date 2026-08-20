# adapters/ 只放橋接外部系統的東西,不是「任何可能有多種實作的介面」

決定 `ContextManager` 該不該做成抽象介面、具體實作放哪裡時,一開始用錯了判斷標準:以為「adapters/ vs core/」的分野是「有沒有多種可能做法」——查證 ADK、LangGraph/LangMem、Claude Code 三家框架後,發現上下文壓縮這件事業界做法確實分歧(sliding window + salience 保護、直接讓 LLM 摘要工具結果、確定性清除+另存硬碟各不相同),一度以此當理由主張把 `ContextManager` 的具體策略放進 `adapters/`。

重新檢視後確認:`adapters/` 目前在這個專案裡的實際意涵,是「橋接到我們自己抽象之外的東西」——`GeminiProvider` 橋接 Gemini SDK、`FunctionTool` 把一個原始 Python 函式橋接進 `Tool` 介面的形狀、未來的 MCP 版本橋接外部 MCP server。這些都是把「外部、不受我們控制的東西」轉換成我們自己的抽象契約。`ContextManager` 的壓縮策略完全不是這回事——它操作的是我們自己的 `LlmMessage`,透過已經抽象好的 `LLMProvider` 做事,沒有橋接任何外部系統。

「業界做法分歧」證明的是這個設計空間本身難、有很多合理解法,不代表**這個專案內部現在就需要支援多種可替換策略**。真正該問的是:`Tool`/`LLMProvider` 之所以夠格當介面,是因為已經有**具體排定的第二個實作**在路上(`ToolInfo.type: Literal["function", "mcp"]` 已經寫死了 MCP 版本的規劃、`AnthropicProvider` 骨架已經存在)——不是因為「理論上可能有其他做法」。`ContextManager` 現在沒有這種具體排定的第二個策略,只有一個決定要做的方案。

決定:

1. `ContextManager` 保留抽象介面,但理由是「`AgentLoop` 自己的測試需要塞 `FakeContextManager`」(具體、現在就存在的需求),不是「未來可能有多種策略」。
2. 具體的策略實作維持放在 `core/`,不歸類進 `adapters/`。抽象介面 `ContextManager` 跟其他介面一樣放在 `core/interfaces/context_manage.py`;具體策略實作另開 `core/context_manage/` 套件(`MainContextManager`)。

## Considered Options

- **把壓縮策略放進 `adapters/`**——否決。會讓 `adapters/` 的意涵從「橋接外部系統」稀釋成「任何抽象介面底下的具體實作」,長期會讓這個目錄的分類標準變得模糊,每次新增模組都要重新爭論該放哪裡。
- **開一個全新的頂層目錄(例如 `implement/`)專門放「核心介面 + 可替換策略」這種東西**——否決。目前這個分類底下只有 `ContextManager` 一個成員,為單一成員先開一個頂層分類,是把「以後可能還有別的」這個未驗證的假設,提前套進專案結構裡——跟直接把 `ContextManager` 塞進 `adapters/` 是同一種過度設計,只是換了一個位置。

## Consequences

`adapters/` 的分類標準維持單純:是不是在橋接一個我們自己抽象之外的外部系統。以後如果 `PermissionManager`/`CostMonitor` 也走上「核心介面 + 可替換策略」這個形狀,且真的出現第二個具體實作(不只是「業界某家框架這樣做」這種間接證據),那時候手上有多個真實案例可以歸納,再考慮要不要把它們一起搬進一個新的共用目錄——不在現在就預先決定。
