# RiskPolicy 的覆寫規則集中定義,不由 Tool 自行宣告

同一個 `RiskLevel`,不同工具有時需要對應到不同的 `ApprovalAction`(例如都是 `HIGH` risk,但 tool A 用強制打字確認、tool B 用按鈕確認)。這個彈性可以用「`Tool` 自己宣告偏好的覆寫」或「集中寫在 `RiskPolicy`」兩種方式達成。

決定:覆寫規則集中定義在 `RiskPolicy`(`(RiskLevel, 工具) → ApprovalAction` 的 override 表),不讓 `Tool` 介面附帶審批相關欄位。

## Rationale

- **稽核成本**:安全模組的稽核者要能一次看完「風險等級 × 工具 → 審批動作」的全貌,而不用另外翻每個工具檔案有沒有偷宣告覆寫。
- **利益衝突**:讓「會被審批擋下來的工具」自己決定「審批要怎麼擋自己」,等於球員兼裁判,可能被誤用來悄悄放寬自己的風險等級。
- **介面單純**:維持 `Tool` 介面窄(ISP,只需 `name`/`schema`/`execute`),不讓審批政策的知識滲透進工具介面。

這個決定表面上跟 `ToolRegistry`「加工具不用改核心」的開放封閉精神有點反直覺,新增工具需要特殊審批行為時,是去改 `RiskPolicy` 的設定(加一條 override),而不是去改 `PermissionManager` 的判斷邏輯——開放封閉原則本身沒有被違反,只是「加設定」而非「加宣告在工具上」。