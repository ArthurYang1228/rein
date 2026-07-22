#!/bin/bash
# 對 staged 變更做 Claude Code review，唯讀、限制回合數與預算
# 見 CLAUDE.md「Code Review 指令」一節
#
# 注意：完整的 staged 檔案清單一律用 git diff --cached 自己抓，不依賴 pre-commit
# 傳入的檔名參數——避免因為 pre-commit 把大量檔案分批傳參，導致這支腳本（進而
# claude -p）在同一次 commit 裡被重複呼叫好幾次。
#
# max-turns / max-budget-usd 調高過：預設的 5 turns 對「一次改很多檔案」的大 commit
# （例如專案骨架初始化）不夠用——每讀一個檔案大約吃掉 1 turn，5 turns 撐不了幾個檔案，
# 回合用完會直接中止且不會重試。日常小 commit（改 1-3 個相關檔案）用不到這麼多額度，
# 但拉高上限只是給大 commit 更多餘裕，不影響小 commit 的實際花費。

ALL_STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$ALL_STAGED" ] && exit 0

CODE_FILES=$(echo "$ALL_STAGED" | grep '\.py$')

RESULT=$(claude -p "請依 CLAUDE.md 的規範 review 這次 commit。

以下是本次 commit staged 的所有檔案（不限副檔名）：
$ALL_STAGED

其中屬於程式碼變更、需要做第 1-5 項審查的檔案：${CODE_FILES:-（無 .py 變更）}

重點檢查：(1) 是否違反單一職責、依賴反轉、開放封閉原則
(2) 有沒有過度設計（為單一實作硬套 pattern）
(3) 安全/成本相關程式碼是否 fail closed
(4) 有邏輯卻沒對應測試的地方
(5) 型別註記與 docstring 是否完整
(6) 檢查上面完整的 staged 檔案清單：是否有金鑰、憑證、API token、.env、個人存取憑證等敏感資訊被誤加入版控；
    是否有私人學習筆記/草稿/非公開文件被誤加入；.gitignore 是否遺漏了應該排除的檔案類型。
    這一項是安全底線，寧可誤報也不要漏報。
格式問題交給 ruff，不用檢查。
若發現嚴重問題（第 6 項一旦命中一律視為嚴重），回覆開頭輸出 'BLOCK:' 加原因；否則輸出 'OK' 加簡短建議。" \
  --allowedTools "Read,Grep,Glob" \
  --max-turns 30 \
  --max-budget-usd 2.00 \
  --output-format text)
CLAUDE_EXIT=$?

# fail closed：claude CLI 沒跑成功（未安裝、認證失效、逾時、預算超支等）就視為
# review 沒有真的執行，不能因此放行——安全相關的失敗要擋下，不能靜默通過。
if [ "$CLAUDE_EXIT" -ne 0 ] || [ -z "$RESULT" ]; then
  echo "⚠️  claude review 未能正常執行（exit code: $CLAUDE_EXIT），依 fail-closed 原則擋下 commit。"
  echo "    請確認 claude CLI 已安裝且已登入，或用 git commit --no-verify 明確略過。"
  exit 1
fi

echo "$RESULT"
if echo "$RESULT" | grep -q "^BLOCK:"; then
  echo "❌ Claude review 發現嚴重問題，已擋下 commit。要略過請用 git commit --no-verify"
  exit 1
fi
exit 0
