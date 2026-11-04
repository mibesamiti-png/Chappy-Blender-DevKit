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


## v0.2: 重複レビューと永続ID（手動）

新しいコマンド `triage` は、AST一致・構造一致・近似候補をレビュー用に可視化します。ソースコードの実行・自動合体は行いません。

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk triage --catalog reports/latest/catalog.json --duplicates reports/latest/duplicates.json --output reports/latest/review_queue.json
python -m cbdk search "法線 中心"
# CND-... は検索結果から取得して置き換えてください
python -m cbdk register --catalog reports/latest/catalog.json --registry reports/latest/registry.json --candidate CND-REPLACE_ME --part-id GEO-001 --name "法線計算" --purpose "面法線の取得" --origin self_owned --license-id LicenseRef-Proprietary --license-evidence "権利者の確認記録" --reviewer "開発担当者"
python -m cbdk decide --registry reports/latest/registry.json --part-id GEO-001 --decision selected --reviewer "開発担当者" --reason "採用候補としてレビュー済み。実機検証は別途必要"
python -m cbdk parts --registry reports/latest/registry.json
```

判定は `selected / rejected / blocked / hold` の4種類。**selectedは実機動作確認済み、ライセンス適合性確認済み、再配布承認済みを意味しません。** 権利情報はレビュー担当者の申告・証跡を記録するだけです。実際のライセンス適合・Blenderテストは別工程となります。

`reports/latest/` と `input_sources_private/` はGit管理から除外済みです。レビューキューに含まれる元ファイル名などの情報は不用意に公開しないでください。


## v0.3 — 静的依存チェック・候補関数の切り出し

元のアドオンを実行せず、単独化できそうなトップレベル関数を解析します。グローバル変数・非許可関数呼び出し・属性アクセス・複雑な代入・デコレータなどの候補は保留します。

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "補間"
# 次の候補IDと原本ファイル名は検索結果から指定してください
python -m cbdk isolate --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/example.py
python -m cbdk isolate --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/example.py --output reports/latest/extracted/helper.py
```

output未指定では検査のみ。指定すると新しいPython関数ファイルと出典JSONを生成し、既存のファイルは上書きしません。これはあくまで未承認のレビュー候補であり、権利・動作・Blender互換性を証明しません。

Blenderインストール済みのPCでは、基礎的なBlender API動作を次のコマンドで任意に検証できます。第三者アドオンや抽出したコードは実行しません。

```bash
python -m cbdk.blender_test blender
# Windowsでは blender を blender.exe のフルパスに置き換えてください
```

レポートは reports/latest/blender_smoke.json へ保存。これは抽出した関数の検証ではなく、Blender環境のスモークテストです。



## v0.4 — Dependency bundles

同じソース内で関数同士が依存している場合、呼び出し元のCND-IDを指定すると依存関係を静的に解析し、必要な関数と定数をまとめてレビュー用ファイルとして出力します。

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk search "法線"
# CND-IDと元ファイルは実際の検索結果に置き換えてください
python -m cbdk bundle --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/example.py
python -m cbdk bundle --catalog reports/latest/catalog.json --candidate CND-EXAMPLE --source input_sources_private/example.py --output reports/latest/extracted/group.py
```

出力なしなら診断だけ。出力ありなら新しいPythonファイルと出典JSONを生成します。元ファイル・既存出力は変更しません。循環依存、実行時評価が必要な注釈式、危険な属性や関数呼び出し、未解決グローバル、同名衝突を拒否します。ソースのSHA-256を照合します。

実データ8ファイル652要素で検証：374トップレベル関数中、31件が静的抽出の候補になり、6件は2関数の組み合わせです。Surface Stampの `_orient2d` と `_point_in_triangle_strict_2d` を元ソース不変のまま抽出できました。

**静的条件を通過しても、Blenderでの動作・コードの安全性・ライセンス適合は保証しません。** 生成物の実行・配布前に人間のレビューが必要です。
