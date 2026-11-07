# CBDK — AI並行開発チーム運用マニュアル

適用：Chappy Blender DevKit（CBDK）の開発ブランチ。運用初版：2026-11-08 JST。
**GitHubの本ファイルを正本**とし、Notionは人間向けの閲覧用ミラーにする。
開発コードと検証済み状態の正本は `docs/project/STATE.json`、生成引き継ぎは `docs/PROJECT_HANDOFF.md`。
この運用書は安全な分業のための手順であり、未承認のリリース・ライセンス決定・私有データ実行の許可ではない。

## 役割・所有ファイル・ブランチ

| 担当 | 役割 | 原則として編集できる範囲 | ブランチ |
|---|---|---|---|
| A（司令塔） | 要件分割、編集範囲の調整、PRレビュー、統合CI、STATE/引き継ぎ/Notion同期、次ラウンドの発行 | 共通ドキュメント・CI・共有基盤（専任で変更する場合のみ） | `feature/v0.18-shape-diagnostics`、検証時の `work/v018-integration-*` |
| B（GLB解析） | 形状・部品対応・比較/差分・BVH・合成fixture | `cbdk/glb_*`、GLB固有テストとBlender smoke、GLB専用文書 | `work/v018-glb-analysis` |
| C（UI生成） | UI-001/BUILD-001、モード/入力/登録/解除/生成テンプレート | `cbdk/ui_layout.py`、`cbdk/modular_builder.py`、`templates/modular_preview/`、関連UI固有テスト/文書 | `work/v018-ui-builder` |
| D（Extensions品質） | EXT-001、ZIP/manifestのfail-closed診断、公式validatorの合成検証 | `cbdk/extension_*`、関連テスト/Extensions専用文書 | `work/v018-extension-quality` |
| Codex（追加戦力） | 必要時のみ重い実装、性能測定、複雑なCI障害、独立した大規模改修 | **Aが割り当てた専用ブランチ・明示ファイルのみ** | `work/v018-codex-<task>`（例。実際のtask名を指定） |

**共通ファイルの所有権はAに一本化**する。`AGENTS.md`、`.agents/skills/`、`docs/project/STATE.json`、`docs/PROJECT_HANDOFF.md`、`docs/DEVELOPMENT_PLAN.md`、`docs/V018_COMPLETION_GATES.md`、`docs/PROGRESS.md`、`docs/NOTION_SYNC.md`、`.github/workflows/`、`cbdk/__main__.py` は原則Aが変更する。専門担当が共通ファイルの更新を要するときは PR 説明に提案し、Aが単独で担当割当する。既存の所有者間でファイルが重なる場合も先にAが調整する。

## 1. 開発ラウンド開始（Aが指示）

1. 現在の `feature/v0.18-shape-diagnostics`、PR #25、`AGENTS.md`、`STATE.json`、`PROJECT_HANDOFF.md`、`V018_COMPLETION_GATES.md`、Codexスキルを読み、**最新ブランチの実測**を確認する。歴史的な完了数や旧コミットを現在の証拠にしない。
2. B/C/Dにそれぞれ衝突しない変更可能なファイル、機能ID、合格条件、禁止事項、作業ブランチ、成果物を指定する。必要に応じてGitHub Issueでタスクを固定する。
3. 専門担当は基点SHAを記録し、専用ブランチの**現状を確認**してから編集。既存の変更や他担当のコミットを上書き/強制pushしない。PRは `feature/v0.18-shape-diagnostics` 宛のドラフト。
4. 1ラウンドで関連する変更を1つのレビュー可能なPRに収める。Codexには同じファイルを並行で編集させない。

## 2. 専門チームの完了条件

- 新旧機能の互換性、異常系、明示された受け入れ条件を実装と単体テストで確認する。
- Blender実行が必要なら**信頼できるCBDK自作合成fixtureのみ**を実行し、対象 Blender 版の実際のGitHub Actions結果を確認する。ヘッドレス検査をWindows実GUIの成功と呼ばない。
- PR本文に「今回の変更」「変更ファイル」「基点SHA/コードSHA」「CI名/実行URL」「失敗/保留」「実データ・GUI・ライセンス等の未検証事項」「Aに必要な共通文書変更」を書く。
- `main`への変更、正式配布、未承認の部品採用、私有GLB/アドオンの実行・公開、GitHub→Blender直接自動インストールは担当権限に含めない。
- `STATE.json`、生成引き継ぎ、共通CI、Notionは**専門チームが直接同期しない**。最新の担当ブランチと実測リンクをAに渡す。

## 3. Aの統合ゲート（個別成功と統合成功は別）

