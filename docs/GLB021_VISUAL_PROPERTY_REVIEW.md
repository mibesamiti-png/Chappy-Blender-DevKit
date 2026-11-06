# GLB-021 — 形状差分 → 静的AST設定候補のレビュー連携（開発中）

開発ブランチ: \`feature/v0.18-shape-diagnostics\`、ドラフトPR #25。正式版 \`v0.17.0\` は維持する。このドキュメントは**レビュー専用の試作**の仕様であり、設定値の自動調整・真の原因特定・ユーザーのアドオンの自動実行を実装したという意味ではない。

## 既存機能を再利用する

- GLB-020 の **\`review.json\`** は参照・生成GLBの匿名部品ごとの赤/黄/灰分類・境界エッジ集計・サンプル感度・曖昧な部品対応候補を記録する。元の生頂点・部品名・ファイルパスを含めない（\`compare_viewer.html\` は派生3D座標を含むためローカル限定）。
- 既存 \`cbdk/glb_property_map.py\` / \`glb_property_usage.py\` / \`glb_geometry_flow.py\` は、利用者が**明示したローカルPythonファイル**のみを \`ast.parse\` で読み、\`bpy.props\` の宣言、構文上の属性参照、構文上の形状処理への引数の流れを調べる。元ソースは**import/exec/compileしない**。出力にはソース本文・既定値・元のファイルパスを含めない。
- 今回の \`cbdk/glb_visual_property_review.py\` は上記2つを橋渡しし、匿名の変更箇所と**候補となる設定名・宣言行・未確認の構文証拠**を1つのレポートに結ぶ。

## 使い方（ローカルPC・明示的な指定が必要）

まず既存のGLB比較を実行：

\`\`\`bash
python -m cbdk glb-diff-visualize reference.glb candidate.glb \
  --blender /path/to/trusted/blender \
  --output reports/latest/my_joint_visual
\`\`\`

次にPythonソースを**実行せず**、AST照合：

\`\`\`bash
python -m cbdk glb-visual-property-review \
  reports/latest/my_joint_visual/review.json \
  --source /local/path/to/my_addon.py \
  --output reports/latest/my_joint_property_review.json
\`\`\`

任意で、人が確認した**生成側の匿名部品**の役割を指定：

\`\`\`bash
python -m cbdk glb-visual-property-review \
  reports/latest/my_joint_visual/review.json \
  --source /local/path/to/my_addon.py \
  --role part_003=socket \
  --output reports/latest/my_joint_property_review_socket.json
\`\`\`

\`--role\` は \`part_001=ball\`、\`part_002=shaft\`、\`part_003=socket\`、\`part_004=hinge\` のように**人が付けるヒント**。オブジェクトの本当の役割や参照GLBとの対応をAIが確認したわけではない。役割を指定しなければ\`profile_shape\`、\`boolean_cutter\`、\`opening_or_cut_depth\`、\`object_scale\`等の**一般的な候補名のみ**を探し、ソケットだと推測したことにはしない。

各実行の出力先は未追跡の \`reports/latest/*.json\` 以下の**新規ファイル**に限定。既存ファイルの上書き、絶対パスへの出力、追跡対象ディレクトリへの出力は拒否する。CLI標準出力には候補の個別プロパティ名・私有ソース名・パス・値を表示しない。ローカルのJSONは候補プロパティや行情報を含む可能性があるため、ユーザーのプライベートデータとして扱い、GitHub・Notionにアップロードしない。

## 判定の条件と出力例の意味

1. **候補の作成**：生成側の匿名部品で\`medium/high\`の面が見つかる、または開放境界が観測される場合にだけレビュー対象として列挙する。完全に無変更の合成基準では候補0件。GLB-020はサンプリング方式のため、現実の差分を100%検出する保証はない。
2. **部品の対応**：GLB-020が一意の\`suggested\`とした場合だけ参照側の匿名IDを**仮の紐付け**として併記する。\`ambiguous\`/\`unmatched\`の場合は参照側のIDを付けない。どの場合も \`cross_file_part_identity_proven=false\`。
3. **設定名の候補**：静的宣言の名前が予めレビュー可能な候補ファミリの識別子と**完全一致**した場合のみ\`exact_declaration_name_only\`を記録する。宣言されていない設定名を「実在する設定」と呼ばない。類似表記・派生プロパティ・動的登録は一致の証拠にできない。
4. **使用箇所の情報**：既存のAST参照・形状フロー解析の結果があっても、「実際に登録済み」「実行時に形状へ影響する」「この差の原因」「修正すべき数値」とは断定しない。
5. **適用操作はゼロ**：\`applies_parameters=false\`、\`source_executed=false\`、\`cause_and_effect_proven=false\`、\`recommended_parameter_value=null\`。Blenderやユーザーアドオンを起動せず、元GLBやソースコードを変更しない。原因と設定値の決定はレビュー後の別工程。

## 合成テスト

\`tests/fixtures/glb021_synthetic_settings.py\` はCBDKだけが作ったテスト用ソース。実行しなくてもAST解析できることを確認する。 \`tests/test_glb_visual_property_review.py\` では、正常0件、ソケット狭窄、ボール移動、リップ面欠損、悪意のある安全フラグ・不正JSON・役割の偽装をテスト。

Blender 4.4.3/4.5.15/5.2.1の既存\`joint_mvp\`工程後に、\`scripts/verify_glb021_joint_review.py\`で実際に生成された4組のGLB-020集計JSONを入力として利用する。合成ASTのプロパティ名と一致したときだけ候補が列挙されること、正常0件、設定値や因果関係を勝手に確定しないこと、元ソース・元レポートが不変であることを確認する。テスト結果は**実際のGitHub Actions runとコードSHAが成功してから記録**する。

**残課題**：本当の部品の種類の自動特定、参考GLBとの確実な対応、AST外の動的設定、メッシュ生成処理への実際の依存性検証、ユーザー自身の非公開アドオンでの検証、正しい変更量や改善を自動決定する工程。後者の実験はGLB-022で許可済み合成環境に限定する。

## 第1段階・実測CI結果（2026-11-07）

コードSHA `8c51a867415738dcca6616a4a197b62a105075e5`： [Python 42292708122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708122)、[Windows 42292708128](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708128)、[Blender 4.4.3/4.5.15/5.2.1 42292708248](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708248)、[Windows Kit 42292708114](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708114)、[引き継ぎ 42292708111](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708111)、[Chromium実GUI 42292708124](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708124) **全6系統success**。

合成の3部品・正常/ソケット狭窄/ボール移動/リップ面欠損について、Blender実GLB比較→匿名集計JSON→静的AST宣言の照合まで実行。正常時の候補0、差分がある部品で明示的な手動役割に基づく設定名候補、欠損では未確認の対応部品を確定しないことを確認。Python単体テストで不正安全フラグ/重複JSON/元ソース実行禁止/非公開情報の標準出力非表示/ローカルのみ新規書込を確認。

**GLB-021全体は一部実装**。このCIはCBDK自作合成モデルと合成アドオン宣言のみで、ユーザーの任意アドオンの実行時の性質、正しい設定値、完全な原因特定は保証しない。正式v0.17.0は変更せず、v0.18はドラフトPR #25を維持。

## 第2段階：レビュー担当者向けの非公開Markdown（オプション）

GLB-021の設定候補JSONに加えて、差分を**人が読んで判断するためのチェックシート**を出力できる。形状の赤/黄の観測面数・境界辺の観測数・ASTの設定名一致・静的な参照件数・形状処理経路件数を整理し、未確認の因果関係と確認手順を明記する。

既存のCLIにオプションを追加：

```bash
python -m cbdk glb-visual-property-review \
  reports/latest/my_joint_visual/review.json \
  --source /local/path/to/my_addon.py \
  --role part_003=socket \
  --output reports/latest/my_joint_property_review.json \
  --markdown
