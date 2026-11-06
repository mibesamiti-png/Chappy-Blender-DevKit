# CBDK GLB-019 → GLB-022 開発ロードマップ

更新日: 2026-11-07 JST（引き継ぎで再確認したユーザー指定の優先順）

このロードマップは **機能計画**。正式リリース v0.17.0 と、開発中のドラフトPR #25を混同しない。状態の正本は [STATE.json](project/STATE.json) と生成 [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md)。

| ID | 目標 | 状態 | 次の扱い | Notion |
|---|---|---|---|---|
| GLB-019 | 実際の参照GLBと生成GLBを読み込み、表面距離・開口差・特徴優先解析を既存比較へ統合 | **implemented / blender_ci** | 合成モデルでCI成功。実ユーザーGLB・512三角形超・個別部品対応は追加検証 | [タスク](https://app.notion.com/p/410948b7493781e888acd4392249365d) |
| GLB-020 | **形状差分の3D可視化**。差の位置、部品、規模を赤/黄などの色と凡例で確認 | **partial / blender_ci** | 匿名部品別の色付きGLBと集計JSONに加え、オフラインHTMLで左右連動3Dビューを追加（Blender3版/JS構文CI成功）。実ブラウザ操作、クロスGLB部品対応、未測定領域表示は残る。詳細 [仕様](GLB_DIFF_VISUALIZATION.md) | [タスク](https://app.notion.com/p/410948b7493781f7a88cf4781588ee25) |
| GLB-021 | **アドオン設定の改善候補と連携**。例: ソケットの開口差→該当しそうな設定候補を人がレビュー | **not_implemented / not_tested** | AST静的解析・差分診断と結び、不明な関連は推測として分離 | [タスク](https://app.notion.com/p/410948b7493781efb123c459b521312e) |
| GLB-022 | **生成→比較→改善の反復実験**。許可済み合成アドオンのパラメータを変更してGLB再生成と改善測定 | **not_implemented / not_tested** | まずCBDK自作・allowlistの合成アドオンのみ。人手の確認・測定履歴を保持 | [タスク](https://app.notion.com/p/410948b74937811ea006d4d6bd55b1dc) |

## GLB-019 — 実装済みとの判断境界

- コード: `cbdk/glb_surface_pipeline.py` と `scripts/blender_glb_surface_review.py`。ローカル2GLBを静的preflight後にBlenderで読込、BVH表面距離と特徴優先多解像度を集計。既存 `glb-regression --surface-review` へ明示opt-in統合。
- 2026-11-06の合成データによるBlender 4.4.3 / 4.5.15 / 5.2.1 CI成功（[run 42257317535](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317535)）。PRの後続HEADも別途検証する。
- **未保証:** 任意実ユーザーGLBの完全一致、大規模モデル、512三角形超、個別部品対応、内部空洞や微小穴の全検出、ユーザー作成の私有アドオン実行。

## GLB-020 — 3D可視化の受け入れ基準（計画）

1. 2つのGLBから比較した位置・距離・重要度を実形状上で視覚的に示す。例: 誤差大＝赤、中＝黄、誤差小＝中立色。閾値と座標系は明記。
2. 対象部品・カメラ視点を選べる。距離数値と表示を一致させ、未解析/曖昧部分は `unknown` と明示。
3. 合成の位置ずれ・開口ずれ・別三角分割（同一形状）の正例・負例を3版Blender CIで検証。実GLBの自動修正はしない。

## GLB-021 — 改善候補連携の受け入れ基準（計画）

1. 形状差分のカテゴリと部品を、既存の静的プロパティ宣言/使用/メッシュ・モディファイア候補へレビュー専用で照合。
2. 出力には候補パラメータ、位置、根拠、確信度、未確認事項、ユーザー確認手順を含める。元アドオンのソース本文・パス・秘密値を公開しない。
3. たとえば「ソケット開口が狭い」から「開口幅に関連しそうな設定」を提示するが、実際の因果関係や正しい補正値は人手・合成実験前に断定しない。

## GLB-022 — 改善の反復実験の受け入れ基準（計画）

1. **CBDK自作・明示allowlist登録済みの合成テスト用アドオン限定**。設定の増減・生成GLB再出力・参考GLBとの比較を繰り返す。
2. 固定基準、各試行の設定差分・数値変化・失敗/悪化/不確定をログに残す。改善方向は同じ指標と条件のもとでのみ判断。
3. 誤差の改善と「モデルの完全一致」は分ける。ユーザー私有アドオンの無断実行、自動コード書換、公開、無審査の適用は禁止。
4. 将来の任意アドオン対応は別途、権限・サンドボックス・確認UI・実機CI・ライセンスを審査する。

## 引き継ぎと記録

- 実装と検証は `docs/project/STATE.json`、生成 `docs/PROJECT_HANDOFF.md`、仕様/進捗、ドラフトPR #25に記録。
- Notion [CBDKプロジェクト](https://app.notion.com/p/410948b7493781449462ca76e9567e75) に4つのタスクIDと状態をミラー。
- **次の新規実装候補は GLB-020**。GLB-019の実ユーザーGLB実測が必要になれば先に安全確認する。

### 2026-11-07 実装進捗: GLB-020は一部実装

- Pythonの色分類と固定Blender実行で、2つのGLBへ赤/黄/灰の面別レビュー色を付ける出力を実装。
- [Blender3バージョン CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143956) の合成モデル書出/再読込は実装コードコミット `01fff174` で成功。Windowsのテストコードのパス差異は後続修正コミット `91e8b6a2` の[Actions](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264413685)で成功。正式v0.17.0、v0.18はドラフトのまま。
- **次の作業**: 元オブジェクト別の見やすさ、未知/未測定領域を偽装せず表示、連動ビューと実ユーザーGLBテスト。

### GLB-020 第2段階・部品別CI実測

- 合成2部品のGLBから、元の私有風部品名を出力せず別々に選択できる着色部品を出力。部品別赤/黄/灰色の統計もJSONに記録。
- Code SHA `7365828b287e08046d66d62fc01c5fcfc2457fed`: [Python 42265921528](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921528), [Windows 42265921533](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921533), [Blender 4.4.3/4.5.15/5.2.1 42265921506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921506), [kit 42265921516](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921516), [handoff 42265921493](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921493): **all five completed/success**.
- 参照と生成で同じ番号の部品が同じ部品とは限らない。完全な対応関係やUIはこれから。

### GLB-020 第3段階：左右連動3D比較（試作）

- `compare_viewer.html`で左右同時回転・拡大/移動、部品の独立切替、灰色の非表示を実装。色付けは24サンプル/面の参考値で、重なる面の描画にCanvas 2Dペインターの近似が残る。
- 実装・テストSHA `b5d1d27f5e7834fa22faeefb02792091c1ac87d0`：Python [42268089086](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268089086)、Windows [42268088883](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088883)、Blender 4.4.3/4.5.15/5.2.1 [42268088779](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088779)、Windowsキット [42268088823](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088823)、引き継ぎ [42268088869](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088869) **全成功**。これはHTML生成とJS構文のCIであり、ブラウザ実機の操作試験ではない。
- HTML自体は派生元3D形状を含むため**公開GitHubやNotionへの実データアップロードは禁止**。見た目の実機レビュー、未知領域・正確な部品対応の機能は次の課題。