1. 全PRの現行HEAD、変更ファイルの交差、draft状態と既存ベースからの差分を確認する。必要ならAが取り込み順序・競合ファイルの所有者を再指定する。
2. **本流に先にマージしない**。独立の統合候補ブランチにB/C/Dの変更を組み合わせ、ドラフトPRで検証する。GitHubの自動マージを使わない。
3. 統合した**同一コードSHA**でPython/Windows/Blender（4.4.3, 4.5.15, 5.2.1）/Chromium/Handoff、変更が関係する場合はKit/Skillを確認。失敗・取消・未実施・旧SHAの緑表示を成功に数えない。
4. 本当に合格した場合のみAが統合方法を判断する。ソースPRを個別に取り込む場合は統合候補と二重適用しない。ファイルのblobコピーだけの候補PRは、元PRのマージ履歴を自動では閉じない。
5. 共通の進捗更新は `STATE.json` → `python scripts/project_handoff.py --write` → `--check` → 仕様/進捗記録 → GitHubコミット。Notionは確認済み・私有情報を含まない節目だけ更新し、結果が確認できなければ pending とする。
6. `v0.19` 以降の計画承認は**開始ゲートの省略ではない**。現行 `v0.18` の自動化可能な仕事と未確認の人間ブロッカーを正しく区別して判定する。正式版はv0.17.0維持（将来の変更はライブ正本で確認）。

### 初回ラウンドの参照（歴史的な実例。常に最新HEADを確認）

- B: [PR #27](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/27) GLBの数値トポロジー不一致レビュー。
- C: [PR #26](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/26) 宣言的UI混合モード・登録解除復旧。
- D: [PR #28](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/28) ZIP安全性・validator診断の境界。
- A: [PR #29](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/29) 独立統合候補 `work/v018-integration-bcd`、SHA `e445b12c9a66541ba13bfb10ee6bc0007078c24b`。合計17ファイルの変更は互いに重複せず、対象コードSHAでPython859件×3版、Windows、Chromium、Handoff、Blender3版の**5ワークフロー成功**。ただし別の個別PRのマージ・正式v0.18統合は行われていない。

## 4. Codexの利用上限・利用不可時の代替ルート（必須）

**Codexが使えることを開発の必須条件にしない。** 上限や利用不能の期間は予測せず、復活を待つ指示だけで止めない。

| 状況 | 作業の進め方 |
|---|---|
| Codexが利用可能・大規模な独立タスクがある | Aが範囲・基点・受け入れ条件・専用ブランチを指定。Codexはコード+テスト+ドラフトPRを返す。 |
| Codexの使用量上限・利用不可 | **B/C/Dが既存の担当範囲で作業継続**。Aはタスクを小さく分割し、軽量な修正・仕様/テスト/CI診断を割り振る。Codex専任の作業がクリティカルパスにならないようにする。 |
| 重い計算・Blender検証が必要 | CodexなしでもGitHub Actionsなど**既存の独立CI**で合成fixtureを検証。必要に応じて処理範囲を縮小し、測定不能なら未検証として記録する。 |
| Codexでしか実施できない範囲、または必要な道具がない | Aが `blocked_needs_codex` などの**運用上のブロッカーとしてPR/Issueに記録**し、独立した他の仕事を進める。これは既存の `STATE.json` の正式ステータス値に勝手に追加しない。 |
| Codexが再利用可能になった | GitHubに残るタスク説明・未解決ログ・現行ブランチ差分から再開。古い作業ブランチをそのまま上書きせず最新状態へ整合する。 |

Codexの代替は「チェックなしの手動マージ」ではない。**安全検証・CIが通らなければ保留する**。ChatGPTチャットだけで得られない実Windows GUI確認、ユーザーデータ実験、ライセンス承認も自動的には完了しない。

## 5. 中断・会話喪失時の再開

- 新しいA/B/C/Dチャットは `AGENTS.md` → この文書 → `.agents/skills/chappy-blender-devkit/SKILL.md` → `STATE.json` → `PROJECT_HANDOFF.md` → 自分のPR/ブランチ/CIを確認。前のチャットの記憶に依存しない。
- Aが所有者割当、前回の統合候補PR、取り込み済み/未取り込みのPR、未検証結果を再点検。各専門チームは元の専用ブランチと未マージ変更を上書きしない。
- Notionは人間向け手順・概要、GitHubは**コードと最新実測の正本**。同期していない場合はそれを明記する。

## 6. 効率測定と次ラウンド

ラウンド単位で (a) PR1件がレビュー可能になるまでの期間、(b) 共通ファイル衝突件数、(c) 統合CI再実行/失敗数、(d) Aの手動調整量、(e) Codexの投入有無とその理由を**実測のみ**短く記録し、分業が本当に効率化しているか判断する。件数・テスト数自体の増加を目的にしない。

次の作業候補は各担当のPRと `docs/V018_COMPLETION_GATES.md` の最新残条件から選ぶ。特にBは数が同じでも位置の違う穴・エッジなどの誤認、CはUI側のモード判定と生成テストの境界、DはExtensionsの既知/未知診断と安全な未承認拒否が候補。**具体的なタスクは必ず最新ベースに合わせてAが再選定する**。
