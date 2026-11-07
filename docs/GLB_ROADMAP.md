# CBDK GLB-019 → GLB-022 開発ロードマップ

更新日: 2026-11-07 JST（引き継ぎで再確認したユーザー指定の優先順）

このロードマップは **機能計画**。正式リリース v0.17.0 と、開発中のドラフトPR #25を混同しない。状態の正本は [STATE.json](project/STATE.json) と生成 [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md)。

| ID | 目標 | 状態 | 次の扱い | Notion |
|---|---|---|---|---|
| GLB-019 | 実際の参照GLBと生成GLBを読み込み、表面距離・開口差・特徴優先解析を既存比較へ統合 | **implemented / blender_ci** | 合成モデルでCI成功。実ユーザーGLB・512三角形超・個別部品対応は追加検証 | [タスク](https://app.notion.com/p/410948b7493781e888acd4392249365d) |
| GLB-020 | **形状差分の3D可視化**。差の位置、部品、規模を赤/黄などの色と凡例で確認 | **partial / blender_ci** | 匿名部品別の色付きGLBと集計JSONに加え、オフラインHTMLで左右連動3Dビューを追加（Blender3版/JS構文CI成功）。実Chromium操作CI・空間的な部品候補表示に加え、追加24点で誤差増大を観測した面の紫枠表示も成功。未測定領域の完全把握、部品同一性の証明、実ユーザーGLBは残る。詳細 [仕様](GLB_DIFF_VISUALIZATION.md) | [タスク](https://app.notion.com/p/410948b7493781f7a88cf4781588ee25) |
| GLB-021 | **アドオン設定の改善候補と連携**。例: ソケットの開口差→該当しそうな設定候補を人がレビュー | **partial / blender_ci** | GLB-020集計差分と既存ASTプロパティ照合をレビュー専用で接続済み。原因・数値は未確定、実ユーザーソース未検証 | [タスク](https://app.notion.com/p/410948b7493781efb123c459b521312e) |
| GLB-022 | **生成→比較→改善の反復実験**。許可済み合成条件でGLB再生成と改善測定 | **partial / blender_ci** | CBDK自作モデルの適応探索までCI成功。第6段階の途中経過保存・失敗/打切りレビューを実装し、新しい対象CIを確認中。最大4試行、任意アドオン実行/自由最適化は未実装 | [タスク](https://app.notion.com/p/410948b74937811ea006d4d6bd55b1dc) |

## 今回の優先順

[現状分析・全体実装計画](DEVELOPMENT_PLAN.md)を参照。NEXT-021で既存GLB-019の部品一覧・弱い候補の証拠整合性を検証し、その後NEXT-019/020の失敗時診断・打切り・人手レビューを優先。GLB-020追加機能凍結、GLB-021/022 partial、直接インストール保留を維持。節目のNotion同期は[運用書](NOTION_SYNC.md)へ記録する。

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
- **次の優先課題は GLB-022の合成反復MVPを一般化する前の安全性・失敗時診断・人手レビュー強化**。GLB-020レビューMVPは総合受け入れ済みで高精度化は後日。。GLB-019の実ユーザーGLB実測が必要になれば先に安全確認する。

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

### GLB-020 MVP総合受け入れ・機能追加の一時停止

- **3部品の合成ボールジョイント風モデル**で、正常/ソケット開口狭窄/ボール位置ずれ/ソケットリップ2面欠損を検査。正常時の誤検出0、変更部品だけの差分、欠損時の境界0→4本、ソースGLBのSHA-256不変が合格条件。
- 最終テスト対象コード SHA `db33ce4242bbe98b3c5f9ac43d89bf21c3657089`：
[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898364)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898499)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898512)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898604)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898325)・[Chromium実GUI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898701) **全6系統成功**。
- 途中で「正常な軸に実際の開放端がある」ことが判明し、テスト用メッシュを正しく閉じて再検証。解析の判定閾値は緩めずに修正した。
- **GLB-020はレビューMVP合格・高精度化はバックログ**として、機能ステータスは`partial`を維持。今後は余計な追加改良を止め、次に**GLB-021：問題→アドオン設定の改善候補**、次いでGLB-022の許可済み合成実験を優先。GLB-021/022はまだ未実装、PR #25はドラフト・正式版はv0.17.0のまま。
- [GLB-020受け入れ基準と残課題](GLB020_MVP_ACCEPTANCE.md)

### GLB-021 第1段階：形状差分→AST設定候補の静的照合（レビュー専用）

