# CBDK AI並行開発チーム運用マニュアル

> GitHubを唯一の開発状態の正本にする。Notionは確認用の節目ミラー。複数のChatGPT会話は互いに直接同期されず、GitHubのブランチ・PR・CIが受け渡しの仕組みになる。

## 1. 適用範囲・権限

- 対象リポジトリ: https://github.com/mibesamiti-png/Chappy-Blender-DevKit
- v0.18開発基点: `feature/v0.18-shape-diagnostics`、ドラフトPR [#25](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/25) → `main`。
- 最優先は `AGENTS.md`、`docs/project/STATE.json`、`docs/PROJECT_HANDOFF.md`、`docs/V018_COMPLETION_GATES.md`、既存 [Codexスキル](../.agents/skills/chappy-blender-devkit/SKILL.md)。本書はチーム間の調整方法。古いHEAD/タスク数を真実扱いしない。
- 専門チャットには **専用作業ブランチへのコミットとドラフトPRの提出**を許す。司令塔Aは個別PRをレビューし、統合候補の作成と実測検証、統合方針を決める。
- `main`へのマージ、正式リリース、正式Extension公開、権利/ライセンス決定、未承認ソース/私有アドオンの実行・採用・公開、保留されたGitHub→Blender直接インストールには**別途明示承認が必要**。CI成功はこの承認ではない。
- 現行v0.18の自動化可能ゲートが未達の間、v0.19〜0.22は承認済みだが未有効。実データ/GUI/権利ブロッカーをタスク完了に書き換えない。

## 2. 担当表と編集境界

| 担当 | 開発範囲 | ブランチ例 | 主な所有コード | 共通ファイル |
| --- | --- | --- | --- | --- |
| **A: 司令塔（ChatGPT）** | タスク整理、依存関係、統合PR、正本更新、Notion節目同期 | `feature/v0.18-shape-diagnostics`; 検証用は `work/v018-integration-*` | `docs/project/STATE.json`, `docs/PROJECT_HANDOFF.md`, `docs/PROGRESS.md`, 共通CI | Aが管理 |
| **B: GLB解析** | 形状差分、部品対応、数値的トポロジー、合成GLBテスト | `work/v018-glb-analysis` | `cbdk/glb_*`, GLB専用テスト・文書・smoke | 直接変更しない |
| **C: UI・アドオン生成** | `UI-001`、`BUILD-001`、宣言UI、登録・解除・復元 | `work/v018-ui-builder` | `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, `templates/modular_preview/`, UI専用テスト | 直接変更しない |
| **D: Extensions・品質** | `EXT-001`、ZIP安全性、マニフェスト診断、公式合成validator | `work/v018-extension-quality` | `cbdk/extension_*`, Extensions専用テスト・文書 | 直接変更しない |
| **Codex: 任意の追加戦力** | 大規模実装、難しいデバッグ、反復負荷測定・CI修正、統合不具合 | 専用ブランチ/worktree | Aが割り当てた**限定領域だけ** | 単独で正本変更・統合しない |

**ファイル所有権の競合に注意:** `cbdk/__main__.py`, `catalog/`, `scripts/` の一部、`.github/workflows/` は共同依存になりやすい。どの担当が編集するか、着手前にPR/タスク票でAが決定する。必要なら「共通ファイルの変更要求」をAへ渡す。担当外ファイルを上書きしない。

## 3. 1サイクルの実行手順

1. **Aが現状を確認**: 現行開発HEAD、PR #25、個別PR、`STATE.json`、CI結果、前回のブランチ所有者を確認。作業をB/C/Dへ振り、編集可能パス・テスト・受け入れ条件・私有データ禁止を明示する。
2. **B/C/Dが独立して作業**: 読み込み元の基点SHAを記録し、個別ブランチだけ変更。小さく焦点を絞った実装と回帰テストを加え、実際の実行環境と「未検証」を区別する。完了したらv0.18開発ブランチ向け**ドラフトPR**を提出する。
3. **AがPRを比較**: PRのhead SHA、変更ファイル一覧、現在のbase SHA、CI、衝突・共通API依存を比較。未解決なら担当へ修正を依頼。ファイル非重複でも動作の依存衝突は起こりうる。
4. **統合検証**: 原PRを改変せず必要に応じ `work/v018-integration-*` 上でコードを合わせ、**統合後の正確なcommit SHAで**Python/Windows/Blender 4.4.3・4.5.15・5.2.1/Chromiumなど影響するCIを確認する。旧PRの成功を統合CI成功と取り違えない。
5. **統合ゲート**: 統合テストが緑でも、変更内容/安全境界/未検証項目をレビューしてからAが統合判断を行う。取り込み手順と承認に従ってv0.18開発ブランチへ移す。**`main`や正式リリースへ自動マージしない。**
6. **Aが正本を更新**: `STATE.json`、`docs/PROJECT_HANDOFF.md`（`python scripts/project_handoff.py --write` と `--check`）、関係仕様・`docs/PROGRESS.md`を実測で更新し、節目だけ既存Notionへ安全な要約を同期。Notion失敗は成功扱いしない。
7. **第2ラウンド**: 統合済みSHAを次の共通基点にして担当を再割当。前回PRに未統合変更がある間、古い基点から同じ修正を重複作成しない。

### 開始前のタスク票（Issue またはPR説明に記録）

```text
Task ID:
担当 / PR / 開発ブランチ:
基点SHA:
編集可能ファイル:
編集してはいけない共有ファイル:
依存PR・先に統合すべき変更:
目的・受け入れ条件:
検証コマンド・必要なBlender版:
未検証（GUI/実ユーザーデータ/権利など）:
Codexが必要な条件 / Codexなしの代替:
完了時の成果物（コミット、PR、CI、次アクション）:
```

## 4. Codexは**任意**：上限・障害・未接続でも開発を継続

**重要: Codexが利用上限や通信エラーで使えなくても、開発停止の条件にしない。** ChatGPT専門チームB/C/Dと司令塔Aだけで開発可能な範囲を進める。Codexの枠が復活する時刻・量を推測しない。

| 状況 | 実行する方針 |
| --- | --- |
| Codex利用可能 | 大量のファイルにまたがる修正、負荷試験の整理、大きなリファクタ、統合後の複雑な不具合など**独立した高価値タスク**を依頼。担当ブランチ・対象パス・完了条件を指定 |
| Codexの利用上限・障害 | B/C/Dは担当範囲の小規模実装・静的検査・回帰テスト・文書化・CIの結果分析を継続。AはPRレビューと組合せ検証を進める |
| 変更が大きすぎる | `Codex候補`としてIssue/タスク票に入力例、再現条件、対象ファイル、未確認事項、受け入れ条件を記録。安全な小単位に分割できる部分はB/C/Dが担当 |
| 手元でBlenderやWindowsの実測不可 | CIが実行できればその結果を使い、できなければ `blocked/needs-runtime` として正確な実行コマンドを保存。テスト成功を偽装しない |
| 並行開発が混雑 | B/C/Dの作業数を減らす。競合率・レビュー待ち・CI待ちが改善するか測る。並列数を増やすこと自体を成果にしない |

**再開手順:** Codexが使える状態になったら、まず最新GitHub/PR/CIを読み、以前の未着手タスク票が現状に適合するか再確認。すでにB/C/Dが解決したタスクを繰り返さない。Codexに古いHEADを強制pushさせない。

## 5. CI・品質・プライバシー

- CIを約束したのではなく、**実測した成功/失敗/取消/未実行**を必ず分ける。head SHA一致と各matrix jobの完了を確認。必要なら差分を統合ブランチで再テスト。
- 合成モデルでの成功を任意ユーザーGLB精度と混同しない。ヘッドレスBlender UIとWindows GUI/Undoショートカットは別の証拠。公式validatorの合成例は実部品のライセンス/Extension配布許可を証明しない。
- 自作合成GLB/PNGは許可範囲でCIへ。私有GLB、派生HTML/画像、`input_sources_private/`、元コード/私有レポート、資格情報は公開GitHub・Actions artifact・Notionへ送らない。
- PRの個別CIが成功しても統合後のテストは必要。スキル/Kit workflowが未起動なら成功数に算入しない。
- 統合後に履歴を残す。不要なrebase/force pushで他チームの作業を破壊しない。

## 6. 初回運用実績（2026-11-08 JST時点のスナップショット）

- [Team C PR #26](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/26): UIの混合モード表示・後片付け復旧。基準SHA `c9163fa39e30`。
- [Team B PR #27](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/27): 数値的境界/非多様体エッジ差分の保守的な候補判定。SHA `606fd99c622b`。
- [Team D PR #28](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/28): ZIP安全監査・公式ログの厳格検査。SHA `e0ad30d2f525`。
- [Team A統合候補 PR #29](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/29): 変更17ファイルが重複せず、合体SHA `e445b12c9a66541ba13bfb10ee6bc0007078c24b`。
- 統合候補の[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42395028094) は859件×Python3版、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42395028160)、[Blender 3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42395028123)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42395028146)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42395028095)の5系統を全て成功確認。Skill/Kitはこの統合候補に対する実行証拠がないため5系統に算入しない。
- この時点で**個別/統合PRはドラフト・未マージ**。検証済みでも、統合許可やmainマージではない。進捗/次期移行の判定は最新`STATE.json`を再読して確定する。

## Notionの閲覧用マニュアル

- [CBDK — AI並行開発チーム運用マニュアル](https://app.notion.com/p/411948b7493781c49de4f175ac0b9ee6)（GitHub正本の人間向けミラー。コード/CIはGitHubを優先）
- 次ラウンドの作業票は [PARALLEL_ROUND_002.md](PARALLEL_ROUND_002.md) を参照。

## 7. 継続観測と改善

1サイクルごとに、独立PR数、統合時に実際に衝突したファイル数、CI再試行数、実装・レビューに費やした所要時間（分かる場合）、人間確認待ち件数を残す。**単純なコミット/テスト数はスピードの代理指標にしない。**初回の「編集ファイル重複0」は成功だが、今後の運用でも同じと仮定しない。

## 8. 別チャットの再開指示

「`AGENTS.md` と `docs/PARALLEL_DEVELOPMENT.md`、最新`STATE.json`、自分の担当PRを読んで、統合済み基点SHAと所有ファイルを確認。Codexが利用不可でも安全な実装を続け、未実測のCIは未実測と記録。担当ブランチのドラフトPRを提出し、共有台帳/Notionは司令塔Aへ報告。main/リリースは変更しない。」


## Notion運用マニュアル（節目同期先）

[CBDK — AI並行開発チーム運用マニュアル](https://app.notion.com/p/411948b749378108a044c697db6163d5) は本ファイルを読める形に要約した子ページ。GitHubを運用ルールの正本とし、Notionは手動の節目ミラー。Codex利用上限時でもA/B/C/Dは開発を継続する。
