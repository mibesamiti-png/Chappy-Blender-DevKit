# CBDK v0.18 — GLB診断 × Blenderプロパティの静的照合

## 目的

GLBから判定した「Ball直径」「Socket開口」などの**設定候補群**と、利用者のローカルBlenderアドオンの `bpy.props` 宣言を照合し、実際に**ソース内に名前が存在した**候補だけを別扱いにする。

これは**レビューの手がかり**であり、Blender上に正式登録されたこと、モデルを変更すること、最適な値であること、ユーザーが使っているアドオンの同等性を証明しない。

## 使い方

事前にCBDKの `glb-regression`（または `glb-compare` → `glb-repair-plan`）で `repair_plan.json` を作成する。元アドオンは手動でローカルに保存し、**GitHubへアップロードしない**。

```bash
python -m cbdk glb-map-properties \
  reports/latest/glb_regression/repair_plan.json \
  --source input_sources_private/my_addon.py \
  --output reports/latest/glb_property_mapping.json
```

複数のPythonファイルを調べる場合は `--source` を最大16回指定できる。ディレクトリ丸ごとの自動探索は行わない。

**保存先は `reports/latest/` の新規JSONのみ**（Gitの追跡対象外）。既存出力の上書きやシンボリックリンク経由の外部出力を禁止している。再実行には別の出力ファイル名を指定する。

## 静的解析の範囲

- ファイルを読み取って標準ライブラリの `ast.parse` で構文解析する。元アドオンを`import`、`exec`、`eval`、Blender起動などで**実行しない**。
- ファイルのトップレベルクラスに宣言された `FloatProperty`、`IntProperty`、`EnumProperty` などの `bpy.props` プロパティを調べる。
- `from bpy.props import FloatProperty` や `import bpy as blender` などの明示的なimport/別名のみ扱う。
- 変数名が候補IDと**完全一致**すると `exact_declaration_name_only` として記録する。似ているだけの文字列を実在プロパティとみなさない。
- 各候補にソースの匿名ラベル（例 `source_1.py`）、クラス名、行番号、宣言種類を残す。ただし登録有無と実際の形状への影響は `not_checked` のまま。
- デフォルト値、Pythonソース本文、絶対パス、ローカルファイル名、その他の値の複製は行わない。

単一ソースの上限は1MiBで、ファイル数は16まで。途中でシンタックスエラー、台帳の不一致、危険な承認フラグなどを確認したら失敗扱いにする。

## 生成JSONの意味

`cbdk_glb_property_mapping` の `recommendations[]` に以下を分けて記録。

- `exact_name_matches`：静的AST上、同じ識別子を持つプロパティ宣言が存在した候補
- `unmatched_parameter_families`：提示した候補名と一致する宣言が見つからなかったもの
- `validated_geometry_effect: false`：**一致しても**形状への影響はまだ未確認
- `safety`：原本非実行・非改変・未承認・非マージ・非公開の状態

プロパティ名が異なる、動的に登録される、別ファイルにある、複雑な内部変換で利用される、といったケースは検出できない。その場合も名前がないことを不具合とは断定しない。

## これから先

今回の照合は第一段階（GLB-007/NEXT-009）。次は、人手で承認したプロパティと機能・実際の編集結果を結びつけて、**出典と検証を残したうえで**提案の品質を上げる。

未知のアドオンを自動実行しない。私有コードやGLBをGitHubにコミットしない。設定値の自動適用・自動修正は行わない。

## v0.18 追加：プロパティが参照される場所の静的追跡（GLB-008）

`glb-map-properties` で名前が完全一致した宣言には、`possible_code_references` を追加している。

- `possible_reference_count`: その識別子と同名の `object.property` アクセスをASTで見つけた数
- `access_counts`: `read`（読み取り）、`write`（単純な代入）、`read_write`（`+=`など）、`delete`（`del`）
- `examples`: 匿名の `source_1.py`、クラス・関数名、行番号、アクセス種別、受け手が `self` かその他かの粗い分類を最大16件
- `examples_truncated`: 16件を超えた場合はtrue。合計件数は保持し、1ファイル4096参照を超えると安全上の理由で拒否する
- `receiver_binding_verified: false` / `runtime_effect_verified: false`: どちらも実証していない

`context.scene.ball_diameter` と `self.ball_diameter`、`another_object.ball_diameter` は同じ文字列でも**別物かもしれない**。単純な属性名一致だけでは、その宣言に結びつくとは判断できない。動的 `getattr`、辞書経由、外部モジュール、実行時生成の属性も確実には追えない。

ソースを実行せず `ast.parse` のみで調べる。関数名・クラス名は私有ソース由来の情報なので、**レポートは引き続きGit無視対象 `reports/latest/` にのみ保存**し公開しない。コード本文、値、元ファイル名、絶対パスは含めない。実際の形状への影響や設定値の自動変更はしていない。

## v0.18 追加：宣言クラス自身からの参照と別オブジェクト参照の区別（GLB-009）

`glb-map-properties` の `exact_name_matches[].same_class_reference_review` に、静的な関連度の手がかりを追加。

- `possible_same_source_class_self_count`：宣言されたプロパティと**匿名ソースラベル・クラス名**が同じ範囲で `self.<property>` を参照した箇所の件数
- `possible_access_counts`：上記のうち、`read` / `write` / `read_write` / `delete` の分類別件数
- `other_or_unresolved_attribute_reference_count`：他クラス/別ファイル/別オブジェクトなどにある、同名属性への参照件数
- `classification`：同じクラスの `self` 参照構文があるかどうかの**未確認な仮説**
- `actual_receiver_binding_verified: false`、`registered_in_blender_verified: false`、`geometry_effect_verified: false`：いずれも未検証

同一クラス・同じ `self` という表記でも、実際のインスタンスがそのプロパティに結び付くとは限らない。参照例の保存は従来どおり最大16件だが、分類別の合計は保存例に関係なく**全件で集計**する。長すぎるクラス名の匿名化による誤一致は安全側で除外する。

これにより、明らかに別オブジェクトの参照を優先候補に昇格させず、人が調べる箇所を絞る。コード本文・既定値・秘密ファイルのパスは引き続き出力しない。Blender実機でプロパティを使ったこと、ジオメトリを変更したこと、適切な修正値が判明したことは意味しない。