```

上記の場合、レビュー用の**ローカルのみ**のファイルが2つ作られる。

- `reports/latest/my_joint_property_review.json`：従来の集計とASTの構造化候補
- `reports/latest/my_joint_property_review.md`：日本語の人間向けレビュー文書（**非公開**）

Markdownには候補プロパティ名、匿名部品ID、元ファイルの**匿名化ラベルと宣言クラス/行番号**が含まれるため、ユーザーのローカルにのみ保持する。元のPythonソース全文、実際のファイルパス、設定のデフォルト値、3D頂点データをMarkdownへコピーしない。CLI標準出力にもこれらを表示しない。どちらも`reports/latest/`の未追跡領域のみ・新規作成限定・既存ファイルは上書き拒否。Markdownの保存先が既にある場合は、JSONの書込み前に拒否する。

レビュー項目では次を区別する：

1. **観測事実**：黄/赤の三角面数・境界辺数。正常側に色差が検出されなくても完全一致の証明ではない。
2. **AST宣言の一致**：あるプロパティ名がソース内で宣言されていることのみ。
3. **構文上の使用・形状処理の候補**：参照箇所・構文上の伝播を検出しても、本当にその値がメッシュを変えるとは断定しない。
4. **人の確認欄**：部品対応・設定の登録・他の原因・許可済み合成モデルでの比較実験。原本の自動修正なし。

`render_review_markdown`が受け付けるのは安全フラグと匿名部品情報が正しい未承認のGLB-021結果のみ。勝手に「修正値」や「因果関係が確認された」という不正なフラグを含むデータは表示自体を拒否する。

合成Blender GLBの4ケースについて、JSONとMarkdownの対応、正常時0件、異常時の候補名、誤った公開パス、ソース情報の漏出、既存ファイル衝突をCIで検証する。**実際の完了状況・成功SHA・run IDはCI結果が確認できた場合だけ記載**する。


## 第3段階：確認順を明示したレビューシート

ローカル専用の日本語Markdownチェックシートは候補を**確認のしやすさ**で並べる：

1. ASTで形状処理APIへの構文上の経路が観測された候補。
2. ASTで属性参照が観測された候補。
3. `bpy.props`宣言名のみ一致する候補。

これは**「原因らしさ」「成功率」「修正すべき優先度」のランキングではない**。構文上の経路があっても実際に実行・登録・形状変更されているかは不明。順序を変えても、個別の候補名・AST宣言・行番号・人手チェック項目は保持し、正しい設定値を自動推測しない。未変更の部品は引き続き候補0件。

コードは `cbdk/glb_visual_review_markdown.py`、回帰テストは `tests/test_glb_visual_property_review.py`。ユーザーの私有ソースやレポートをGitHubへコミットせず、出力は `reports/latest/*.md` に新規作成するローカル文書のみ。CI結果はテスト対象SHAとRun IDを分けて記録する。

### 第2・3段階のCI結果：日本語レビューシートと確認順（2026-11-07）

コードSHA `af8e873a613b6b3075448db11f8f26c860dba2a4`：[Python 42296654049](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654049)、[Windows 42296653825](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653825)、[Blender 4.4.3/4.5.15/5.2.1 42296654171](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654171)、[Windows Kit 42296653959](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653959)、[引き継ぎ 42296653876](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653876)、[Chromium 42296653807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653807) **全6系統成功**。

`--markdown`で作る非公開チェックシートでは、形状処理への構文上の経路あり→属性参照あり→宣言名のみの順に設定候補を並べる。これは**人が確認しやすい順序**であり、原因の確率・修正の効果・設定値の正しさを意味しない。正常な合成GLBでは候補0件。Python回帰テストで順序・注意書き・私有パス遮断を確認し、Blender3版CIでは合成GLB→AST照合→Markdown生成を検証。実ユーザーの私有ソース、GLB、実際の因果関係は未検証。

## 第4段階：固定値の合成モデルでの変更・無関係対照実験

ASTで候補宣言を見つけただけでは、実際に形状へ作用する証拠にはならない。そのため、ユーザーのアドオンではなくCBDK内部の固定パラメータだけを用いて、ソケット口を意図的に縮小→再び元値に復帰してGLB差分を測定する実験を追加。関係ないボール移動だけの対照ケースでも、ソケットの誤差は残る必要がある。

テストコードSHA `3b553039968e982e973d10d3427bf0607bbad88d`：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028446)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028346)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028811)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028286)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028673)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028338) **全6系統成功**。

**合成ジェネレーターで設定と形状の因果が確認できても、実アドオンでの登録や実行時の効果は未確認**。正しい修正値の自動提案・GLB-022の一般的な反復実験・ユーザー私有ソースの実行は引き続き行わない。詳細：[GLB-021合成設定実験](GLB021_SYNTHETIC_INTERVENTION.md)。
