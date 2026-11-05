# CBDK v0.10 — サンプルアドオン自動組み立て

## 目的と現在の範囲

既存のCBDK自作ヘルパー3件（BLCTX-001/002・BME-001）を、安全な固定レシピに従ってZIPにまとめ、**自分のPCでのみ試す開発プレビュー用のBlenderアドオン**を作る。

作成するのは `CBDK Mesh Inspector Preview`（3D View > Sidebar > CBDK）。Object Modeで選択メッシュ数、Edit Mesh Modeで選択頂点・辺・面の数を表示する。元の選択状態、モード、トポロジーには手を加えない。ただし画面に最後の検査文字列を表示するため、シーン内の一時的な文字列プロパティだけは更新する。

## 生成する

リポジトリルートからPython 3.11〜3.13で実行。

```bash
python -m cbdk build-addon \
  --recipe recipes/mesh_inspector.json \
  --preview-unapproved \
  --output dist/CBDK_Mesh_Inspector_Preview.zip
```

- `--preview-unapproved` を**明示しない限り生成を拒否**。現在のCBDK部品は `approved=false` / `license_review=pending` であり、配布許可・正式採用の根拠がない。
- 実行スクリプトや外部アドオンを引数で受け付けない。許可済み部品ID・許可済みソースと固定テンプレートのみパッケージ化。
- ZIPには `cbdk_mesh_inspector_preview/` フォルダが1つ入り、`__init__.py`、`helpers/context.py`、`helpers/edit_mesh.py`、出典ハッシュ入り `CBDK_BUILD_INFO.json` などを含む。
- 同じ名前のファイルは上書きしないので、新版を生成するときは保存先の名前を変更するか以前の出力を手動で管理する。
- **Blender Extensions（新しい形式）ではなく、レガシー形式の開発プレビュー**。正式な配布用Extensionはライセンス・部品採用の確認後に別途実装する。

## 自分のBlenderで利用

Blender 4.4.3以降で、編集 > プリファレンス > アドオンから「ディスクからインストール」／「Install Legacy Add-on」を選び、上記ZIPを選択して有効化する。3DビューのNパネル（サイドバー）に「CBDK」タブが出る。選択メッシュ数または編集メッシュの選択V/E/Fを確認できる。

既存の公開アドオンや日常使用の .blend はこのサンプルでは変更しない。ただし開発プレビューなので、大切な作業シーンでいきなりテストするのは避ける。

## クラウド自動検査

`.github/workflows/blender-smoke.yml` は公式Blender 4.4.3、4.5.15、5.2.1をSHA-256で確認し、プレビューZIPを生成した後、`scripts/blender_generated_addon_smoke.py` で一時フォルダからロードする。

検査内容：
1. ZIPの構造とプレビュー用メタ情報
2. アドオンの有効化とPanelの登録
3. Object Modeでメッシュ1個の数え上げ（ライトは無視）
4. Edit Modeで三角メッシュの選択V=3/E=3/F=1、モードが変化しないこと
5. アクティブメッシュなしの拒否
6. アドオン無効化後のPanel/Sceneプロパティ消去

テストは仮想のBlenderユーザー環境で動き、本人のPCのUIを自動操作するものではない。ZIPを手動でインストールした場合の見た目、他アドオンとの競合、性能は別途確認が必要。

## 安全上の境界

元の外部アドオンはコピー・実行しない。既存の `catalog/authored_parts.json` の正式採用状態も変更しない。出力される開発用ZIPは、正式公開・一般配布に用いない。


## v0.11: v2モジュラーレシピ

`recipes/modular_objects.json`、`recipes/modular_edit.json`、`recipes/modular_combined.json` の3例を追加。

| 機能ID | 必要なCBDK部品ID | 同梱される機能 |
|---|---|---|
| `object_selection` | `BLCTX-001`, `BLCTX-002` | Object Modeで選択メッシュ数の確認 |
| `edit_selection` | `BLCTX-001`, `BME-001` | Edit Modeで選択V/E/Fの確認 |

レシピ例：

```json
{
  "schema_version": 2,
  "template": "modular_preview",
  "package_id": "cbdk_modular_preview",
  "display_name": "CBDK Combined Inspector Preview",
  "features": ["object_selection", "edit_selection"],
  "purpose": "local_development_preview"
}
```

生成は従来の `python -m cbdk build-addon --recipe ... --preview-unapproved --output ...` を使います。

依存部品を**機能IDから自動算出**し、不要なモジュールは同梱しません。ソースハッシュと依存した部品IDを `CBDK_BUILD_INFO.json` に記録。実行可能なPython文字列、ファイルパス、ユーザーソースの指定は禁止で、レシピは厳密に検証されます。ZIPは同一入力ならバイト列が一定で既存ファイルを上書きしません。

3レシピとも**同じ `cbdk_modular_preview` パッケージを別構成で生成**するため、同時にBlenderへインストールしないでください。旧v1の `cbdk_mesh_inspector_preview` は引き続き生成できます。

GitHub Actionsでは、Blender 4.4.3、4.5.15、5.2.1ごとに3構成を実際に有効化・操作・無効化して検査します。この検査はヘッドレスであり画面の視覚的品質評価を含みません。


## v0.12 — 機能カタログと静的な構成プラン

`catalog/addon_features.json` は、自作機能の `id` / `source` / `required_parts` / `requires_features` / `min_blender` / `max_blender` を管理。実装ファイル・部品対応は `cbdk/feature_catalog.py` 側の許可リストにも固定し、カタログのJSONだけを書き換えて未知のコードを導入することはできません。

