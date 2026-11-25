# CBDK通常開発 R17 — 完成条件優先の正式割当

2026-11-25 JST。**本書を含むA節目同期PRのdev統合・その新HEAD独立7系統CI全成功・Issue #125のR17 normal更新をAが確認するまでは設計のみ。** R17はv0.19開始や正式リリースではない。

## R16受入証拠

A統合[#130](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/130) はB#126/C#124/D#127の10パスを一度だけ取り込み、各5CI、結合 `bb93d51773cb646c073ba282ecf20d1e893197fd` 5CI成功。Blender3版の実行ログ各63チェック（R16 6項目）。dev `b9936b35a17ec538c61e82622eabaf8bfcf3bc35` の独立7CI全成功：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525702)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525596)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525689)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525694)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525609)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525591)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45520525679)。旧PRを二重マージしない。詳細は[PROGRESS](PROGRESS.md)。R16は検証・文書とコメントのみで機能挙動変更なし。

## R17の目的と受入条件（各1件の限定バッチ）

| 担当・専用枝 | 既存完成条件に直結する実装 | 受入・停止条件 |
|---|---|---|
| B NEXT-008/009・GLB-021/022 `work/v018-glb-analysis-r17` | 既存のGLB focus、AST候補、実測済み合成反復の私有triageを利用し、ユーザーが次に確認する部品/観測差分/設定宣言/試行結果/停止理由を一箇所から追える改善レビューにする。既存 `cbdk/glb_experiment_triage.py` 等を先に確認し、重複する新形式を作らず不足のみ実装。B所有 `cbdk/glb_*` と専用tests/docs。 | 既存の自作合成成功・棄却・未完了の一連の証拠を使い、優先候補と未測定/矛盾を区別。対象の確認/再試行の前提を明示、実パラメータ因果や値の推奨・自動実行/変更・真正性は認定しない。既存レポートで十分なら利用手順を示して停止。私有GLB/実アドオンの許可が必要な残りはブロッカー化。 |
| C UI-001/BUILD-001 `work/v018-ui-builder-r17` | 固定5機能の既存宣言UIを、レシピごとに選択可能な限定の表示名・配置/グループ化・既存型付き設定で構成できるようにする。現在の `cbdk/ui_layout.py`、`cbdk/modular_builder.py`、`templates/modular_preview/` を先に確認し、必要なら安全なレシピ別データ入力を明示的に追加。C所有の上記パス、`catalog/ui_layouts.json`、C専用tests/docs。既存レシピや共通API変更は最小、所有衝突はAへ。 | 旧レシピ出力/既存5機能6レシピを維持、少なくとも2種の異なる自作レイアウトで静的計画→生成→3版Blender Panel.draw/実operator→解除を実証。任意Python/RNA型/operator/sourceパス、モード安全境界拡大禁止。汎用任意アドオンや実Windows GUI未検証を明示し、残りを限定。 |
| D EXT-001 `work/v018-extension-quality-r17` | 必須manifest検査に続く未実装のoptional構造（blender_version_max、permissionsを優先）を、既存データ専用 `cbdk/extension_manifest*.py` / preflightに一括実装し、正式Extensions生成に必要な未対応とowner入力を区別。対象3版の公式仕様/CLI実測を利用。D所有 `cbdk/extension_*`、専用tests/docs。Aはこのタスクに限り既存 `scripts/verify_extension_manifest.py` のデータ専用fixture追加を明示許可（共有CI設定は変更不可）。 | 正常/異常/未対応を同じバッチで検証、固定6既存例・7プレビュー・ZIP上限を維持。公式validateとの差異は不明/不一致として明記、値/パス/未知キーの漏洩禁止。合成データ専用、ライセンス選択・正式ZIP/公開・任意ソース実行不可。実ライセンス/正式配布待ちは分離して停止。 |

A: 既存のSTATEとv0.18完成ゲートで上記成果がどの残条件を満たしたかを判定。新しい研究ロードマップやチェックリストを増やさず、未達のうち自動化可能なものとユーザー/権利/GUI待ちを分離する。R17の目的が満たされれば次の負例ラウンドを自動追加しない。

## 実行と終了ルール

- 開始時に最新dev/AGENTS/STATE/Handoff/正式割当/Issue #125と対象PR・CIを確認。必須文書は省略しない。CIサマリー→必須job/新規実行マーカー・失敗詳細の順。確認済み同一SHAの証拠は再利用可。既存ゲートは不変：専門最終HEAD各5系統、結合HEAD5系統、dev独立7系統、Blender4.4.3/4.5.15/5.2.1実測。必要な新CIのみ起動し、未実行を成功扱いしない。
- 一担当一PR。関連実装・正負例・実行を一括処理し、既存PRに短いHEAD/成果/CI/未検証/次アクションを残す。実装の利益がなければ理由を残し停止。新管理ツール、DILアダプタ、新しい研究、意味のない再検証、他担当の無断変更を行わない。効率は既存記録で観測できる範囲のみ、比較できなければ未測定。
- 既存のA所有STATE/HANDOFF/PROGRESS/CI/Notionとmain・正式v0.17.0、研究#114/#115、v0.19〜22 active=falseを維持。私有GLB/元ソース・派生物の公開/実行、実Windows GUI保証、ライセンス/公開承認、GitHub直接インストールは禁止。正式受入・追加権限・マージはAの既存ゲートとownerの別承認に従う。
