# A代行 R11/R12統合・R13正式割当 実験記録

実行主体: Codexセッション。Astraは依頼上の実験名で、モデル同一性・純粋推論時間・トークン費用は未計測。全計測時刻UTC。

開始 2026-11-08T01:02:17Z、開始dev `a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`。前セッションの応答後、ユーザー指示による再開 01:12:23Z。待機を純粋作業時間へ算入しない。

## 取り込み・品質

R11 #91 `faab6ab023f50495c719d091b29f320aa6ab36df` はR12 #96 `f222e20d01995489ed4612ec37230defe054fbd7` の祖先。累積13ファイルを最新dev基点のA候補へblob単位で同一確認して取り込んだ。B/C/D専門PR #88–#90/#93–#95や旧統合候補を重ねてマージしていない。競合0、本体/CI変更0（tests/docsのみ）。R11/R12専用回帰22件、C実機マーカー各4件/各Blender版。製品不具合を新たに発見・修正したとの主張はない。

[#98](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/98) 最終HEAD `8b3edeb960c7ecabbbd91b096415c9986060a66d`、最初の統合コミット01:03:05Z、PR作成01:03:09Z。候補5CI: Python42432535081 / Windows42432535143 / Blender42432533843 / Chromium42432535110 / Handoff42432535130すべて成功。実ログで4.4.3/4.5.15/5.2.1のnative_r11/native_r12各4件を独立確認。ローカルPython3.12.14は1076件発見、1074成功/Windows専用2skip、40.585秒。登録監査5機能6レシピ成功。

ユーザー許可に基づくdev限定squash: 2026-11-08T01:12:45Z、`ab42913d300efd003450027a2697586e15ca76ad`。main/正式v0.17.0/未承認部品/私有データは変更なし。

旧レポート[CODEX_R11_BENCHMARK.md](CODEX_R11_BENCHMARK.md)（#92最終4c2a25a）、[CODEX_R12_BENCHMARK.md](CODEX_R12_BENCHMARK.md)（#97最終60123ea）を原文保存。過去時点の未統合記述は履歴であり現在状態は本記録とSTATEを優先。旧レポートPRも再マージ不要。

## 統合後の独立CIと計測

[durable handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260441)、[Windows kit package](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260440)、[Agent Skill package](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260362)、[offline 3D browser interaction smoke](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260376)、[Python tests](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260317)、[Windows PowerShell launcher regression](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260329)、[Blender multi-version runtime smoke](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260358)

7系統全成功の最終job終了: 2026-11-08T01:16:04Z。統合から 199 秒。個別・統合前CIを流用していない。

手動dispatchが自動PR #25起動と重複し7件余分に実行された。失敗修正の再試行ではないが無駄な実行として記録。今後は自動runを取得して不足familyだけdispatchする。CI構造は変更していない。

| Run | event | 結果 | queue proxy秒 | 実行span秒 | job実行合計秒 |
|---|---|---|---:|---:|---:|
| [42433258355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433258355) | workflow_dispatch | success | 4 | 58 | 147 |
| [42433260317](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260317) | pull_request | success | 3 | 48 | 126 |
| [42433260329](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260329) | pull_request | success | 3 | 67 | 121 |
| [42433260358](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260358) | pull_request | success | 4 | 190 | 471 |
| [42433260362](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260362) | pull_request | success | 4 | 5 | 5 |
| [42433260376](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260376) | pull_request | success | 4 | 36 | 36 |
| [42433260440](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260440) | pull_request | success | 3 | 7 | 7 |
| [42433260441](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260441) | pull_request | success | 3 | 6 | 6 |
| [42433260564](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433260564) | workflow_dispatch | success | 4 | 50 | 99 |
| [42433262994](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433262994) | workflow_dispatch | success | 4 | 172 | 466 |
| [42433265137](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433265137) | workflow_dispatch | success | 9 | 41 | 41 |
| [42433266991](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433266991) | workflow_dispatch | success | 14 | 38 | 38 |
| [42433269049](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433269049) | workflow_dispatch | success | 4 | 6 | 6 |
| [42433271309](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42433271309) | workflow_dispatch | success | 34 | 9 | 9 |

計測方法: GitHub Actions API run.created_at→最初のjob.started_atをqueue proxy、job開始最小→終了最大を実行span、各jobの差の和を実行合計とした。並列実行合計は壁時計時間と異なる。run.updated_atは成功時刻として使わない。純粋編集/思考/API待ち/レビュー待ちの完全分離は未計測。

## R10 Aとの比較

| 指標 | R10 | 今回R11/R12 A | 解釈 |
|---|---|---|---|
| 統合PR作成→最終必須job成功 | #86 23:36:06→23:39:21、195秒 | #98 01:03:09→01:06:03、174秒 | 同じGitHub時刻算式で直接比較可能、難易度は異なる |
| 統合PR merge | #86 23:39:44 | #98 01:12:45 | 今回は会話再開待ちを含む |
| 状態同期PR | #87 作成23:37:14→最終CI23:46:41、567秒、merge23:46:59 | #99 作成01:04:02、最終CI/mergeはPRの最終HEADで確認 | 最初の文書準備CIを最終同期CIに代用しない |

R10日付は2026-11-07、今回2026-11-08（UTC）。R10最終HEAD #86 `6a12b7fa1926912f501c80b133d0d457cdc19999`、#87 `f850996e71ed989e53120732bd50fa4427e33fec`。R11開始→統合候補CI成功16分01秒、R12同10分01秒は各原レポートの参考指標。今回は二ラウンドの統合と台帳回復を含むため速度優劣・モデル性能は断定しない。専門PR・旧CIの詳細は原レポート参照。今回A候補失敗0/修正再試行0、追加の重複dispatch7、Handoff空行7行を正規生成で修正。

## 状態・ABCD復帰

要件44件: implemented26 / partial16 / not_implemented1 / deferred1。NEXT24件: done18 / in_progress5 / deferred1。新規完了昇格なし。実GLB/Windows GUI/第三者Addon/ライセンス/正式Extensions/Pages未確認。v0.19〜0.22承認済み・未有効（現行自動化ゲート未完）。

A状態同期・正式割当は[#99](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/99)。STATE/生成Handoff/PROGRESS/queueを同期し、同PR最終HEADの発火CI成功を確認してdev限定統合する。そのmergeCommitが文書同期後の再開基点。自己参照する最終SHAを本文へ埋め込むためのCI再実行は行わず、PR APIのhead.sha/merge_commit_shaと完了コメントを証拠とする。

Notion: 節目同期の実結果はSTATE maintenance_policy.notion_sync_statusを参照（古い成功を再利用しない）。既存ページ410948b7-4937-8144-9462-ca76e9567e75だけ更新、新規ページなし。

ABCDへ戻す手順: #98統合・ab42913の7CI・#99のCIとmergeを確認→最新dev fetch→[R13正式割当](R13_ABCD_START.md)とキューの担当枝へ各1追加draft PR。旧PR群は履歴として保存し二重merge/force pushしない。R13実装は未着手。Bは中間密度/閾値、Cは旧module参照の回復、Dはinventory/path alias。共通台帳/CI/NotionはA。未完了時は#99最終HEADからCI結果を確認し、コード統合をやり直さない。

Notion節目書込は成功（警告なし）。初回はinsert_contentのcontent引数不足でvalidation_error、書込なし。content指定へ修正した1回の再試行で成功。R13は#99統合後という条件を正確に同期済み、統合後に同じ節を完了表記へ更新する。
