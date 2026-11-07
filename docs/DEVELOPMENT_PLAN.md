# CBDK 現状分析と継続実装計画

更新: 2026-11-07 JST。正本は `docs/project/STATE.json`。本書は優先順と判断理由を説明する。

## 調査した基準

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

## 優先する作業

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
