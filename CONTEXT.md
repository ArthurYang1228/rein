# Rein

一個「人在迴路中」的 mini agent runtime。核心賣點是風險揭露、事前審批與事後品質審查——寧可多一次人工確認、寧可誤報風險,也不要靜默執行危險操作或漏報。

## 語言

### 事前:風險與審批

**RiskLevel**:
單一操作的風險等級,由 `RiskClassifier` 依操作內容(例如 bash 指令字串)做確定性 pattern 比對後產出,值為 `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`。無狀態判斷,只看這次操作本身的內容,不受歷史或對話上下文影響。
_對應_: 中文文件慣用「低 / 中 / 高 / 極高」指同一組值,是同一件事的中文說法,不是另一套分類。

**RiskClassifier**:
確定性風險規則引擎,比對已知危險 pattern 產出 `RiskLevel`。只有在 `RiskPolicy` 對這次的具體操作沒有直接記錄時才會被呼叫——不是每次工具呼叫都無條件重跑分類。
_Avoid_: 風險判斷器

**RiskPolicy**:
決定「這個操作最終要執行哪個 `ApprovalAction`」的政策,以 `RiskLevel` 為主軸(`RiskLevel → ApprovalAction` 的預設表 + 可選的 `(RiskLevel, 工具) → ApprovalAction` 覆寫),也可能有針對特定工具/指令的直接記錄(例如使用者選過「這個 session 都不要再問」而動態寫入的許可)。`PermissionManager` 查詢時,具體操作的直接記錄優先於 `RiskLevel` 層的規則。這是 session 範圍內會變動的狀態,不只是啟動時讀一次的靜態設定檔。覆寫規則集中定義在 `RiskPolicy` 本身,不由 `Tool` 自行宣告——避免審批行為分散在多處難以稽核,也避免工具自己決定「別人怎麼審查自己」。
_Avoid_: SessionPolicy(討論中曾提出的舊詞,已確認只需要一種政策概念,不要並存兩套)

**PermissionManager**:
依 `RiskPolicy` 決定要執行哪個 `ApprovalAction`:先查具體操作有沒有直接記錄,查無才呼叫 `RiskClassifier` 取得 `RiskLevel` 再查一次政策。也是 `RiskClassifier` 與 `CostMonitor` 這兩個獨立信號匯流做最終決策的地方。
_Avoid_: 審批方式決策器

**ApprovalAction**:
「取得人類事前核准」的策略介面(一次操作執行前的關卡),不同實作可以有不同流程(例如單純按鈕核准,或是需要先呼叫 LLM 生成白話說明才能呈現)。若某實作的契約要求產生白話說明卻失敗,視為這個 Action 執行失敗、fail closed,不會靜默用預設文字帶過核准。人類拒絕時,以失敗結果塞回訊息歷史,`AgentLoop` 不中斷,讓 LLM 自行尋找替代方案。
_Avoid_: 審批方式(容易和已棄用的 SessionPolicy 混用)

### 事後:結果品質審查

**ResultReviewer**:
選配的事後審查元件,透過建構子注入 `AgentLoop`(未注入則完全不啟用這一關,不是強制階段)。在 LLM 產生結論時觸發一次(目前以 `stop_reason == "end_turn"` 判斷),讓人類確認產出結果是否符合預期。跟 `ApprovalAction` 是完全獨立的機制且判斷依據不同:`ApprovalAction` 管「要不要讓某個工具呼叫發生」(風險控制,一輪任務可能觸發多次,跟 `RiskLevel` 有關);`ResultReviewer` 管「這輪任務的結論人類看過了嗎」(品質確認,一輪任務只觸發一次,跟 `RiskLevel` 無關)。
_Avoid_: HITL(泛稱,不夠精確,容易跟 `ApprovalAction` 混用)

**ReviewVerdict**:
`ResultReviewer` 的判斷結果,值為 `ACCEPT`(結束,回給使用者)或 `REJECT`(附帶人類的文字 `feedback`,回到 LLM 思考繼續下一輪)。刻意只留兩個值——沒有拆出 retry/revise,因為尚未觀察到需要分開處理的不同迴圈行為。
_Avoid_: RETRY、REVISE(討論中提出後確認是過度設計,已收斂)

### 成本

