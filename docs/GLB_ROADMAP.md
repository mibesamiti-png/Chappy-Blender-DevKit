# CBDK GLB-019 → GLB-022 開発ロードマップ

更新日: 2026-11-07 JST（引き継ぎで再確認したユーザー指定の優先順）

このロードマップは **機能計画**。正式リリース v0.17.0 と、開発中のドラフトPR #25を混同しない。状態の正本は [STATE.json](project/STATE.json) と生成 [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md)。

| ID | 目標 | 状態 | 次の扱い | Notion |
|---|---|---|---|---|
| GLB-019 | 実際の参照GLBと生成GLBを読み込み、表面距離・開口差・特徴優先解析を既存比較へ統合 | **implemented / blender_ci** | 合成モデルでCI成功。実ユーザーGLB・512三角形超・個別部品対応は追加検証 | [タスク](https://app.notion.com/p/410948b7493781e888acd4392249365d) |
| GLB-020 | **形状差分の3D可視化**。差の位置、部品、規模を赤/黄などの色と凡例で確認 | **partial / blender_ci** | 匿名部品別の色付きGLBと集計JSONに加え、オフラインHTMLで左右連動3Dビューを追加（Blender3版/JS構文CI成功）。実Chromium操作CI・空間的な部品候補表示に加え、追加24点で誤差増大を観測した面の紫枠表示も成功。未測定領域の完全把握、部品同一性の証明、実ユーザーGLBは残る。詳細 [仕様](GLB_DIFF_VISUALIZATION.md) | [タスク](https://app.notion.com/p/410948b7493781f7a88cf4781588ee25) |
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

### GLB-020 第4段階：候補推定・Chromium実操作CI

- 部品対応候補を位置・寸法・三角面数の相互最近傍と曖昧度で提示。候補の手動表示は可能だが、部品の同一性の証明や自動修正ではない。
- コードSHA `72e9bd4e4ad2cb9b9716ee0cb5ea10de60cd779e` では、[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183982)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184368)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184086)・[Windowsキット](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184021)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183990)・[Chromium実ブラウザ操作](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183979)が**全6系統success**。
- 今後は未観測領域・表示遮蔽精度・実ユーザーモデルの検証を進める。GLB-021/022は未実装のまま。

### GLB-020 第5段階：追加測定で感度のある面を紫枠強調

- 既存24点の色は維持し、別の24点で誤差が増えた面だけ紫枠表示（ローカルHTML）。集計JSONには匿名部品別の件数と未検証フラグのみ。
- コードSHA `38057b1da49eeb61020664c4923ced2b2bad8406`： [Python 42279824321](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824321)、[Windows 42279824307](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824307)、[Blender 4.4.3/4.5.15/5.2.1 42279824378](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824378)、[Windows kit 42279824398](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824398)、[引き継ぎ 42279824427](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824427)、[Chromium GUI 42279824304](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824304) **全6系統success**。
- **紫枠無し＝検証済みではない**。全体未観測領域、内壁の詳細検証、実GLB、部品同一性の証明は次の課題。GLB-021/022は未着手。

### GLB-020 第6段階：開口や欠損面を調べる境界エッジ監査

- 各匿名メッシュ部品で、近接座標の辺共有を数え、**観測上の境界辺数**と非多様体候補を集計。ローカルHTMLの部品一覧にも境界辺数を表示。
- 単独の空間的な部品対応候補でも、境界の有無・非多様体の状態が食い違うと`ambiguous`へ降格。**一致した部品という証明・自動補修はしない**。
- Pythonでは閉じた四面体/1面欠損/非多様体辺を検証。Blender3版CIには合成GLBの閉四面体0本、開四面体3本を検査する工程を追加。
- **未保証**：境界0本でも閉じたソリッド・空洞無し・小穴無しとは言えない。近接統合は浮動小数点許容差の影響あり。詳細[境界エッジ仕様](GLB_BOUNDARY_AUDIT.md)。
- GLB-020は一部実装、GLB-021/022は未実装。CI成功情報はテストSHAを確認して追記。

#### 第6段階のCI証拠

コードSHA `2cec6c99082107a4f2a65459f36f641b189f3bc5` の [Python 42284401645](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401645)・[Windows 42284401719](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401719)・[Blender 4.4.3/4.5.15/5.2.1 42284401757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401757)・[Windowsキット 42284401594](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401594)・[引き継ぎ 42284401833](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401833) は全て success。 [Chromium 42284401610](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401610) は別途結果確認中。

### GLB-020 第7段階：境界線の3D位置表示（レビュー用）

- `compare_viewer.html`の左右Canvasに推定境界線を水色で重ねる。チェックでオン・オフ、匿名部品別の絞り込み、視点同期に追従。推定線分は**私有HTMLにのみ含み**、GitHub/Notionで共有する集計JSONに元の座標を残さない。
- テスト対象のコードSHA `2a2bc8c33aaf4d11811e7892a8bbc51542b316b4`： [Python 42286544157](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544157)、[Windows 42286544061](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544061)、[Blender 4.4.3/4.5.15/5.2.1 42286543992](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543992)、[Windowsキット 42286543968](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543968)、[引き継ぎ 42286543977](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543977)、[Chromium実GUI 42286544018](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544018) **全6系統成功**。
- **制約**：X-ray的な線分表示は遮蔽の正確さを保証しない。線がなければ穴がないとは断定できず、意図した開口と欠陥も自動で区別できない。GLB-020は一部実装、GLB-021/022未実装、正式版v0.17.0/ドラフトPR #25維持。
