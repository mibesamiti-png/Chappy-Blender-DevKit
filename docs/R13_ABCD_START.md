# R13 ABCD正式割当（#99統合後に有効、実装未着手）

開始条件: R11/R12 A統合、統合SHAの独立7CI成功、AのSTATE/Handoff/PROGRESS/キュー同期完了。コード統合ab42913と独立7CIは成立済み。本割当PR #99のCI成功・dev統合を最後の開始条件とする。着手時は最新devを取得する。

| 担当 | branch | 編集可能パス | 負例・受け入れ |
| --- | --- | --- | --- |
| B P2 | work/v018-glb-analysis-r13 | cbdk/glb_*、GLB専用tests/docs | seed追加、除外6–9、密疎反転位置。投影回数は校正し速度と分離。全辞書R2/R8一致、R3独立、予算維持。欠陥/反復利得なしならtests/docsのみ |
| C P1 | work/v018-ui-builder-r13 | templates/modular_preview/、UI専用tests/docs | enable失敗のmodule eviction、旧pending ledger、新importによる隠蔽、原参照で明示回復。3Blender版で新marker、foreign保全・漏れ0、既存R5–R12/5機能6レシピ維持 |
| D P2 | work/v018-extension-quality-r13 | cbdk/extension_*、Extensions専用tests/docs | 同commit/異inventory、読取中変更、junction/leaf/8.3、未知basis。許可外読取0、不明はfail-closed、権利false、ZIP制限/7正例維持 |

各担当は共通STATE/Handoff/PROGRESS/Notion/CI/scriptsを編集しない。依存は同期済み最新devだけ。相互未統合変更に依存しない。専門各最終HEADにPython3/Windows2/Blender3/Chromium/Handoffの5系統、Aは結合HEADで再検証。OS capability不足はskip、実GLB/GUI/第三者共存/権利は未確認のまま。

## チャットへ送る共通プロンプト

AGENTS.md、PARALLEL_DEVELOPMENT.md、PARALLEL_ROLLING_QUEUE.md、最新STATE/Handoffを読み、R13開始ゲートを確認してください。最新dev HEADから上表の担当専用branchへ分岐し、担当の負例・受け入れ条件だけを実装してください。各担当最大1件の未統合追加draft PR。共有台帳/Notion/共通CIはA管理。Codex利用不能でも安全な作業は継続可能。旧R11/R12 PRを二重取り込みせず、main/正式リリース/私有データ/未承認採用は行わない。関連テスト→確定HEADの5系統CI→正確な結果と未検証をAへ提出してください。