**CostMonitor**:
獨立於 `RiskClassifier` 的另一個分類器,依對話累積的 token 花費(有狀態、隨時間累加)判斷是否超過門檻,產出成本相關信號給 `PermissionManager`。跟 `RiskClassifier` 各自負責不同性質的風險來源(無狀態的內容 pattern vs 有狀態的累積門檻),只在 `PermissionManager` 這一層匯流成單一決策,不合併成同一個分類器。

### 上下文治理

**ContextManager 的 compact 保留規則**:
compact 只需要保留 LLM 思考需要的對話內容(工具執行結果、人類在 `ResultReviewer` 給的 `REJECT` 回饋等),不需要保留審批決策本身——「這個 session 已經核准過某類操作」這件事記錄在 `RiskPolicy`(狀態物件),不是記錄在對話訊息裡,不會因 compact 而遺失。

### 工具(Tool)

**Tool**:
agent 可呼叫的單一操作的抽象介面(`name`/`description`/`input_schema`/`execute`),只描述「一個可呼叫的東西長什麼樣子」,不規定實作方式。每個註冊給 LLM 的工具都是**扁平**的一個可呼叫操作,沒有「一個 Tool 底下再分多個 function」的巢狀結構——直接對齊 Anthropic/OpenAI/Gemini 原生 tool-use API 的形狀,讀檔/寫檔這類風險等級不同的操作務必拆成獨立工具。

**FunctionTool**:
`Tool` 介面目前唯一的具體實作,把一個純 Python 函式(型別註記 + docstring)包裝成符合 `Tool` 契約的物件,由 `register_tool` 裝饋器在 import 當下自動產生。工具作者只需要寫函式,不用手寫 class、不用自己實作 `Tool`。未來非本地函式的工具來源(例如 MCP)會是 `Tool` 的另一個獨立實作,與 `FunctionTool` 並存,`ToolRegistry`/`AgentLoop` 不需要因此修改。

**ToolInfo**:
描述一個工具 metadata 的 pydantic model(`name`/`description`/`input_schema`),由 `register_tool` 自省函式簽章與 docstring,在註冊當下算好一次,之後只被讀取、不重新計算。
_Avoid_: 用裸 dict/JSON 表達工具描述——一律用 pydantic model。

**register_tool**(裝饋器):
把純函式包裝成 `FunctionTool` 並加入 `ToolCatalog` 的裝饋器。註冊當下若函式缺 docstring、某個參數沒有型別註記、或用了自省邏輯目前不支援的型別,直接拋 `ToolRegistrationError`(fail fast),不產出殘缺的工具描述。第一版自省只支援 `str`/`int`/`float`/`bool` 且皆為必要參數,支援範圍不足時才擴充(YAGNI)。

**ToolCatalog**:
process 範圍、只在 import 階段填一次的全域工具集合,包含所有被 `register_tool` 裝饋過的工具,不管哪個 agent 會不會用到。
_Avoid_: 跟 `ToolRegistry` 混用——`ToolCatalog` 是宇宙全集(來源),`ToolRegistry` 是某個 agent 從這個全集篩選出來的子集合(用途)。

**ToolRegistry**:
依一份工具名稱列表,從 `ToolCatalog` **篩選**出對應子集合的元件,不會重新實例化工具(工具早在 `ToolCatalog` 填入時就是完成品)。不同 agent 可各自建立自己的 `ToolRegistry`,篩出不同子集合,彼此獨立,共用同一份 `ToolCatalog` 不會重複付出自省成本。名稱列表裡若有 `ToolCatalog` 找不到的名字,直接拋錯,不靜默略過。

**ConsecutiveFailureLimit**:
同一個工具呼叫連續驗證失敗(pydantic 驗證 LLM 給的參數不過)達上限次數時觸發的計數器,跟 `max_iterations`(整個 `AgentLoop` 的總輪數上限)是不同維度——`max_iterations` 管整體別跑太久,`ConsecutiveFailureLimit` 管別卡在同一個壞掉的呼叫上、把整體預算燒光。達上限時把「已達重試上限」的訊息塞回 message history,`AgentLoop` 不中斷、也不升級成人工確認——驗證失敗代表工具根本沒真的執行,沒有安全疑慮,只是沒效率,性質上歸 `CostMonitor` 的範疇而非 `RiskClassifier`。人類拒絕(`ApprovalAction` 的 deny)與參數驗證失敗,共用同一套「失敗結果塞回 message history、不中斷迴圈」的回饋機制。