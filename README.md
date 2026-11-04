# Chappy Blender DevKit (CBDK)

**ChatGPT / Codex向け Blenderアドオン開発資産ライブラリ・静的解析ツール**

開発段階: **v0.1 — Phase 1の基礎 + Phase 2の重複候補抽出（プロトタイプ）**。
AIが自作アドオンのPythonコードから再利用候補を抽出・検索し、重複を報告します。実コードを**実行せず**ASTで静的解析します。

## 最初に試す

Python 3.11+ の環境で、プロジェクト直下から実行：

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "選択 頂点"
python -m cbdk search "STL 出力"
python -m cbdk compare
python -m unittest discover -s tests -v
```

オリジナルのBlenderアドオンは `input_sources_private/` に配置します（配布版には、手持ちの8ファイルを同梱していますがGitで無視する設定です）。**公開GitHubに元ソースを勝手にアップロードしないでください。**

実行後の成果物:

- `reports/latest/catalog.json` — ファイルと関数・メソッド・クラスの静的台帳
- `reports/latest/duplicates.json` — AST一致 / 形状一致 / 類似候補
- `reports/latest/report.md` — 読みやすい分析レポート
- `reports/latest/metrics.json` — 件数と分類

## 現段階でできること

- Pythonファイル・ディレクトリ一括収集
- Python構文エラーの記録、`bl_info`解析、関数/クラス/メソッド/呼び出し関係の抽出
- 正規化AST一致、識別子や定数を無視した構造一致、簡易近似判定
- 日本語・英語の検索（辞書式）、JSON/Markdown出力
- 元ソースを実行しない読み取り専用解析
- 標準ライブラリのみで動作（Blender/Python外部ライブラリのインストールは不要）

## まだできないこと

- 自動で関数の意味を確定・統合すること
- 出典ライセンスを自動で判断すること
- 汎用部品を自動抽出して依存関係付きでパッケージ化すること
- Blenderを起動した実機テスト（Blender環境が必要）
- 新しいアドオンの自動組み立て、ZIPビルド
- GitHub上の新規リポジトリ作成と自動同期

**類似判定は候補提示のみ。挙動が同等とは限りません。** 同じ関数構造でもモジュール変数やクラスの文脈が異なることがあります。

## プライバシー / ライセンス

Git管理から `input_sources_private/` を除外しています。外部OSSはライセンス確認を行い、まずURL・バージョン・出典だけ管理します。サンプル実装 `parts/common/safe_path.py` は `blender_to_bambu_studio.py` のファイル名処理を参考に独立化したもので、現時点では未ライセンス確認のため第三者への再配布前に確認してください。

## ロードマップ

- v0.1: 静的解析 / 重複候補 / カタログ / テスト
- v0.2: 比較UI、手動採用、永続ID、ライセンス記録
- v0.3: 部品の依存関係解析とBlender内テスト
- v0.4: Codex用レシピ検索とアドオンビルダー

詳しくは `docs/PROGRESS.md` と `docs/SPEC.md` を参照。

## v0.2: 手動重複レビューと永続部品ID

v0.2は「同じ処理の候補を見つける」だけでなく、**候補の根拠を可視化し、人間が採用判断を記録する**機能を追加します。元コードは実行・変更しません。

```bash
# 1. 手持ちのアドオンを非公開ディレクトリで解析
python -m cbdk scan input_sources_private --output reports/latest
# 2. AST一致・形状一致・近似一致をレビュー用に一覧化
python -m cbdk triage --catalog reports/latest/catalog.json \
  --duplicates reports/latest/duplicates.json --output reports/latest/review_queue.json
# 3. 検証用の候補IDを検索
python -m cbdk search "法線 中心"
# 4. その候補に永続IDと出典・権利確認の記録を付ける（例のIDは置換）
python -m cbdk register --catalog reports/latest/catalog.json \
  --registry reports/latest/registry.json --candidate CND-REPLACE_ME \
  --part-id GEO-001 --name "法線計算" --purpose "面法線の取得" \
  --origin self_owned --license-id LicenseRef-Proprietary \
  --license-evidence "権利者が確認した記録" --reviewer "開発担当者"
# 5. 手動判定（自動承認ではない）
python -m cbdk decide --registry reports/latest/registry.json \
  --part-id GEO-001 --decision selected \
  --reviewer "開発担当者" --reason "動作要件を確認。実機検証は別途必要"
