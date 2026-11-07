# CBDK 現状分析と継続実装計画

更新: 2026-11-07 JST。正本は `docs/project/STATE.json`。本書は優先順と判断理由を説明する。

## 現在の到達点（2026-11-07 JST）

今回NEXT-008/009の既存範囲を集中実装。双方向debug_focus、同名複数宣言を選ばない実験triage、再束縛されたconstructor別名の検出除外を追加。ローカル自作GLBで完了/未完了/模擬失敗への接続成功、b17fa4dの対象6CI成功（Python787件×3/Windows2/Blender3版）。[仕様/検証](GLB_DEBUG_TRIAGE.md)。

両タスク全体は実データの実体・登録・因果・真の部品対応が未確認で継続。NEXT-003完了とNEXT-002明示履歴の3版成功は前回実測を維持し、GUIは未検証。現行UI-001の自作5機能/6レシピ選択・検証UI、Extensions準備も自動化未完了であるため次期移行条件は未達。将来計画は承認済み・未有効のまま。次の自動化優先はUI-001：固定自作5機能を対象に、見出し/ボタン/表示順を宣言データから検証・生成する。未知operator/任意コード/正式採用は対象外。

## 現行UI-001の実装・実測（2026-11-07 JST）

開発コミット [ea0a4bf](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/ea0a4bf42a6e001b83eca5959da905bab7e1660c) で、`catalog/ui_layouts.json`の安全な固定5機能の見出し/ボタン/順序からBlenderパネルを生成し、選択された機能だけを表示できるようにした。未知operator/JSON重複/余計なフィールドを拒否し、legacy/v2の後方互換を維持。

[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102139)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102083)・[Blender3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102168)・[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102045)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102092)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42379102137)の全6CI成功。headless `Panel.draw`監査は実Windows GUIや任意UIの完成を意味しない。UI-001は`partial / blender_ci`。次世代は未有効、PR #25ドラフト、正式版v0.17.0を維持。

## UI-001 操作性改善（2026-11-07 JST）
固定5自作機能のプレビューに、Blenderのモード・active meshを使ったボタン有効/無効と、`vertex_nudge`用の範囲付きXYZ入力を追加。未知operator・入力コードの実行は引き続き禁止。生成パネルの`Panel.draw`、operator引数引継ぎ、Scene登録/解除をheadlessで確認した。コード[597ed5c](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/597ed5c9d40e750025e7d86ca9ccd525a4ca7786)の[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508527)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508424)・[Blender3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508575)・[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508465)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508411)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42380508412)は6系統成功。UI-001はpartial、Windows GUI Ctrl+Z/操作感・汎用UI・再配布権利は未確認。詳細 [UI_DECLARATIVE_PREVIEW.md](UI_DECLARATIVE_PREVIEW.md)。

## EXT-001 構造と公開ブロッカーのプレフライト（2026-11-07 JST）

コード [1f31506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/1f3150611dc9da5a4ff1c7f4d4f89042f399911c) で、既存自作legacy/modular ZIPをコード実行なしで検査し、ZIPの出自/重複/危険パス/ハッシュ不一致と、Blender Extensionsへの移行に必要なライセンス/承認/maintainer/version等の未解決条件をJSONに記録。manifest TOML/Extensions ZIPを生成しない。手元のpreview build時点のSHAは公式Blender Extension形式認証でも権利許諾でもない。

[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597364)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597323)、[Blender4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597324)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597344)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597328)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42383597372)全6系統成功。Blender CIでは両形式のZIPを実際にビルドしてpreflightがrelease-blockedと返すことを検証。EXT-001はpartial / blender_ci。正式Extensions生成・公式validate・ライセンス判断・公開承認は未完了。次世代ロードマップは未有効でv0.18を継続。[詳細](EXTENSION_PREFLIGHT.md)。

## 初回引き継ぎ基準（履歴）

- 開始ブランチ `feature/v0.18-shape-diagnostics`、開始HEAD `7a021f5978302d21d02d51bbb4b4fc263284fa1e`。
- main は調査時 `c5b63ba`。正式版・`last_verified` は v0.17.0。PR #25 は open / draft / 未マージ。
- 最新のコード・テストコミット `e254aa7e32e6ce5e06d8dd46f662f01c1e64d858` はPython 3.11/3.12/3.13、Windows 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1、Windows Kit、Handoff、Chromiumの6系統で実ジョブ成功。後続HEADは文書のみの `[skip ci]` コミットであり、HEADそのものの実行成功とは記録しない。
- 実測リンク: [Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800567)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800581)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800595)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800603)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800626)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42357800564)。
- ローカル開始時: Python 3.12.14、701件成功。ローカルBlenderは4.3.2であり、対象3版の代替証拠にはしない。

## 実装の現在地

| 領域 | 実装済みの範囲 | 未完了・検証境界 |
|---|---|---|
| 静的解析・再利用 | AST棚卸し、重複候補、静的依存、Blender API監査 | 任意依存の解決・候補の意味的同等性・採用/権利の自動認定なし |
| 生成・設計 | 7自作部品、5機能、6レシピ、登録計画・失敗するTODOテストのひな形 | 汎用UI、正式Extensions形式、正式採用/再配布は未完了 |
| 編集・検証 | 選択頂点移動、監査、ベストエフォート復元、3版ヘッドレスCI | GUI Undo/Redo、クラッシュ時の完全復元、任意実プロジェクトは未検証 |
| GLB診断 | bounds、7方向輪郭、BVH表面距離、特徴優先測定、匿名部品一覧・弱い面数候補 | 512面上限、サンプル間の穴・内部空洞・真の部品同一性は未保証 |
| GLB-020〜022 | ローカル3D差分MVP、AST候補レビュー、合成限定の適応探索 | 全体はpartial。実アドオン因果・修正値・任意コードの自動実行/修正は未実装 |
| 引き継ぎ | GitHub台帳・生成文書・CI、既存Notionミラー | 新しい部品一覧/候補の変更が台帳に未反映だったため今回補足 |

