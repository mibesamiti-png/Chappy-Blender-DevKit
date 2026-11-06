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