```bash
python -m cbdk feature-list --output reports/latest/features.json
python -m cbdk addon-plan --recipe recipes/modular_combined.json \
    --target-blender 4.4.3 --output reports/latest/addon_plan.json
```

計画の結果には、要求した機能 `requested_features`、依存関係を満たす順に並べた `ordered_features`、自動追加した依存機能 `dependency_features_added`、必要部品 `part_ids`、必要ソース `part_sources`、Blenderバージョン範囲などが含まれます。循環・未知の依存・コード側と違う部品ID・互換性違反は、生成前にエラーで止めます。

`build-addon` の `--target-blender` は任意指定。指定した場合、v1/v2両方のプレビューで4.4.0以降のサポート範囲を確認します。**指定しない場合はBlenderバージョンを推測しません**。GitHub Actionsは4.4.3・4.5.15・5.2.1を指定して、機能構成計画と実生成を確認します。CLIプランの `runtime_verified=false` はあくまで静的チェックを意味します。

現段階のカタログは2機能だけ。将来の機能追加ではPython側の許可リスト・機能実装・依存テスト・Blender実機テストも追加していきます。外部の自作アドオン原本は無条件でインポート/実行しません。


## v0.13 — 新しい共通部品を追加

`BLGEO-001 / mesh_world_bounds`：Object Modeのアクティブメッシュのローカルバウンディングボックスを `matrix_world` で変換し、ワールド軸に沿った最小・最大座標、寸法、頂点数を独立した読み取り専用レコードで返す。スケール/回転/移動を考慮する。**未適用モディファイアは計算に含まない**。Edit ModeはBMeshとの同期不整合を避けて拒否、空メッシュと非有限値は拒否する。

`BLMOD-001 / modifier_snapshot`：Object Modeのアクティブメッシュのモディファイア名・種類・viewport/renderフラグを、変更可能なBlenderオブジェクトへの参照を保持しないタプルとして返す。値を変更せず適用もしない。

機能レシピ：
- `recipes/modular_geometry.json` — `mesh_bounds` と `modifier_summary`
- `recipes/modular_all.json` — 従来の `object_selection` / `edit_selection` も加えた計4機能

```bash
python -m cbdk build-addon --recipe recipes/modular_geometry.json \
  --target-blender 4.4.3 --preview-unapproved \
  --output dist/CBDK_Geometry_Preview.zip
```

既存の旧レシピから生成するアドオンは引き続き動作する。新しい部品を追加するときは、`catalog/authored_parts.json`・`catalog/addon_features.json`とコード側の許可リスト・実際のBlenderテストを更新する。サンプルZIPは開発プレビュー専用で、複数構成を同時インストールしないこと。


## v0.14 — 選択頂点の局所的な移動

`BME-002: translate_selected_vertices(context, offset)` は、Blender Edit Modeで単一の独立したメッシュの選択頂点をローカル座標で移動する共通部品です。

- **実行前チェック**：`EDIT_MESH`、1メッシュだけ編集中、共有されていないメッシュ、リンクライブラリなし、シェイプキーなし、頂点選択あり、3成分の有限なオフセット（各軸±10単位、ゼロ移動は禁止）、既存/計算後の座標が有限かつ安全な範囲内。
- **成功時**：選択頂点の座標のみ変更。頂点/辺/面の数、選択状態、オブジェクト変換、モディファイアはそのまま。
- **失敗時**：全頂点を事前検証するので入力不備による部分更新を避ける。書込み・`bmesh.update_edit_mesh`中の例外では元座標へのロールバックを試みる。復元不能なエラーも隠さない。電源断やBlender内部の致命的エラーまで原子性を保証するものではない。
- **Undo**：共通部品を直接Pythonから呼ぶだけではUndoステップが作成されないため、アドオンのOperator `cbdk.modular_vertex_nudge` に `bl_options={'REGISTER','UNDO'}` を設定した。GUIでのUndo動作は必要になったときに別途確認。
- **実機テスト**：デフォルト未選択頂点が変化しないこと、Edit Mode維持、BMeshトポロジー不変、ゼロ/NaN等の入力拒否を検査。レシピ `modular_nudge` と `modular_all` の両方でテスト。

```bash
python -m cbdk addon-plan --recipe recipes/modular_nudge.json --target-blender 4.4.3
python -m cbdk build-addon --recipe recipes/modular_nudge.json --target-blender 4.4.3 --preview-unapproved --output dist/CBDK_Vertex_Nudge_Preview.zip
```

個人用の開発プレビューのみ。元の外部アドオンは取り込まず、カタログ承認やライセンス確認を自動変更しません。


## v0.15 — 差分検証・復元ガード

新規部品 `BME-003` は `capture_edit_snapshot`、`audit_vertex_translation`、`restore_edit_snapshot` を提供。PythonだけでBMesh型への依存なしに差分を比較できるよう、内部記録を不変データ構造にしています。

`BME-002` の編集は **スナップショット → 全入力の事前検証 → 頂点移動 → Blenderへ更新 → 差分監査** の順に進みます。無関係な頂点やトポロジーの変更、予定と違う座標差がある場合は復元を試み、成功と宣言しません。

メッシュの頂点＋辺＋面が20万を超える場合はメモリ使用量を抑えるため事前に拒否します。これは暫定的な開発用の上限であり、BMeshのすべての内部データを永続的に保存するものではありません。UndoはBlenderの `REGISTER/UNDO` Operatorに委ねます。GUIでのCtrl+ZそのものはヘッドレスCIでは保証しません。