- `glb-visual-property-review` CLIはGLB-020の匿名集計`review.json`から異常が観測された生成側の部品だけを対象に、利用者が指定したPythonソースの`bpy.props`宣言や構文上の使用箇所を**実行せず**に照合。設定名が完全一致しても「原因・修正量」は不明のまま。
- `--role part_003=socket`等は手動の未確認ヒントであり、役割の自動識別を主張しない。候補宣言と行番号はignored `reports/latest`ローカル限定。元のアドオンやGLBを変更しない。
- コードSHA `8c51a867415738dcca6616a4a197b62a105075e5`： [Python 42292708122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708122)、[Windows 42292708128](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708128)、[Blender 4.4.3/4.5.15/5.2.1 42292708248](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708248)、[Windows Kit 42292708114](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708114)、[引き継ぎ 42292708111](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708111)、[Chromium実GUI 42292708124](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708124) **全6系統success**。
- GLB-021は**partial / blender_ci**、GLB-022は未実装。GLB-020レビューMVP合格による細かな機能追加凍結は維持。[詳細](GLB021_VISUAL_PROPERTY_REVIEW.md)。

### GLB-021 第2段階：人間による判断のためのレビューシート

- `--markdown` オプションで、GLB-020で観測された部品別の誤差、ASTの宣言名一致/構文的な使用経路、未確認の因果関係を分けて、**日本語の確認リスト**として出力できる。原因・修正値・部品の正しい対応関係を自動承認しない。
- 候補名・宣言位置を含むMarkdownはローカル`reports/latest`の非公開データ。既存ファイルの上書きや追跡対象への書込みは拒否。公開GitHubやNotionには元アドオンに由来する識別子を載せない。
- 次はレビュー内容の品質と原因の実験的検証を段階的に評価。GLB-021は`partial`のまま、GLB-022は未実装。[GLB-021詳細](GLB021_VISUAL_PROPERTY_REVIEW.md)。

### GLB-021 第4段階：固定合成ソケットの原因と反証

- 合成モデルだけで直径0.78の狭窄→1.70への復帰による差分消失と、無関係なボール移動では未解消の事実をBlender3バージョンで検証。
- テストコードSHA `3b553039968e982e973d10d3427bf0607bbad88d`：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028446)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028346)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028811)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028286)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028673)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028338) **全6系統成功**。
- **実アドオンのプロパティが原因であるという推定は未成立**。GLB-021は一部実装、GLB-022は未実装。[検証プロトコル](GLB021_SYNTHETIC_INTERVENTION.md)。

### GLB-021 第5段階：合成実験の変更履歴と比較

- 3つの固定合成ケース（ソケット口を0.78に狭める、0.78のままボールを移動、元の1.70に戻して再生成）を、匿名部品の観測差分集計と安全フラグでJSON/日本語Markdownに記録。
- テスト対象コード SHA `ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f`：[Python 42299997255](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997255)、[Windows 42299997246](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997246)、[Blender4.4.3/4.5.15/5.2.1 42299997251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997251)、[Windows Kit 42299997311](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997311)、[引き継ぎ 42299997254](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997254)、[Chromium 42299997355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997355) **全6系統成功**。
- **合成モデル内の効果の差**を確認するものであり、元アドオン設定の実行時の依存性・正しい変更量は未確認。次は許可済み合成GLB-022への段階的な接続を検討するが、GLB-021 partial・GLB-022未実装を維持。[受け入れと残課題](GLB021_TRIAL_HISTORY.md)。

### GLB-022 第1段階：固定合成GLBの反復生成・比較・採否・停止

