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


## v0.2 — 2026-11-04

### 今回実装（ローカルPythonテスト確認）
- `cbdk/curation.py`: AST/構造/近似の候補をまとめたレビューキュー、固定部品ID、出典・権利証跡、レビュー履歴、同一AST登録ガード、原子的JSON保存
- `cbdk/__main__.py`: `triage`, `register`, `decide`, `parts` コマンド
- `tests/test_curation.py`: 7件追加、ローカル合計16件成功（Python 3.13）
- 非公開の自作アドオン8ファイルで再走査：652シンボル、AST一致115、構造一致12、近似候補105、レビューキュー232件

### 未実装
- 類似コードの意味一致・品質比較・自動統合
- 真の承認済（`approved`）部品の生成、独立したライセンス検証
- Blender実機テスト、アドオンビルド・ZIP配布
- GitHub CIの結果はプルリクエストで別途確認


## v0.3 — 2026-11-04

### 実装・Python単体テスト済
- cbdk/isolation.py: ソースSHAと候補IDの整合確認、外部参照とASTリスクの抽出、静的に単独化できるトップレベル関数の別ファイル出力、出典JSON出力、元ファイル保護
- python -m cbdk isolate: 診断／抽出をCLIから指定
- cbdk/blender_test.py・scripts/blender_smoke.py: 明示的な手動起動によりBlenderを背景実行する検査ツール（Blender実機未確認）
- Python 3.13: 既存16件＋新規11件＝27件成功
- 実データ8ファイル652シンボル、トップレベル関数374件中21件が厳格な静的条件で切り出し候補。Relief Pattern Toolの _smoothstep01 を原本を変更せず別ファイル出力して確認

### 未実装・未検証
- Blender実機のテスト実行、個々の抽出コードの実機検証
- 複数関数の依存グラフ解決と一括抽出、同等性・性能比較
- 権利の法的確認・部品の正式承認・Extension ZIP生成

eligible_for_review_extraction=true は静的条件を満たすだけであり、verification=static_only、approved=false のまま管理する。
