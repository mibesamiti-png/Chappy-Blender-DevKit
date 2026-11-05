# CBDK Registration Draft（開発用・レビュー前）

CBDKの新しい**自作機能・共通部品**を登録する前に、更新箇所をチェックリスト化する機能です。
既存の許可リスト、部品台帳、機能台帳を静的に確認します。元のアドオンは実行しません。

## 使い方

既存部品だけを再利用する例（結果を画面にJSON表示）：

```bash
python -m cbdk registration-draft \
  --feature-id inspect_selection_alt \
  --requires-part BLCTX-001 \
  --requires-part BME-001
```

新規共通部品を提案する例（**実際には登録しない**）：

```bash
python -m cbdk registration-draft \
  --feature-id align_vertices \
  --requires-part BLCTX-001 \
  --requires-part BME-004 \
  --new-part-id BME-004 \
  --new-part-module edit_align \
  --output reports/latest/registration_draft.json
```

生成されるJSONは `status=proposal_only`、`approved=false`、
`runtime_verified=false`、`source_executed=false`、
`catalog_modified=false` と明記します。
ファイルへの保存は **reports/latest/ 以下への明示指定時だけ**、既存ファイルは上書きしません。

## 登録計画からテストのひな形を生成（v0.17 ドラフト）

上の `registration-draft` コマンドで `--output` を指定した場合、次のコマンドでレビュー用Pythonテストひな形を作れます。

```bash
python -m cbdk registration-tests --draft reports/latest/registration_draft.json
```

出力先は `reports/latest/scaffolds/test_<機能ID>_review.py` に固定され、**既存ファイルを上書きしません**。Gitで無視されるローカル領域にのみ出力し、CBDK本体の`tests/`、許可リスト、カタログは変更しません。

生成されるPythonには、次の5件の未完成テストを設けています。

1. 自作ソース・依存部品・権利の人手確認
2. BlenderのObject/Editモードと選択状態の仕様
3. 期待する正常動作
4. 異常入力時にメッシュや選択が破壊されないこと
5. 変更操作の場合のUndo/Redo、複数Blender版の実機テスト

**全項目は初期状態では `self.fail("TODO: ...")` として失敗します。**
実装・レビュー・本物のテスト追加が終わるまで、完成・合格扱いにはしません。生成ファイルを勝手に実行する処理もありません。

読み込み時は登録計画を現行許可リストから再計算し、JSONの重複・変更・有効期限切れに相当する台帳の不一致・危険なパスを拒否します。失敗した場合は登録計画を再生成してね。

## 自動で確かめる範囲

- 新しい機能IDと部品IDの形式・重複、既存の部品IDの実在
- 新部品と機能が参照する予定のパスが既存ファイルと衝突しないこと
- `catalog/authored_parts.json` のID・ソースとコードの許可リストが一致すること
- `catalog/addon_features.json` とコード中の信頼済み機能台帳が一致すること
- レシピ、部品・機能のソース、テスト、CI、仕様・GitHub引き継ぎの更新作業一覧

## 自動化しない範囲（重要）

- 新しい**機能実装用**PythonコードやBlender UIの自動生成・実行（未完成のテストひな形のみ生成可）
- `TRUSTED_FEATURES` / `TRUSTED_PART_SOURCES` への自動追加
- `approved=true`、ライセンス許諾、第三者ソースの採用
- Blender Extensionsの公開・配布やGitHub→Blender自動インストール
- Python/Windows/Blenderの実機合格認定

レビューでコード・依存関係・権利を確認してから、別の開発変更として台帳を更新し、
`python -m cbdk.recipe_matrix`、全Pythonテスト、Blender/Windows CIを実行すること。
今後の新機能追加でも安定版の `main` を未検証のまま変更しない。

**検証状況（2026-11-05）：** v0.17ドラフトPR #20に実装と回帰テストを追加。
GitHub Actionsのランナー未割当問題（Issue #19）が継続し、最新版CIは未検証。
