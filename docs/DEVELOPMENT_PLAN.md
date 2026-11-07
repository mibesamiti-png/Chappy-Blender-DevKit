# CBDK 現状分析と継続実装計画

更新: 2026-11-07 JST。正本は `docs/project/STATE.json`。本書は優先順と判断理由を説明する。

## 現在の完了単位（2026-11-07 JST）

開始HEAD87ceb5d、指定feature/v0.18-shape-diagnosticsで継続。PR #25はドラフト、正式v0.17.0。開始時に直近コード5dc799aの6CI成功を確認。今回の修正コード2867ab3も対象6CI全成功。下の初回調査・各節目は履歴として保持する。

既存NEXT-023と、それを受け入れ条件に持つNEXT-020の実装・検証を完了。条件証拠・同条件比較・失敗/不一致除外・独立合成再実行と時間/メモリ観測を一括検証した。既存NEXT-005の実測検討も完了。無関係な新規NEXT番号は追加しない。完了後は既存NEXT-019/009の形状差分と設定/コードのレビュー連携へ戻る。

現在の要件は43件（実装済26、一部13、未実装3、保留1）。作業は23件（完了16、進行中6、未着手0、保留1）。異なる粒度を混ぜて完了率とせず、CI成功だけでpartialをimplementedへ昇格しない。実データ/GUI/権利/正式提供の未確認を残す。

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
