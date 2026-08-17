# LLMProvider 不設計正規化的 stop_reason 欄位

`LLMProvider.call()` 原本直覺應該回傳一個正規化過的 `stop_reason`(對應 Anthropic 的 `end_turn`/`tool_use`),讓 `AgentLoop` 用它判斷這輪要不要繼續呼叫工具。但查證 Gemini API 的 `finishReason` 後發現:即使回應包含 `function_call`,`finishReason` 通常還是 `STOP`,不像 Anthropic 用兩個獨立值明確區分「一般結束」跟「要呼叫工具」——甚至有開發者社群回報過因為誤以為 Gemini 會有對應的 `FUNCTION_CALL` 值而踩雷。

決定:`LLMProvider` 介面不設計 `stop_reason`/`finish_reason` 欄位,`AgentLoop` 一律直接檢查回傳 `Message.content` 裡有沒有 `ToolUseBlock` 來判斷要不要繼續。既然連 Gemini 自己的原生欄位都無法只靠它可靠判斷有沒有工具呼叫,不如兩家 provider 都用同一套「檢查內容形狀」的邏輯,不用為 Gemini 額外維護一個不可靠的正規化欄位。

## Considered Options

- 幫 Gemini「發明」一個對應的正規化 `stop_reason` 值(在 `GeminiProvider` 內部自己判斷再包裝成一致的欄位)——否決,因為判斷邏輯最終還是得回頭檢查內容裡有沒有 `function_call`,等於多一層轉換卻沒有消除掉真正的判斷依據,不如讓 `AgentLoop` 直接做這個檢查。

## Consequences

「LLM 生成純文字、沒有工具呼叫」這件事,`AgentLoop` 不再進一步區分是「LLM 在問人類問題」還是「任務做完了」——這兩者在這個設計下觸發的是同一件事(這輪結束),差異留給更外層(`ResultReviewer` 或呼叫端)判讀文字內容,`AgentLoop`/`LLMProvider` 這一層完全不處理這個語意。
