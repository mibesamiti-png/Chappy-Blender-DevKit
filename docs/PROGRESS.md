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


## v0.6 — 2026-11-04

### 実装・Python単体テスト済
- `parts/blender/context.py`: 明示的コンテキストを受け取り、アクティブメッシュと選択メッシュの読み取り専用取得（BLCTX-001/002）
- `parts/blender/edit_mesh.py`: 編集モードと単一メッシュ条件を確認するBMeshの選択要素数取得（BME-001）
- `cbdk/contracts.py`: v0.5のBlender API監査結果から、編集モード候補・Operator・実機テスト条件を含むレビュー用契約JSON生成
- `python -m cbdk contracts`: CLI。レポートは承認済みコードではなくメタデータ
- `scripts/blender_parts_smoke.py` と `python -m cbdk.blender_test blender --suite parts`: Blender実機用の信頼済み読み取り専用部品スモークテスト
- Pythonユニットテスト64件成功（v0.5の56件 + 新規8件）。bmeshはテストでは模擬化
- 原本8ファイルの再監査：407 API関連シンボル、169コンテキスト依存候補、407テスト契約、うち編集メッシュ候補10、Operator候補37

### 未実装・未検証
- Blender本体がこの環境にないため、`--suite parts` の実機検証は未実施
- 既存アドオンからのbpy/bmesh依存関数の自動切り出し・実機認証
- 複数Blenderバージョン実機互換・テストログの部品レジストリ紐付け
- 拡張機能ZIPのビルド、部品の自動採用、ライセンス確認済み判定

**区別：** `Python tests passed` != `Blender runtime verified` != `approved component`。


## v0.7 — 2026-11-04

### 実装済・Python単体テスト済
- `cbdk/evidence.py`: Blenderの信頼済みスモーク実行結果に対し、部品ID・全チェック項目を検証し、ソースとテストコードのSHA-256、Blenderバージョンを含む証拠JSONを生成
- `scripts/blender_parts_smoke.py`: 3部品の正常系・不正モード・選択メッシュ・編集メッシュを個別に記録するスモークテスト
- `python -m cbdk verify-parts`: 指定Blenderでスモークテストし、結果を保存（失敗時は検証済み0件）
- `python -m cbdk evidence-status`: 保存記録のコード／テストスクリプトのハッシュ整合性チェック（真正性は保証しない）
- `catalog/authored_parts.json`: 自作ヘルパー3部品の初期台帳（全件 `not_recorded`・`approved=false`）
- Pythonユニットテスト76件成功（v0.6の64件＋新規12件）

### 未実装・未検証
- Blender実行ファイルが現在の開発実行環境にないため、Blender本体での個別テストは未実行
- `blender_smoke_passed` は包括的な動作保証、全Blenderバージョン互換、ライセンス確認済み・正式採用を意味しない
- 外部アドオンから抽出した関数の実機テストと正式採用、配布用Extension ZIP生成


## v0.8 — 2026-11-04

### 実装
- `run_blender_tests_windows.bat` + `scripts/windows_run_blender_tests.ps1`: Windows用ワンクリック実機テスト。自動Blender/Python検出（Python>=3.11）、ユニットテスト・実機スモーク・証拠の整合性検査・ログ保存
- `.github/workflows/blender-smoke.yml`: 公式Blender 4.5.15 LTS（Linux x64）をSHA-256照合して背景起動。3部品の検査、成功/失敗ログ・JSONをActions Artifactとして保存
- `docs/TEST_ENVIRONMENT.md`: Windows/クラウド利用手順・失敗時ログ共有
- `tests/test_environment_setup.py`: 実行キット構造・CIチェックサム・プライバシー維持のユニットテストを追加

### 検証
- Python: 79/79件成功（既存76件+新規3件、Python 3.13）
- GitHub ActionsのBlender 4.5.15 LTS実機テスト: 3/3部品成功、`evidence-status` fresh=true をログで確認（PR #7 run 41800757530）
- Windows BAT：Windows実機未検証。ユーザーPCでワンクリック実行して確認する段階
- 未検証：他のBlenderバージョン・他のOS・ユーザー既存アドオンから抽出したコード・Blender Extensionの配布パッケージ