python -m cbdk parts --registry reports/latest/registry.json
```

`decide` は `selected / rejected / blocked / hold` の4段階。**selectedはBlenderで動作確認済み・配布承認済みを意味しません。** 権利情報はユーザーの申告・証跡を記録するだけで、システムが正当性を認定するものではありません。

`reports/latest/` と `input_sources_private/` はGitから除外しています。個人用レジストリを共有する場合は、元ソース名や出典の扱いを事前に見直してください。自動合体・承認・ZIPビルド・Blender実機テストは今後の段階です。

## v0.4 — 同一ファイル内の依存関係をまとめて切り出し

複数の関数が互いに呼び出し合う場合、依存するトップレベル関数と単純な不変リテラル定数を解析し、単一のレビュー用Pythonファイルにまとめられます。

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "球のクリアランス"
# CND-... と元ファイル名は検索結果に合わせて差し替える
python -m cbdk bundle --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/addon.py
python -m cbdk bundle --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/addon.py --output reports/latest/extracted/group.py
```

- `--output` を省略すると依存グラフとブロック理由のみ表示します。
- 生成される `.py` と同名の `.json` はレビュー用の**未承認候補**です。実機確認なしにアドオンに組み込まないでください。
- `max_functions=64`、深さ24、各関数最大5000 ASTノードで制限します。
- 循環参照・外部グローバル・デコレータ・動的デフォルト引数・属性操作・危険な関数呼び出し・組み込み関数名の上書き・実行時注釈式は拒否します。
- 元ソースのSHA-256を確認し、元ファイルも既存出力ファイルも上書きしません。
- 同一ソースファイル内だけを対象とします。`bpy` に依存する一般的なBlender関数や別ファイルのモジュール依存はまだ未対応です。
- **静的条件に合格しても、動作同等性・安全性・ライセンス・Blender互換性を保証しません。**

実データ例：Surface Stamp v2.5.2の `_point_in_triangle_strict_2d` と `_orient2d` は、元ソースを変更せず一組として抽出できました。

## v0.5 — Blender API監査とファイル間の依存関係

**原本を実行せず、ASTだけを解析する**方式を維持しながら、次の2つを追加しました。

### 1. Blender API使用状況の監査

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk audit-blender --catalog reports/latest/catalog.json --output reports/latest/blender_audit.json
```

`bpy`、`bmesh`、`mathutils` の参照と呼び出し、および `bpy.ops`、`bpy.context`、編集メッシュAPIなどの**実機検証が必要そうな箇所**を抽出します。`import bpy as blender` や `from bpy import ops` の静的な別名も検出します。

レポートは**参考情報**です。`context` を引数から渡すなどのパターンは推測を含み、動的ディスパッチ・インポートでは検出漏れがあります。API互換性・安全性・Blender実行成功を保証しません。

### 2. 複数ファイルにまたがる関数抽出（未承認のレビュー候補）

```bash
python -m cbdk crossfile --catalog reports/latest/catalog.json \
  --candidate CND-REPLACE_ME \
  --source input_sources_private/myaddon/main.py \
  --sources-root input_sources_private/myaddon
# 検査でブロッカーがない場合に限り、 --output reports/latest/review_bundle.py で出力
```

対象は**明示的な相対インポート**（例：`from .helpers import helper`）でつながる、同一の検索ルート内・スキャン済み・SHA-256一致のトップレベル関数のみです。関数名の衝突、循環参照、任意の属性操作、外部依存、変化したソース、動的処理は拒否します。ASTで認めた数値定数と`math`依存だけを展開できます。別名インポート・ワイルドカード・Blender固有APIは現時点で自動抽出しません。

出力物は新しい`.py`と同名の`.json`（出典、依存関係、元ソースのSHAなど）です。原本・既存の出力ファイルを上書きせず、採用を自動承認しません。生成物は必ず人がレビュー・テスト・権利確認を済ませてから利用してください。

テスト：

```bash
python -m unittest discover -s tests -v
```

**重要：** 合成したテストデータでは動作を確認していますが、Blender本体上での抽出結果の動作検証、複雑なアドオンの互換性・意味同等性の確認はまだ未実施です。