- CBDKの固定ソケットモデルだけで、初期の狭窄状態をBlenderで生成→差分測定→関係ないボール移動を**棄却**→既知正常値へ復帰して**採用**→観測異常面0で停止まで自動試行。候補は毎回実際にBlenderでGLB生成。最大2試行、実ユーザーモデルは投入しない。
- `cbdk/glb_synthetic_iteration.py`、`scripts/run_glb022_synthetic_iteration.py`を追加し、JSON＋日本語Markdownに匿名部品別の観測異常面数・採否・停止理由を記録。元GLB/合成ジェネレーターSHA-256不変と不正試験拒否をテスト。
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`：[Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)・[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)・[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)・[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)・[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)・[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- **GLB-022は一部実装（合成ループMVP）**。自由な値の探索、任意のアドオン実行・コード編集、正しい補正値の自動提案、完全な幾何一致は未達。GLB-020のMVP凍結は維持。[詳細](GLB022_SYNTHETIC_ITERATION.md)。

### GLB-022 第1段階：固定合成GLBの実再生成・採否・停止

- CBDK自作固定ジェネレーターだけを実行して、狭窄ソケットを初期条件に**試行1の無関係なボール移動を棄却、試行2の既知正常形状復帰を採用**。最大2試行、観測差分0で停止。履歴は匿名JSON/日本語Markdownで非公開保存。
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`： [Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)、[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)、[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)、[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)、[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)、[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- **GLB-022はpartial / blender_ci**。試行は実Blenderによる新規GLB生成だが、候補は厳密な固定2種で、任意の実ユーザーアドオン/GLBや一般的なパラメータ探索には未対応。GLB-021もpartial、GLB-020 MVP凍結、正式v0.17.0/ドラフトPR #25維持。[品質基準・制約](GLB022_ALLOWLISTED_ITERATION.md)。

### GLB-022 第2段階：固定3候補の合成反復と部品間の副作用判定

- CBDK合成のソケット・ボール・軸を実Blenderで毎回生成し、`narrow_placebo`（改善なし）と`shifted`（ボール悪化）を棄却、`identical`（観測差分0・他部品悪化なし）を採用。予算1/2での打切りは未修復として終了。旧2候補も回帰維持。
- コードSHA `d8d233e801b4da33f5f79cf6983818cefdca918c`：[Python 42305594556](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594556)、[Windows 42305594566](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594566)、[Blender 4.4.3/4.5.15/5.2.1 42305594589](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594589)、[Windows Kit 42305594635](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594635)、[引き継ぎ 42305594684](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594684)、[Chromium 42305594551](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594551) **全6系統成功**。
- **GLB-022 partial / blender_ci**のまま。合成固定3候補での観測のみで、連続的最適化、実ユーザーモデルの自動修復、真の部品同一性・幾何の完全一致は未実装。[実験仕様](GLB022_MULTI_CANDIDATE.md)。

### GLB-022 第3段階：合成中間改善と数値評価

- CBDK合成の固定0.78→1.24→1.70をBlenderで毎回生成。`narrow_mid_shifted`は他部品悪化で棄却、`narrow_mid`は観測最大サンプル距離が減るので**中間改善として採用**、`identical`で観測距離0・停止。旧2/3候補プロトコルの回帰も維持。
- テスト対象コードSHA `44e15f8f6664fe29e06810fd06d8d73dda70bec6`：[Python 42307811087](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811087)、[Windows 42307810687](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810687)、[Blender4.4.3/4.5.15/5.2.1 42307810797](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810797)、[Windows Kit 42307810828](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810828)、[Handoff 42307811040](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811040)、[Chromium 42307810743](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810743) **全6系統成功**。
- ただし全体双方向最大サンプル距離は厳密なHausdorff距離ではない。実ユーザーアドオンの任意設定値探索・部品ごとの連続誤差や完全幾何等価性は未保証。GLB-022 partial、正式v0.17.0/ドラフトPR #25維持。[段階的な検証仕様](GLB022_PROGRESSIVE_SYNTHETIC.md)。

### GLB-022 第4段階：算術生成した4候補の合成GLB比較

- 自作合成ソケットだけで0.78から既知正常1.70までの4分割格子を計算し、候補1.01/1.24/1.47/1.70をBlenderで実生成・GLB-020で比較。サンプル距離改善時のみ採用、停滞候補は棄却、予算不足時は未完了と記録、既知正常で観測0停止。
- テスト対象コード SHA `23e9dec5d313468a70cc3bab7a5bb57fc090a8b3`：[Python 42309145079](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145079)、[Windows 42309145003](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145003)、[Blender4.4.3/4.5.15/5.2.1 42309145076](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145076)、[Windows kit 42309145019](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145019)、[引き継ぎ 42309145005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145005)、[Chromium 42309145006](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145006) **全6系統success**。
- **GLB-022 partial / blender_ci**。固定範囲の格子生成で、実アドオンのパラメータを自由探索する機能や真の幾何等価性は未実装。旧3プロトコルの回帰維持。[受け入れ・安全制約](GLB022_GENERATED_GRID.md)。

### GLB-022 第5段階：測定で候補を変更する適応探索（合成限定）

- CBDK合成ソケット開口の0.78〜1.70を0.01刻みで二分。試験専用の全体双方向サンプル最大距離0.12以内かどうかで次候補が変わり、Blender3版の実生成・比較は1.24→1.47→1.35→1.41。1.47を測定上の目標内候補と記録し、最大4回で停止・最適値未確定と明記。
- テスト対象コードSHA `37ee124aabb44df5ad9cb246342712bd9e0eb2ef`：[Python 42311608904](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608904)、[Windows 42311608916](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608916)、[Blender4.4.3/4.5.15/5.2.1 42311608910](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608910)、[Windows Kit 42311609353](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609353)、[引き継ぎ 42311609070](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609070)、[Chromium 42311609211](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609211) **全6系統success**。
- **GLB-022 partial / blender_ci**。実アドオンの設定を変更して因果や最適値を見つけるものではなく、単調性の仮定を他形状へ一般化しない。古い4プロトコルの回帰維持。[仕様と制限](GLB022_ADAPTIVE_SYNTHETIC.md)。

## 今回の開発単位: NEXT-022 / GLB-022第6段階

工程チェックポイント、検証済みprefixの保存、固定失敗分類、日本語確認事項、非実行の読取CLIを一括実装。[仕様](GLB022_RUN_REVIEW.md)。対象CIと同期状態はSTATE/HANDOFFへ記録する。新しい探索条件やユーザーコード実行へは拡張しない。
