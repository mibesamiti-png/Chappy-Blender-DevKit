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

## 自動で確かめる範囲

- 新しい機能IDと部品IDの形式・重複、既存の部品IDの実在
- 新部品と機能が参照する予定のパスが既存ファイルと衝突しないこと
- `catalog/authored_parts.json` のID・ソースとコードの許可リストが一致すること
- `catalog/addon_features.json` とコード中の信頼済み機能台帳が一致すること
- レシピ、部品・機能のソース、テスト、CI、仕様・GitHub引き継ぎの更新作業一覧

## 自動化しない範囲（重要）

- 新しいPythonコードやBlender UIの自動生成・実行
- `TRUSTED_FEATURES` / `TRUSTED_PART_SOURCES` への自動追加
- `approved=true`、ライセンス許諾、第三者ソースの採用
- Blender Extensionsの公開・配布やGitHub→Blender自動インストール
- Python/Windows/Blenderの実機合格認定

レビューでコード・依存関係・権利を確認してから、別の開発変更として台帳を更新し、
`python -m cbdk.recipe_matrix`、全Pythonテスト、Blender/Windows CIを実行すること。
今後の新機能追加でも安定版の `main` を未検証のまま変更しない。

**検証状況（2026-11-05）：** v0.17ドラフトPR #20に実装と回帰テストを追加。
GitHub Actionsのランナー未割当問題（Issue #19）が継続し、最新版CIは未検証。
