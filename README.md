# Rein



>一個把「人在迴路中的安全感」當核心賣點的 agent runtime。多數 agent 工具拚的是自動化程度，
Rein 在意是：**風險揭露，危險操作要有白話解釋，資源與成本要有明確上限**——寧可多一次人工確認，
也不要靜默執行有風險的操作；寧可誤報風險，也不要漏報。

## 為什麼是 Rein

現有的 agent / coding CLI 工具在「要權限時說不清楚為什麼」這件事上普遍做得不夠好。
Rein 用雙層架構處理每一次工具呼叫：

1. **確定性風險分類**——規則引擎比對已知危險 pattern，產出風險等級與觸發原因（安全底線，不交給 LLM 判斷）
2. **LLM 白話敘述**——解釋「這個操作想做什麼、為什麼需要」，輔助使用者理解，不負責安全判斷

兩者合流後，才產出審批卡片，依風險等級決定審批方式（自動核准 / 按鈕核准 / 對話確認 / 直接禁止）。

## 核心功能

**基本能力**
- LLM 呼叫
- Session 管理
- Prompt 管理
- 工具（tool）操作與註冊
- Context 管理

**安全機制（招牌功能）**
- 指令風險分類 + 白話說明（`RiskClassifier`）
- 資源與成本上限監控，含 token 費用即時追蹤與雲端資源成本護欄（`CostMonitor`）
- 多元人在迴路（HITL）審批模式（`PermissionManager`）

**進階能力（選配）**
- MCP 工具整合
- RAG 檢索

## 核心架構

| 模組 | 職責 | 說明 |
|---|---|---|
| `AgentLoop` | 核心迴圈 | LLM 思考 → 工具呼叫 → 結果回填 → 再次思考 |
| `ToolRegistry` | 工具註冊與查找 | 新增工具只需註冊，不用改動核心迴圈 |
| `PermissionManager` | 決定審批方式 | 依 `RiskClassifier` 給的風險等級選擇自動核准 / 按鈕核准 / 對話確認 / 禁止 |
| `RiskClassifier` | 風險規則引擎 | 確定性規則比對已知危險 pattern，安全底線，不交給 LLM 判斷 |
| `CostMonitor` | 成本監控 | token 費用即時追蹤、雲端資源成本護欄 |
| `ContextManager` | 上下文治理 | 對話超過水位時觸發 compact |
| `SessionStore` | Session 持久化 | 儲存與還原對話狀態 |
| `EventBus` | 事件發布/訂閱 | 供前端即時串流事件 |



## 快速開始

專案目前僅有骨架，尚未提供可執行的 CLI 或安裝步驟。等核心 Agent Loop 完成後補上：

```bash
uv sync
uv run <入口指令待補>
```

## 專案roadmap

- [ ] `AgentLoop`（核心迴圈）—— 能跑通「LLM 思考 → 工具呼叫 → 結果回填 → 再次思考」的最小閉環
- [ ] `ToolRegistry`（工具註冊與查找）—— 至少 2-3 個工具可註冊、依名稱查找並被 `AgentLoop` 呼叫
- [ ] `PermissionManager`（審批方式決策）—— 能依風險等級切換自動核准 / 按鈕核准 / 對話確認 / 禁止
- [ ] `RiskClassifier`（風險規則引擎）—— 危險 pattern 規則比對完成，且「危險指令不漏報」測試全過
- [ ] `CostMonitor`（成本監控）—— token 費用即時累計、達軟/硬上限能正確觸發警告與暫停
- [ ] `ContextManager`（上下文治理）—— 對話超過水位時能正確 compact，且不遺失關鍵資訊
- [ ] `SessionStore`（Session 持久化）—— 對話能存檔並在重啟後正確還原（resume）
- [ ] `EventBus`（事件發布/訂閱）—— agent 各動作事件能即時推送給前端