## AI Agent Skill v1.0 — 2026-11-05

### 実装
- Codexリポジトリスキル: `.agents/skills/chappy-blender-devkit/SKILL.md`
- 補助資料: `references/WORKFLOW.md`, `references/QUALITY_GATES.md`, `references/EXAMPLES.md`, `agents/openai.yaml`
- 手順: 重複/既存部品検索、AST解析、Blender context管理、Python/Blender CI、原本・ライセンス保護、GitHub PRと進捗の記録
- `scripts/package_skill.py`: 同一ソースからスタンドアロンZIPとスキル専用プラグインZIPを生成
- `tests/test_skill_package.py` と `.github/workflows/skill-package.yml`: frontmatter、参照資料、実在CLI、生成ZIPの構造を検査
- `docs/SKILL_SETUP.md`: Codex/ChatGPT向けの導入説明

### 未検証・注意
- 実際のChatGPT/Codex環境へのインストール、スキルの自動選択・呼び出しは未検証
- スキルだけでコードを自動実行する機能はなく、利用可能なツール・認可が必要
- CBDK v0.8.0とスキル v1.0.0は別々にバージョン管理

## v0.8.1 — 2026-11-05

- Windows PowerShell5.1が `unittest -v` の標準エラー出力を誤検知して停止する問題を修正（`Start-Process` でstdout/stderrを分離し終了コードを確認）。
- インストール済みBlenderを全件検出し、バージョン別に個別テスト・証拠保存。4.4.3と5.2.1のテストに対応。
- Windows GitHub ActionsでPowerShell5.1の実行回帰テスト、LinuxのクラウドBlender実機テストを4.4.3/4.5.15/5.2.1のマトリクスに変更。
- **Windows PCでの実機検証はCIと別に必要**。3部品のスモーク成功は全アドオン・全バージョンの動作保証ではない。

### Windows CIで追加発見したバグ

- CIのソースチェックアウトと一時フォルダが異なるドライブだった場合、`os.path.relpath` が `ValueError` を返していた。
- `cbdk/scanner.py` を修正し、異なるドライブ間では絶対パスにフォールバック。Pythonテスト `test_cross_volume_path_does_not_abort_scan` を追加。
- スキルZIP生成時の初期パッケージングは、公開ドキュメント `reports/README.md` を過剰に拒否していたため、ZIPから除外したうえで他の `reports/` は引き続き拒否する。


## v0.9.0 — 2026-11-05

### 実装
- `cbdk/part_matrix.py`: ローカルの実機テスト証拠JSONを読み込んで、部品IDごとのBlenderバージョン別スモーク検証表を出力。古いSHA-256・不完全な部品チェック・不正なJSON・未知の部品ID・台帳とのソース不一致は除外する。
- `python -m cbdk part-matrix --evidence-dir reports/latest`: 既存のWindowsで作成された `parts_evidence*.json` を自動集計し、`parts_matrix.json` と `.md` を作成。`--evidence` の複数指定にも対応。
- Windowsワンクリックテストは、全Blenderバージョンの実機検査後に部品マトリクスを自動生成。古いログがあってもBlenderのテスト自体を失敗扱いにしない。
- GitHub Actionsの各Blenderバージョンの実機テストでも `part-matrix` を実行し、検証結果を成果物に含める。
- `tests/test_part_matrix.py`: 3バージョン集計、改変/古いコードの拒否、破損JSON、巨大ファイル、シンボリックリンク、台帳のID・ソース不整合、CLIなど14テストを追加。

### 検証状態
- Pythonローカル 101件成功（既存87件＋新規14件）
- 部品台帳 `catalog/authored_parts.json` の採用状態を自動変更しない。集計結果は `approved_by_evidence=false`、`authenticity=not_verified` を明示。
- テストJSONは署名や真正性の保証がない。コードSHA-256一致と実機スモーク成功は、外部アドオンの挙動同等性やライセンス許諾を意味しない。
- GitHub CI / Windows版 / Blender実機テストは別途確認する。
