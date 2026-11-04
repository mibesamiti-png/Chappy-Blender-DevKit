# 進捗記録

## v0.1 — 2026-11-04

### 実装済（コード確認・Python自動テスト対象）

- `cbdk/scanner.py`: ソース列挙、AST、シンボル台帳、bl_info、呼び出し関係
- `cbdk/dedup.py`: AST一致、構造一致、簡易類似スコア
- `cbdk/search.py`: 日本語エイリアスを用いたCLI検索
- `cbdk/report.py`: JSON / Markdown出力
- `cbdk/__main__.py`: CLIコマンド
- `AGENTS.md`: Codex開発指針

### 未実装

- 依存関係に基づく安全なコード分離・統合
- Blender実機テスト / ExtensionのZIPビルド
- 意味重複のAI検証・自動採用
- GitHubリポジトリ作成（作業環境内の単体プロジェクトを作成した段階）

### 検証状態

- Python単体テスト: 9件成功（2026-11-04 / Python 3.13.5）
- 実データスキャン: 8ファイルすべて解析成功。652シンボル、AST一致115グループ（余剰出現128）、構造一致12グループ、近似候補105ペア。`reports/initial_scan` に出力
- Blender実機検証: 未実施（Blender実行環境なし）

## 次に着手すること

候補一覧から重複の誤検知を確認し、再利用価値の高い関数15個を手動で選抜して、独立モジュール化と依存関係・ライセンス情報の管理を実装する。

## v0.2 — 2026-11-04（今回の変更）

### 実装済・Python単体テスト確認
- `cbdk/curation.py`: AST/形状/近似のレビューキュー生成、永続部品ID、出典/ライセンス証跡の記録、採否履歴、重複登録防止、JSON原子的保存
- `cbdk/__main__.py`: `triage`, `register`, `decide`, `parts` CLI追加
- `tests/test_curation.py`: 7件のテスト追加（合計16件がPython 3.13環境で成功）
- 私有ソース8件で再検証：652シンボル、115 AST一致グループ、12構造一致グループ、105近似候補、レビューキュー232件

### 未実装・要検証
- `selected` の意味一致・Blender実機検証・ライセンスの独立した確認
- 本採用(`approved`)判定・自動抽出・共通部品への置換
- Blender ExtensionsのZIP生成、Codexによる自動統合
- GitHub Actionsでのテスト結果はマージ前に確認する

## v0.4 — 2026-11-04

### 実装済（Pythonコード確認・自動テスト対象）
- `cbdk/bundle.py`：同一ファイルの関数依存グラフ、循環参照検出、単純な不変定数とmath依存処理、トポロジカル順序でのまとめ出力
- `python -m cbdk bundle`：検査専用モード／出典JSON付きでの書き出しモード
- 名前衝突・外部グローバル・動的処理・デフォルト引数・未承認のソースを検出してブロック
- 同じファイルのASTをキャッシュして一括解析の性能を改善
- 38件のPythonユニットテスト成功（既存27件 + 新規11件）。生成コードの実行テストは**合成した安全なテストデータのみ**。
- 実データ8ファイル、652シンボル、374トップレベル関数：31関数が単独／組み合わせの静的抽出条件に合格、そのうち6関数が2関数構成のグループに属する。Surface Stampの2関数を出典JSONとともに抽出し、原本SHA不変を確認。

### まだ未対応・未検証
- Blender本体を使用した抽出結果の動作検証（未実施）
- Blenderのbpy・bmesh依存を持つ関数や異なるソース間での自動切り出し
- 挙動同等性、ベンチマーク、ライセンスの法的確認、正式な採用承認
- ZIPで配布可能なBlender Extensionの自動組み立て

`eligible_for_review_extraction=true` は静的条件を満たしたことだけを表し、`verification=static_only`、`approved=false` のまま管理する。

## v0.5 — 2026-11-04

### 実装済（Python自動テスト対象）
- `cbdk/crossfile.py`：明示的な相対インポートによる複数ファイルの静的関数依存追跡、ハッシュ照合、循環参照・同名衝突検出、単純定数と math の安全側抽出、別ファイルと出典JSONへの非破壊出力
- `cbdk/blender_audit.py`：bpy/bmesh/mathutilsの呼び出し、import別名、bpy.ops・bpy.context・編集モードAPIを検出し、実機検証が必要な候補をレポート化
- `python -m cbdk crossfile` / `python -m cbdk audit-blender` CLIを追加
- 合成データでの依存連鎖、衝突、循環参照、外部API拒否、出典情報、Blender API監査などのテストを追加
- Pythonテスト：56件成功（v0.4の38件 + 新規18件）
- 自作アドオン原本8ファイル（652シンボル）で静的API監査：関連407シンボル、コンテキスト依存候補169シンボル

### 未実装・未検証
- Blender APIに直接依存する関数の自動切り出し（現在は安全側で拒否）
- 複数ファイルの別名インポート、ワイルドカード、動的インポート
- Blender本体上での生成コードの動作テストとUI検証
- 同等性証明、速度比較、法的なライセンス確認、正式部品承認、Extension ZIP自動生成

**検証状態の区別:** Python単体テスト成功・自作コードの静的解析成功。Blender実機未検証。`approved=false` のまま。