古い仕様の追補・PROGRESS・Notionの時系列記録に「未実装」が残る。履歴は保持し、現在の要約とSTATEを更新する。GLB-010は台帳のpartialを維持し、静的経路と実行時因果を区別する。

## 初回優先作業（履歴）

1. **今回 / NEXT-021:** 既存GLB-019レポートの整合性を補強。真偽値と整数を区別し、完全/途中省略した部品一覧と総面数の矛盾、面数超過のないskip、空シーンの測定を拒否する。合成GLBの実生成→再読込→ランナー検証を3版CIへ追加。STATEとNotionの現在要約を同期する。
2. **NEXT-020 / NEXT-019:** 合成反復の失敗・打切り・悪化・不確定の診断とレビューを改善。実測指標の一貫性を維持する。GLB-020の任意の追加機能は凍結。
3. **NEXT-002 / NEXT-005:** 背景Undoプローブの限界とWindows GUIでの確認項目を整理し、実際に操作した項目だけ記録。
4. **NEXT-003:** 登録計画・許可リスト・カタログ・レシピ・CIの不一致検出を改善。自動承認しない。
5. **NEXT-007〜009:** 実データ検証が必要になった際は対象と実行許可を明確にし、ローカルで確認。私有データを公開CIに入れない。
6. **UI-001 / EXT-001:** UI設計・正式パッケージ・権利確認の判断後に提供範囲を決定。INST-001は保留。

## 人間が判断する事項

- 自作/抽出部品の権利・ライセンス・正式採用、正式Extensions公開の範囲。
- 私有アドオンを実行する必要が生じた際の対象・許可・実行環境。現行の合成allowlistから自動拡張しない。
- Windows GUIの操作感とUndo/Redoの合格条件、最終リリース/マージの判断。

今回のレポート検証修正と合成CI追加は既存仕様内で実施する。マージ・正式公開は行わない。

## 今回の到達点

NEXT-021の実装・検証は完了。コード`31bf3de18c357d796194dcac369c66e55b3973bf`の全6CI成功、Python707件×3版/Windows2版/Blender3版合成4ケースを確認（[Blender実測](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722777)）。GLB-019はimplemented/blender_ci。次の実装は上記2のNEXT-019/020を優先。GLB-020/021/022はpartialを維持し、Notionへの実際の同期結果は`NOTION_SYNC.md`に記録する。

## 今回の継続単位：NEXT-022

上記優先2から「合成適応探索の失敗・打切り・人手レビュー」を選択。途中失敗で正常履歴が保存されない問題を、工程前チェックポイント、検証済みprefix保存、固定診断、日本語レビューと読取CLIで解消する。旧探索条件や任意ユーザーコード実行は広げない。関連テスト・ローカル合成試験後に一度の対象CIでまとめて確認する。[仕様](GLB022_RUN_REVIEW.md)。実測結果と次の段階はSTATE/HANDOFFを参照。

NEXT-022はコード5dc799aの全6CI成功により完了。次はNEXT-023：同一プロトコル・合成条件・予算・指標の実行レビューを読取専用で比較し、改善/失敗/不確定を一覧化する。不整合や入力改変を成功比較から除外し、任意実ユーザーアドオンへは拡張しない。GUI/権利/正式提供の別課題は維持する。

## 今回の到達点と次回

2867ab3の対象6CI全成功によりNEXT-023/NEXT-020を完了。既存NEXT-005も[3版監査/Undoの実測検討](AUDIT_RUNTIME_REVIEW.md)を記録して完了。次回は既存NEXT-019/NEXT-009のGLB-021候補レビューと許可済み合成反復履歴の対応を優先する。残るNEXT-002/003/007/008/009/019は継続、NEXT-004は保留。GLB-021/022・GUI/権利/正式提供を形式的に完了へ変更しない。新しいNEXT番号は追加していない。

## 継続中の単位：NEXT-019 / NEXT-009

GLB-021のAST候補とGLB-022の初期測定を正規化SHAで結び、完了/未完了/失敗prefixを一つの私有レビューへ整理する。関連/全体PythonとローカルBlender確認後、対象3版CIで接続を判定する。実ユーザーの設定実体・登録/効果やGUI/権利は完了にしない。[実装仕様](GLB021_EXPERIMENT_LINK.md)。

次期計画の承認・移行方針は[別管理](future/CBDK-FUTURE-019-022.md)。同じ開始承認は取り直さない。現行自動化の残作業・人間ブロッカーを[V018_COMPLETION_GATES.md](V018_COMPLETION_GATES.md)に記録し、未有効のまま保持する。

NEXT-019の測定元一致連携は79fea17の6CI/対象Blender3版成功により完了。NEXT-009の実データ実体/効果、NEXT-002のGUI、NEXT-007/008の実データ、権利確認は完了にしない。次回は既存NEXT-003の登録・依存・レシピ検査の未検出ケースを点検し、現行自動化を進める。次期計画の承認は独立ファイルに保持し、有効化条件はまだ未達。

## 現行優先作業の今回の区切り

NEXT-003の生成前AST登録/依存検査・CI一覧照合を実装し、NEXT-002の明示履歴Native Undo/Redoを単一/複数頂点・連続編集へ拡充。関連テスト後に対象CIを一括確認する。NEXT-003完了判定はCI後。NEXT-002はWindows GUI待ちを残す。次は既存NEXT-008/009の安全な自動化残りと実データ許可境界を整理し、現行UI-001の自動化可能な範囲へ進む。将来計画は未有効を維持。
