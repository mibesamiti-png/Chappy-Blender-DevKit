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
