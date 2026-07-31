# RiskClassifier 與 CostMonitor 保持獨立分類器,只在 PermissionManager 匯流

`RiskClassifier` 判斷的是單一操作內容(無狀態的 pattern match),`CostMonitor` 判斷的是對話累積花費(有狀態、隨時間累加的門檻比對)。兩者資料型態與判斷方式完全不同,若合併成一個分類器會違反單一職責(CLAUDE.md:「`CostMonitor` 不該管審批,`RiskClassifier` 不該碰 API 呼叫」)。

決定:兩者各自獨立輸出信號(`RiskLevel` / 成本門檻狀態),只在 `PermissionManager` 這一層匯流做最終決策。「事前審查」的定義因此從「這一次工具呼叫前」放寬為「下一步不可逆行動發生前」,涵蓋工具呼叫與繼續消耗預算兩種情境,不需要為預算風險另立第三種時間分類。

## Considered Options

- 把預算超支併入 `RiskLevel`(例如新增一個「預算風險」判斷規則到 `RiskClassifier`)——否決,因為會讓一個無狀態的規則引擎背負有狀態的累積判斷職責。