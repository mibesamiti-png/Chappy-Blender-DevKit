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


## v0.10.0 — 2026-11-05

### 新機能：レシピからBlenderアドオンを自動組み立て

- `cbdk/addon_builder.py`: スキーマ固定・許可済み部品ID3件とソースの整合性を検査し、信頼済みテンプレートと自作ヘルパーから**レガシーBlenderアドオンZIP**を決定的に生成。
- `recipes/mesh_inspector.json` と `templates/mesh_inspector/__init__.py`: 開発プレビューのMesh Inspector（3D View > Sidebar > CBDK）。Object/Edit Modeのメッシュ選択数を表示、選択状態・モード・トポロジーを変えない。
- `python -m cbdk build-addon --preview-unapproved`：意図しない未承認部品の配布を避ける明示的プレビューフラグ。承認やライセンスクリアの判定は**自動では行わない**。
- `scripts/blender_generated_addon_smoke.py`: クラウドのBlenderで生成ZIPを一時ロードし、アドオン有効化・Panel登録・Operator実行（Object/Edit/異常系）・無効化と後片付けを確認。
- CIでBlender 4.4.3 / 4.5.15 / 5.2.1の各バージョンについて生成アドオンも検証し、ZIP・ログをActions成果物に追加。
- `tests/test_addon_builder.py`: 構造・出典SHA・決定性・重複ID・未承認ブロック・既存ZIP上書き拒否など14件の回帰テストを追加。
- `docs/ADDON_BUILDER.md`: 使い方・検証対象・形式の制約。

### 現時点で未実装・未検証

- サンプル以外のアドオンを組み立てる汎用レシピ/独自UI設計
- Blender Extensionsの公式manifest形式でのビルド・公開
- 外部コードのライセンス許諾と部品正式採用
- UI操作感やユーザーの実際のプロジェクトでの動作

### 実際のGitHub Actions検証結果（PR #11）

- Python 3.11 / 3.12 / 3.13: **115/115件成功**（既存101＋アドオンビルダー新規14）。
- Windows PowerShellランナー（Python 3.11 / 3.13）: 成功。
- Blender 4.4.3 / 4.5.15 LTS / 5.2.1 LTS: 3ジョブとも成功。
- 生成したアドオンZIPをBlenderの一時環境に展開し、`addon_utils.enable` / UI登録 / Object Modeの読み取り / Edit ModeのV・E・F / 対象メッシュなしの拒否 / `addon_utils.disable`での登録解除を、各バージョンで**6/6項目ずつ実機確認**。
- CI成果物から `CBDK_Mesh_Inspector_Preview.zip` とテストログを取得。ユーザーWindowsの画面を操作してインストールする手順・他アドオンとの競合は未検証。
- `CBDK_BUILD_INFO.json`内の`blender_runtime_verified_for_this_build=false`は保守的なローカル生成時点の値。CIに付随する別ログが実行証拠となる（ZIPだけでは真正性を証明しない）。


## v0.11.0 — 2026-11-05

### 実装済
- `cbdk/modular_builder.py`: スキーマ2の宣言的レシピを厳密に検証し、機能IDから必要な部品IDを依存解決。許可済みテンプレートのみ取り込み、決定的なZIPを生成。任意Python・ディレクトリ参照・未検証の自動採用は禁止。
- 2種類の独立機能 `object_selection` / `edit_selection` を導入。各機能が必要とするモジュールのみ同梱。
- サンプルレシピ3種類（Object-only、Edit-only、Combined）。3つとも同一パッケージ識別子なので同時導入不可。
- v0.10の旧固定 `recipes/mesh_inspector.json` とそのビルダーは**後方互換を維持**。
- `scripts/blender_modular_addon_smoke.py` を追加、GitHub Actionsで3レシピ×Blender 4.4.3 / 4.5.15 / 5.2.1のZIP構造、選択機能、読取処理、登録解除を自動検査。
- `tests/test_modular_builder.py`: 許可リスト、不要依存の除外、決定性、インジェクション阻止、旧形式保持などの回帰テストを追加。

### まだ対象外
- 一般のユーザー提供アドオンから無承認コードを自動収集・導入すること
- 動的に新しいPython実装を生成すること、任意のUIレイアウト構成
- 個人向けプレビュー以外の公開・販売向けExtension生成、ライセンス正式承認
- UIの視覚的品質、利用者のPC固有の操作感


## v0.12.0 — 2026-11-05

### 実装
- `catalog/addon_features.json`: 自作プレビュー2機能の宣言的メタデータ（必要な部品と依存する機能、Blenderの最低対応版）を追加。JSONは実行されず、コード内の許可リストと一致が必須。
- `cbdk/feature_catalog.py`: ID・ソース・部品関係の厳格照合、未知の依存と循環検出、決定的なトポロジカル順序、部品依存閉包、Blenderバージョン範囲の検査。静的な計画を返すだけで正式承認はしない。
- `python -m cbdk feature-list` / `addon-plan` を追加。追加される機能と必要部品をZIP生成前に把握可能。
- `build-addon --target-blender 4.4.3` に対応。v1/旧固定プレビューも含め対応外のBlenderバージョンをブロック。
- レシピ式ZIPはカタログで検証した機能順・部品だけを同梱し、生成情報に対応Blender範囲と要求機能を記録する。
- カタログ操作・循環・なりすましコード・重複・無効バージョン・互換性の拒否、旧レシピとの互換性テストを追加。
- GitHub ActionsでBlender 4.4.3 / 4.5.15 / 5.2.1の機能カタログ監査・対象バージョン指定でのZIP組み立て・実機スモークを確認。

### まだ対象外
- 任意のユーザー提供アドオンからの自動採用、任意Pythonコードの自動実行
- 完全に自由なBlender UI生成、正式なExtensionsパッケージ作成と一般配布
- 実際のBlender GUIレイアウト、マウス操作の自動検証
- GitHubからBlenderへの直接インストール・更新（希望により保留中）


## v0.13.0 — 2026-11-05

### 実装
- `parts/blender/measure.py` / `BLGEO-001`：Object Modeメッシュの未適用形状に対するワールドAABBと寸法、頂点数。空メッシュ・編集中の状態・異常座標を拒否し、ユーザーシーンは変更しない。
- `parts/blender/modifiers.py` / `BLMOD-001`：モディファイア名・種類・表示/レンダーフラグの不変スナップショット。変更や適用はしない。
- 新規 `mesh_bounds` と `modifier_summary` オペレーターを `templates/modular_preview/features` に追加し、`catalog/addon_features.json` とコード許可リスト・依存マッピングに登録。
- 新規2レシピ `modular_geometry` / `modular_all`。既存の3レシピと旧v1を維持し、必要部品だけZIPに封入。
- `cbdk/evidence.py` と実機スモークスクリプトを5部品に拡張、各部品の異常系と読み取り検証を実施。
- GitHub Actionsで従来3バージョンのBlenderそれぞれで部品5件および生成アドオン5構成の有効化・モード別機能・登録解除を検査するよう変更。
- Pythonテストでスケール・オフセット座標、モディファイア結果が不変であること、未登録/空データの拒否、新レシピの依存閉包を検査。

### 検証・注意
- 本記録のCIの合否は各Pull Requestの実際のチェックを優先し、確認前に成功とは扱わない。
- GitHubからBlenderへの直接インストール・更新機能は、希望により保留中。
- **未実装**：汎用的なメッシュ加工オペレーター（形状変更）、高度なUIビルダー、Blender Extensions正式パッケージ、ライセンス/正式採用、Windows GUI手動操作の自動評価。


### GitHub Actions 実測結果（PR #14 / 2026-11-05）

- Python 3.11 / 3.12 / 3.13：**166テスト成功**（前版154件＋新規12件）。
- Windows PowerShell 5.1：Python 3.11 / 3.13両ジョブ成功。
- Blender 4.4.3 / 4.5.15 LTS / 5.2.1 LTS：それぞれ**5/5共通部品スモーク成功**。5つのレシピ（objects/edit/combined/geometry/all）で生成したアドオンすべて、有効化・演算子・モード拒否・解除の各実機テスト成功（合計15構成）。旧v1プレビューも3バージョンで成功。
- 途中のGitHub ActionsでBlender公式ダウンロードへのHTTP 403が発生したが、PR #14の最終コミット `beb92406757b79e5ac389d1b9de548d24cbb6c32` に対応する成功した3ジョブのログで確かめた。外部ダウンロードの一時的な失敗とコードの不具合を区別する。
- 部品は引き続き `approved=false`、`license_review=pending`。クラウドのLinux/ヘッドレス実機スモークはWindowsの視覚的UI品質・実作業での操作感の確認ではない。


## v0.14.0 — 2026-11-05

### 開発内容
- `parts/blender/edit_transform.py`：BME-002の `translate_selected_vertices` を追加。Edit Modeで選択頂点だけ、有限のローカルオフセットで移動。元座標の事前保存/全件検査、BMesh更新失敗時の復元、共有メッシュ・シェイプキー・マルチEdit Mode拒否。
- `templates/modular_preview/features/vertex_nudge.py`：`REGISTER`/`UNDO`付きOperator。デフォルトZ+0.1、各軸の指定±10。
- `recipes/modular_nudge.json`、拡張した `recipes/modular_all.json`。旧レシピは後方互換のまま維持。
- カタログに `BME-002` と `vertex_nudge` を未承認のまま追加。6共通部品・5機能。許可リストと最小依存マッピングを更新。
- 単体テストで移動前の検査・未選択頂点の不変・複数選択・例外時ロールバック/不完全復元検出を確認。実機スモークで頂点移動・不要なトポロジー変更なし・オペレーターのUndoフラグを検査。
- GitHub ActionsでBlender 4.4.3 / 4.5.15 / 5.2.1それぞれの6部品と6レシピ実行を要求（合計18構成）。

### 検証境界
テスト実行結果はCIのログを確認してから記載。ヘッドレスのBlenderでは実際のGUI Undoキー操作・UIレイアウトの視覚品質は未検証。失敗時ロールバックはBlenderの致命的なクラッシュまでは保証しない。Githubからの自動インストールは保留。


### GitHub Actionsで実行した検証結果（PR #15）

- Python 3.11 / 3.12 / 3.13：**182/182件成功**（旧166件＋今回の安全系16件）。
- Windows PowerShell：Python 3.11 / 3.13のジョブが成功。Windows用開発キットZIP生成も成功。
- Blender 4.4.3 / 4.5.15 / 5.2.1：6部品すべてのスモーク成功。6種類のレシピ（objects/edit/combined/geometry/nudge/all）から生成したアドオンの起動・実行・解除に成功（計18構成）。
- 新しいBME-002実機テストでは**指定頂点1個のZ座標のみ0.125移動**、未選択頂点/面・辺の数・編集モード維持・NaN拒否を検査。`vertex_nudge`オペレーターは`REGISTER/UNDO`フラグを確認。
- 初回CIは、**正常に頂点移動した結果を次の旧メッシュ寸法テストが平面と誤認した**ため失敗。テスト環境の頂点を移動後に元へ戻して、全3バージョンのCIで成功。
- `cbdk/evidence.py`に、失敗したBlenderスモークの終了コードと標準出力/標準エラーの末尾を結果JSONへ保存する処理を追加。成功認定や部品の承認状態には影響しない。
- Blender上でCtrl+Zのキー操作やUndoスタック履歴を実際に視覚操作したかどうかは未確認。ネイティブUndoフラグでの登録と編集処理の動作確認が今回の検証範囲。


## v0.15.0 — 2026-11-05

### 実装
- `parts/blender/edit_audit.py` を追加。BME-003：メッシュの座標/頂点選択/辺と面の接続を最大20万要素まで不変スナップショット化。計算後の差分を検査し、予定外の変更が起きたら失敗とする。
- `parts/blender/edit_transform.py` の `translate_selected_vertices` に監査を接続。加工後に全頂点とトポロジーの差分を確認し、書込失敗・監査違反では座標と選択を復元。復元不能・トポロジー改変は明確なエラー。
- `VertexTranslationResult.audit` に差分情報を格納。以前の `moved_vertices` と `offset` は維持。
- `vertex_nudge` が依存する共通部品としてBME-003をカタログとallowlistに追加。**7部品・5機能**、旧レシピの機能は維持。
- Blender実機の部品スモークに、未選択頂点を意図的に破損させて差分検出・復元するテストを追加。
- Pythonテストでは座標・選択・辺/面の接続の一致、無関係な頂点の変更、復元失敗と大量メッシュのガードを検証。
- Blender 4.4.3 / 4.5.15 / 5.2.1で従来の6構成アドオンを再検証するCIを継続。

### 制約
- スナップショット検査はローカルの補助的検証であり、Blenderのクラッシュ、全データの復旧、完全なAtomic Transaction、GUIでのUndo動作まで保証するものではない。
- 部品の正式採用・再配布許可は未確認。GitHubからBlenderへの直接インストールは引き続き保留。


## 引き継ぎ台帳への移行（2026-11-05）

長い会話を読み込めない場合でも開発を継続できるよう、GitHub上に `docs/project/STATE.json`（最新版の要件・実装/未実装・既知の問題・優先タスク・実測CI記録）と、そこから自動生成される `docs/PROJECT_HANDOFF.md` を導入。

このファイルは**過去の節目と判断過程を残す履歴**として維持する。現状把握と新規チャットの再開は `docs/PROJECT_HANDOFF.md` を先に読む。PR/節目では状態台帳を更新し、GitHub Actionsによる照合/同期を実施。


## v0.16.0 — 2026-11-05

### 実装
- BME-003: preflight_audit_sizeでBMesh要素数を列挙/コピー前にチェックし、20万要素超は加工前に拒否。
- audit_live_vertex_translationを追加。加工後の頂点座標/選択状態を逐次読み込み、2個目のフル頂点スナップショットを不要にした。辺/面接続は従来どおり確認。
- BME-002のtranslate_selected_verticesからライブ監査を呼び出すよう変更し、入力事前検証・失敗時のスナップショット復元は維持。
- 誤差判定を巨大なワールド座標の絶対値ではなく、期待移動量で評価して小さな編集失敗の偽成功を防止。
- tests/test_audit_scaling.py に12件の境界値、重複しない接続、異常編集の回帰テストを追加。
- scripts/blender_audit_scaling_smoke.py でBlenderの70×70格子メッシュを使った時間・追跡メモリの観測値と上限拒否時の形状不変を検証。
- 既存7部品・5機能・6レシピを維持。3バージョンのBlender CIにスケーリング検査を追加。
- docs/project/STATE.jsonの状況・バグ・次の作業を更新。生成引き継ぎ書はGitHub Actionsで自動同期する。

### 限界
- 20万要素の上限は継続。辺/面の接続照合では一時的なデータを確保し、完全なゼロメモリではない。
- Blenderのクラッシュ時の原子性、GUIでのCtrl+Z/Redo操作感は未検証。
- CIの実行結果を確認するまでこのバージョンの成功を断定しない。状態台帳のlast_verifiedが旧版を指す場合、新版は未確認という意味。


### v0.16 の確認済み実測とCIブロッカー（2026-11-05）

- PR #18 のコミット `aa4a5cb8c93e1d58c1b9a1649b6dc38b55ac174c` で、GitHub Python CI（3.11/3.12/3.13）、Blender 4.4.3/4.5.15/5.2.1 の実機スモーク、開発用Windows ZIP生成は成功。
- GitHub Actionsから取得したBlender 70×70格子の実測: 5,041頂点、9,940辺、4,900面。頂点移動＋監査 4.4.3: 0.19051秒、4.5.15: 0.24000秒、5.2.1: 0.45833秒（GitHubホスト固有の参考値、一般的速度保証ではない）。上限超過の変更前拒否と旧差分検査との一致を3バージョンで確認。
- ローカルに取得したPRのWindowsキットをPython 3.13で展開し、`python -m unittest discover -s tests` を実行して **221/221 OK** を確認。旧テストの優先順位固定値と新しいBlender性能テストのモジュール読み込みパスは修正済み。
- **ただしWindows PowerShell CIはGitHub上で失敗扱い**。該当ジョブの `steps`・`logs_url` が未取得、ログ取得は404 BlobNotFound。再実行およびWindows 2025ランナーへの一時的切替でも改善せず、既存Windows 2022ランナーへ戻した。
- さらに後続のCI実行ではPython/Blender/ZIPまで実行ステップが出ないまま失敗扱いとなる。原因は現時点で未確定。詳細は [Issue #19](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/issues/19)。**全CIが再検証できるまでPR #18をmainへマージしない**。`last_verified` は引き続きv0.15の成功記録。


### v0.16 CIリソースの調整（2026-11-05）

GitHubのCIジョブが実行ステップ0・runner_id=0で終了する状態をAPIで再確認。11月4日のGitHub Actions障害は公式では解消済みのため、Actions利用枠・予算ブロックなどアカウント固有の原因も候補としてIssue #19に記録（**原因は未確定**）。過去の大量のPR更新で同じコミットのpushとpull_requestが重複テストを実行していたため、Python CIのpush対象をmainに限定。6つのワークフローにPR単位のconcurrencyキャンセルを追加。引き継ぎCIはPRでの重複Pythonテストを省略し、main push時の実測記録は維持。Blender3版とWindows PowerShellの実機品質ゲートは削除しない。新しいCI改善用の回帰テストを追加。**全CIが実行できるまでマージしない**。



### v0.16 追加修正：非有限座標からの安全な復元（2026-11-05）

- BME-003の復元処理が、異常座標を修復する前に `capture_edit_snapshot` を呼び出し、NaN/Infを含むBMeshを拒否する問題を確認。
- `_topology_matches_snapshot` を追加し、**座標を読み取らず**に頂点/辺/面の個数と接続関係を照合してから元座標・頂点選択を復元するように修正。
- 復元後は元座標、選択、接続関係を**再検査**する。Setterが例外を出さず元の値に戻せなかった場合も、不完全復元として明示する。
- NaN/Inf混入、破損座標の読み出し不可、サイレントsetter失敗、編集途中で未選択頂点が非有限に破損する場合を扱う回帰テスト4件を追加。
- ローカル（Python 3.13.5）で **229/229件成功**。これはGitHubの実機CI合格とは区別する。CI用ブランチ `feature/v0.16-audit-streaming` 上に保存済み。最新のGitHub Actionsは `runner_id=0` / `steps=0`で終了するため未マージ。原因追跡は [Issue #19](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/issues/19)。


### v0.16 追補：旧・新監査の判定統一（2026-11-05）

- 旧スナップショット監査 `audit_vertex_translation` が、移動量が極小で実際には頂点座標が変化していなくても数値許容誤差の範囲で成功扱いしてしまうケースを修正。新ストリーミング監査と同じく、**非ゼロの移動が観測できなければ失敗**とする。
- 両監査が受け付ける `delta` を共通の厳格バリデーターに統一。文字列・bool・None・NaN/Inf・不適切な形を例外化し、未処理のTypeErrorを外へ漏らさない。
- 新規回帰テスト3件：極小移動の無反映、未選択状態での無反映、不正値を旧・新監査が同じように拒否すること。
- 既存メッシュ加工/監査テストを含め**ローカルPython 3.13.5で232/232件成功**。これはGitHub ActionsのWindows/Blender CIとは独立の検証。PR #18は引き続き未マージで、Issue #19のランナー割当問題の解消待ち。


### v0.16 追補：XYZの各軸の監査を強化（2026-11-05）

- 旧・ストリーミング両監査で、3軸をひとまとめに見ず、各座標を**要求移動量と個別に照合**する方式へ変更。例えば「X方向は動いたが、同時に指定された微小Y移動が反映されなかった」場合も検出する。
- 移動量ゼロを要求した軸と未選択頂点については**元の座標との完全一致を要求**。従来の絶対誤差閾値以下の予期しない微小変更も失敗扱いする。
- 非ゼロ移動の数値誤差は絶対閾値と移動量に対する15%の相対閾値の小さい方を使用し、非常に小さい要求を誤差の範囲として見逃さない。float32の丸めで精度不足の場合、正しく拒否する安全側の設計。
- 新規回帰テスト6件：1軸のみ反映、未選択頂点の微小変更、期待移動量より大幅に小さな変更、微小な正しい移動、ゼロ移動軸の変更、頂点移動処理での部分反映の検出とロールバック。
- ローカルPython（3.13.5）の**全238件成功**。最新のBlender/Windows GitHub CIはランナー割当前の問題が継続し、**未検証**。PR #18はmainへマージしていない。


## v0.17 開発中 — 2026-11-05（背景Blender Undo/Redoの証拠分離）

### 開発ブランチで追加
- `scripts/blender_undo_redo_smoke.py`: CBDK生成の `modular_nudge` プレビューだけをBlenderファクトリー設定の別プロセスで有効化し、選択頂点の移動・トポロジー不変を確認。可能ならBlenderネイティブ `bpy.ops.ed.undo/redo` の結果を編集データから再取得して検証。
- `cbdk/undo_probe_report.py`: 構造化JSON証拠を検証し、`verified_background` / `partial_background` / `unavailable_in_background` を区別。`poll()=False` を成功と誤認しない。GUIショートカット検証済みを名乗る証拠は禁止。
- `tests/test_undo_probe_report.py`: 不整合・未検証の成功偽装・二重レコード・不正JSON・GUI検証誤認を拒否するPython回帰テストを追加。
- `.github/workflows/blender-smoke.yml`: 既存6レシピをビルドした後に`modular_nudge`を対象として単独のUndo/Redoプローブを実行し、結果を`reports/ci/undo_redo.json`に保存するCI工程を追加。

### 検証状態・注意
- **この追加変更のPython全体テスト・Blender実機CI・Windows GUIは未実行。** 成功数は記録しない。
- Blenderのバックグラウンド環境ではネイティブUndo/Redoのpollが利用不可の可能性があり、その場合は`unavailable_in_background`を保存する。これはUndo/Redo動作確認の成功ではない。
- GUI Ctrl+Z / Ctrl+Shift+Z の実機操作は別件（GUI-001）として未実装・未検証のまま。
- `main`はv0.15.0、v0.16のPR #18もCIブロッカー Issue #19 により未マージ。v0.17変更は`feature/v0.17-undo-redo-probe`に隔離し、正式検証前にmainへ統合しない。
- `last_verified` はv0.15.0の記録を維持する。

## v0.17 追加開発 — 2026-11-05（6レシピの静的整合マトリクス）

### 変更
- `cbdk/recipe_matrix.py`: `modular_objects` / `modular_edit` / `modular_combined` / `modular_geometry` / `modular_nudge` / `modular_all` の期待機能セットを個別に管理し、カタログ許可リスト・部品依存閉包・信頼済みソースの存在・Blender 4.4.3/4.5.15/5.2.1との静的互換性をまとめて監査する。コードは**実行せず読み取りのみ**。
- `python -m cbdk.recipe_matrix --output reports/ci/recipe_matrix.json`: 依存と安全情報だけを記した決定的JSONを生成。ライセンス承認/Blender実機検証/GUI品質を主張しない。
- `tests/test_recipe_matrix.py`: 13テストを追加。レシピ構成変更、余計なコード欄、欠損ヘルパー、部品参照改変、対応Blender範囲、サイズ過大、シンボリックリンクなどを拒否する。
- `.github/workflows/blender-smoke.yml` に一括監査を追加。Blender生成アドオンのビルド前に実行しJSONを証拠成果物へ格納する。

### 検証状態
- **今回追加した13件を含むPythonテストと新規CIはまだ実行結果を確認していない**。実装とテストの存在は確認したが、成功としては記載しない。
- v0.17ドラフトPR #20の開発ブランチに保存。前提のv0.16 PR #18はCI障害Issue #19のため未マージ。mainはv0.15。
- 部品の正式採用や公開用Blender Extensions生成は引き続き範囲外。 `last_verified` は前回のv0.15のまま。
- 追加のUndo証拠バリデーションでは、ステータスの非文字列型・真偽値によるJSONスキーマ偽装・Blenderバージョン文字列中の制御文字を拒否するよう強化。回帰テスト1件を追加（**実行結果は未確認**）。

## v0.17 開発中 — 2026-11-05（登録ドラフト生成）

### 実装したもの
- `cbdk/registration_draft.py`: 新規自作機能ID・既存部品依存・任意の新規部品ID/ソース予定名を受け、登録に必要な作業項目を**レビュー用JSON**にまとめる。現行カタログとPythonの固定allowlistを照合し、未知の部品ID、重複ID、既存ソース衝突、パストラバーサルを拒否。
- `python -m cbdk registration-draft`: CLIを追加。標準出力にJSON、`--output reports/latest/*.json` 指定時のみプライベートなローカルレポートを新規作成（上書き禁止）。
- `tests/test_registration_draft.py`: 登録計画、既存部品のみの構成、悪意あるID、未登録/重複依存、改変されたカタログ、ファイル衝突、プライベート出力のシンボリックリンク回避、CLI異常終了など16件の回帰テストを追加。
- `docs/REGISTRATION_DRAFT.md`: 操作例と、作業計画は実機認定でもライセンス確認でもないことを文書化。
- GitHub引き継ぎのREG-001要件に登録し、NEXT-003（登録とレシピ構築の改善）を継続。

### 検証・制限
- **今回追加した16件のPython回帰テストとGitHub Actionsはまだ成功を実測していない。** コードとテストが保存された段階。Blender GUI・Windows実機でも未検証。
- レポートは `status=proposal_only`, `approved=false`, `runtime_verified=false`, `catalog_modified=false`。元アドオンの自動実行や許可済みソースへの自動登録は実施しない。
- v0.17の開発先はドラフトPR #20、ベースv0.16 PR #18はIssue #19のCIランナー未割当問題で未マージ。安定版mainとlast_verifiedはv0.15.0のまま。

## v0.17 開発中 — 2026-11-05（登録計画→安全なテストひな形生成）

- `cbdk/registration_scaffold.py`: 保存済みの登録提案JSONを厳密に検証し、現行カタログ/許可リストから同じ計画を再計算。不一致・重複JSONキー・型不整合・シンボリックリンク・領域外参照を拒否する。
- `python -m cbdk registration-tests --draft reports/latest/registration_draft.json`: `reports/latest/scaffolds/test_<feature_id>_review.py` のみ新規生成。Git管理外領域で上書き禁止。元ソース、カタログ、公式テストには書かない。
- ひな形の5テストは、権利と依存のレビュー、Blenderモード・選択、期待結果、異常入力の不変性、Undo/Redoと複数版でのスモーク。それぞれ `self.fail("TODO: ...")` を初期設定にして、レビュー前に誤って成功しないようにする。
- `tests/test_registration_scaffold.py`: 19件の回帰テストを追加。悪意ある入力、JSONキー重複、検証結果の偽装、誤った依存関係、古い台帳、出力上書き、symlink経由の領域逸脱、CLI接続を確認するテストコード。
- `docs/REGISTRATION_DRAFT.md` を更新。要件 `REG-002` と決定 `DEC-010` をGitHub引き継ぎ台帳に追加。

**検証状況：** この変更の19回帰テストとBlender/Windows実機CIの成功はまだ実測していない。GitHub ActionsはIssue #19で実行開始前に失敗しており、主張できる直近の全CI成功はv0.15.0のまま。ドラフトPR #20で保留。

## v0.17 開発中 — 2026-11-05（動作種別によるテストひな形の切替）

- `cbdk/registration_draft.py` に、開発者申告の `unspecified`, `read_only`, `mesh_edit` を追加。未指定の従来JSONには新しいキーを出さず、後方互換性を維持。
- CLI `python -m cbdk registration-draft --behavior read_only|mesh_edit` を追加。テスト項目を切り替える申告値であり、元の未確認ソースの自動解釈・実行ではない。
- `cbdk/registration_scaffold.py` のレビュー用未完成テストひな形を分岐。従来の共通5件に加え、read_onlyでは不変性と不要なUndo変更、mesh_editでは選択範囲変更・ロールバック・Undo/Redoの3件を追加（どちらも合計8件）。全項目は `self.fail(TODO)` で初期状態不合格。
- `tests/test_registration_behavior.py` に回帰テスト13件を追加。既存ドラフト互換性、明示値の検証、生成されたソースの構文、未完了テストのカウント、CLI経由の申告、新規ソース無改変等をテストするコードを登録。
- `docs/REGISTRATION_DRAFT.md`、仕様書、進捗台帳、引き継ぎ、AGENTSを更新。要件ID `REG-003` / 設計判断ID `DEC-011`。

**確認状況：** 上記13件はテストを追加しただけで、GitHub ActionsやBlender/Windows実機では成功を確認していない。PR #18/20はCIの実行前障害（Issue #19）で未マージ。検証済みの最新バージョンはv0.15.0。


## v0.17 開発中 — 2026-11-06（GLB Visual Inspector）

### 実装
- `cbdk/glb_inspector.py`: GLB 2.0のヘッダとJSONチャンクだけを標準ライブラリで解析。scene/node/mesh/material、primitive、POSITION/index accessor件数をJSON化し、外部URI・画像・埋め込みデータを実行/デコードしない。
- `python -m cbdk glb-inspect model.glb`: Blenderなしで `structure.json` 相当の構造レポートを出力。
- `cbdk/glb_render.py` + `scripts/blender_glb_render.py`: 信頼済みBlenderを `--background --factory-startup` で起動し、GLBを実importして `front/right/top/iso` の4PNGと `scene_metadata.json` を生成。
- `python -m cbdk glb-preview model.glb --blender <path>`: 静的構造JSONとBlender実レンダリングを一括生成。
- `scripts/blender_make_glb_fixture.py`: CI専用にCube + Sphereの決定的GLBを作成。
- Blender 3バージョンCIへ、fixture生成 → 静的解析 → 4方向レンダリング → オブジェクト名/枚数/metadata確認を追加。
- `docs/GLB_VISUAL_INSPECTOR.md`: AIがGLB形状を判断する際は、画像生成AIの再構成ではなくBlender実レンダリングと構造JSONを優先するルールを記録。

### 現時点の確認
- GLB静的解析8件 + Blender起動ラッパー5件、合計13件のPython単体テストをローカルで成功。
- ユーザー提供の実GLB `うさぎとかえる - A5(1).glb` を静的解析し、7 node / 7 meshを検出。node名として `足の甲.001`, `つま先.001`, `かかと.001_A`, `かかと.001_B`, `BallJoint_001_Ball` などを読み取れた。これはGitHubへ実データを保存したという意味ではなく、ローカル検証のみ。
- Blender 4.4.3 / 4.5.15 / 5.2.1での新しいGLBレンダリングCIはまだ成功結果を確認していないため、実機検証済みとは記録しない。

### 設計判断
- GLBの内容を画像生成AIだけで「再現した画像」は元データの正確なプレビューとして扱わない。
- 今後の形状理解は `front/right/top/iso PNG → scene_metadata.json → structure.json → ユーザースクリーンショット` を主要根拠とする。
- GLBはModifier、Edit Mode選択、BlenderアドオンPropertyを完全保存しないため、内部構造デバッグでは.blend/Blender実機を引き続き併用する。


### PR #21 CI観測（2026-11-06）
- GLB Visual Inspector用ドラフトPR #21を `feature/v0.17-undo-redo-probe` 向けに作成。
- GitHub ActionsはPython、Windows、Blender 4.4.3 / 4.5.15 / 5.2.1、durable handoffの全実行ジョブで失敗表示となったが、API上はすべて `steps=null` / `logs_url=null`。リポジトリコードや新しいGLBテストへ到達した証拠がない。
- 実行ID: Python `42172631874`、Windows `42172632052`、Blender `42172631906`、handoff `42172631812`。
- 既存Issue #19へ同じランナー割当症状の再現として記録。**GLB実装のBlender runtime failureとは判定せず、未検証を維持する。**


## v0.17 GLB Visual Inspector — 7方向・部品単独・Quick Preview fallback

- Blender本命レンダラーを4方向から**7方向（front/back/right/left/top/bottom/iso）**へ拡張。GLB内Mesh Objectを最大32個まで1個ずつ斜視レンダリングし、重なって隠れる部品を個別確認できるようにした。
- 構造確認では元マテリアルの透明/発光に影響されないよう、Blender内だけで中立Clayへ一時置換。元マテリアル名はscene metadataに保持。
- `glb_inspector.py` schema v2: nodeのparents/mesh_name、POSITION accessor min/max、壊れたnode/mesh参照、node cycleを検査。外部buffer/image URIは**参照だけ記録し読み込まない**。
- `glb-quick-preview` を追加。任意依存 `trimesh + matplotlib + numpy` でBlenderなしでも7方向+部品単独画像を作る。外部URIはloader起動前に拒否、50万頂点/25万面を上限にする。
- ユーザーの `うさぎとかえる - A5(1).glb` をローカル検証し、**7 node / 7 mesh**、足の甲・つま先・かかとA/B・円柱2個・BallJoint球を識別。Quick Previewで**7方向画像 + 7部品単独画像**を実生成できた。ユーザーデータはGitHubへコミットしていない。
- Quick PreviewはMatplotlib 3D由来の低精度fallbackであり、Blender実レンダリングと同等の証拠にはしない。
- 最新PR #21 workflowもPython/Blenderジョブが `steps=null` のまま実行前失敗。Blender 4.4.3/4.5.15/5.2.1実機検証は引き続き未確認。


## 2026-11-06 — public化でGitHub Actions実機デバッグ復旧

- リポジトリをpublicへ変更後、private時に発生していた `runner_id=0 / steps=null` のGitHub Actions実行前失敗が解消。Issue #19を解決としてclose。
- PR #21 head `b2579a4c0149657089c5e6109bed263a5d619dde`: Python 3.11/3.12/3.13、Windows PowerShell 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1の全workflow成功。
- 実CIでWindows一時フォルダの8.3短縮パス差、Blender sibling script import、headless EGL不足、Blender版ごとのrender engine enum差を発見して修正。
- GLB Visual Inspectorは3つのBlender版で合成Cube+Sphere GLBをimportし、構造JSON、scene metadata、front/back/right/left/top/bottom/iso、部品単独サムネイルの生成に成功。
- 背景Blender Undo/Redoプローブは3版で実行。`undo.poll()`不可は `unavailable_in_background` として正常に区別し、GUI Ctrl+Z成功とは扱わない。
- PR #18/#20の旧失敗workflowもpublic化後に再実行し、下位開発スタックの再検証を開始。mainの正式 `last_verified` は統合前なのでv0.15.0のまま維持。


## v0.17.0 正式化 — 2026-11-06

- PR #18 → #20 → #21 の順でmainへ通常mergeし、v0.16監査改善、v0.17 Undo/Redo証拠分離・登録ワークフロー、GLB Visual Inspectorを統合。
- `release/v0.17.0` をmainから作成。`pyproject.toml` とSTATEのcurrentを0.17.0へ更新し、次予定を0.18.0へ進める。
- 正式な `last_verified` はこのrelease PRのPython/Windows/Blender CIが成功した後に更新する。GUI Ctrl+Z/操作感は対象外。
- 次段階として `NEXT-008` に「参考GLB→アドオン生成→GLB再出力→形状差分の自動デバッグ」を登録。


### v0.17.0 release gate 成功 — 2026-11-06

- PR #22 head `804956cf56eafce1c34d1fe1d80d95e54a95fd4c` でPython **334/334**を3.11/3.12/3.13すべて成功。
- Windows PowerShell 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1、Windows kit、durable handoffが全成功。
- Blender 3版すべてで7部品、6レシピ、監査スケーリング、背景Undo/Redoプローブ、GLB 7方向＋部品単独レンダリングfixtureを成功。
- `last_verified` をv0.17.0へ更新。GUI Ctrl+Z/操作感と個別ユーザーGLBのBlender実レンダリングは別検証として残す。


## v0.18 開発中 — GLB形状回帰比較（2026-11-06）

- Blender GLB evidenceをschema 3へ拡張し、各Mesh Objectのworld-space AABB（min/max/center/size）を保存する。
- `cbdk/glb_compare.py`: reference/candidateのscene metadataを比較。全体寸法・中心、部品寸法・中心を許容差付きで判定し、名前が違う場合は寸法＋位置でfallback matchingする。
- `shape` profileではトポロジー差を情報扱い、`strict` profileでは名前・トポロジー差も失敗扱い。欠落/余分部品は体積proxyで重大度を判定。
- `python -m cbdk glb-compare ref/scene_metadata.json cand/scene_metadata.json`: 既存証拠を比較。
- `python -m cbdk glb-regression reference.glb candidate.glb --blender <path>`: 両GLBをfactory-startup Blenderで別々に7方向レンダリングし、比較JSONまで一括生成する。
- 初期版はbounds中心のため、同一外接寸法で輪郭/内部形状だけ異なるケースは完全検出できない。7方向画像を併用し、将来シルエット/表面距離へ拡張する。
- 新規Python/Blender CI結果はまだ未確認。last_verifiedはv0.17.0を維持。


### v0.18 GLB shape regression CI成功 — 2026-11-06

- PR #23でPython **343/343** を3.11/3.12/3.13すべて成功。Windows PowerShell 3.11/3.13、Windows kit、durable handoffも成功。
- Blender 4.4.3/4.5.15/5.2.1すべてでsynthetic GLBからschema 3 metadataの`world_bounds`を生成し、`glb-compare`による自己比較まで成功。
- GLB-003を実装済み/Blender CI検証済みに更新。ただしboundsが同じ別輪郭・穴・内部形状は完全判定できないためLIM-008は継続。
- NEXT-008全体（アドオン生成→出力GLB→自動修正ループ）はまだ進行中。比較エンジンが最初の基盤として完成。


## v0.18 開発中 — シルエットIoU回帰（2026-11-06）

- Blender import後の実メッシュを正射影し、32x32のbinary silhouette bitsetをscene metadata schema 4へ保存する。
- 全体は7方向、各部品はfront/right/top/isoの4方向。最大32部品、1回のsignatureは25万三角形を安全上限にする。
- `glb-compare` は同方向bitsetのIoUを計算し、既定0.90未満を`scene_silhouette` / `object_silhouette`エラーとして記録する。部品差分では対象部品名と方向も出す。
- boundsが同じでも輪郭が違うケースを検出するPython回帰テストを追加。小さな穴やサブピクセル細部は32x32量子化で見逃しうる。
- 現時点では実装保存のみ。Python/Windows/Blender CI成功はまだ確認していない。


### v0.18 silhouette drift 実機検証成功 — 2026-11-06

- PR #24 head `2735aa974539ec95fde20e2c9f1de155f6687209` でPython **347/347**を3.11/3.12/3.13、Windows PowerShell 3.11/3.13、Windows kit、durable handoffが成功。
- Blender 4.4.3/4.5.15/5.2.1すべてで32x32 scene/object silhouette signatureを生成。
- reference Cubeと、同じworld boundsを持つ八面体candidateを作り、bounds許容差を緩めても`scene_silhouette`または`object_silhouette`で失敗判定することを3版すべてで確認。
- Blender 4.5.15では`glb-regression`のreference→candidate一括経路も意図どおりexit 1となり、比較レポートを生成。
- GLB-004を実装済み/Blender CI検証済みに更新。小穴・内部形状・32x32未満細部は次段階の課題。

## v0.18 開発中 — 2026-11-06（GLB診断の数値根拠とフェイルクローズ）

- PR #25の `cbdk/glb_diagnose.py` を拡充。全体7視点のシルエット差分はscene単位で束ね、部品別の差分は個別に保持。`evidence_summary`へ、対象視点、最悪IoU、最大相対誤差、欠落部品の体積割合、重大度ごとの件数を集約。
- 比較元の`passed`とerrors/差分数が矛盾する場合は診断を拒否。JSON重複キー・NaN/Infinity・不正なseverityや数値、過大な証拠データを拒否。
- 警告/情報や未対応の差分コードだけが残っていても、`needs_review=true`とする。比較合格は指定許容差での判定に過ぎず、3D形状の完全一致・内部の空洞を保証しない。
- `tests/test_glb_diagnose_evidence.py` に19件の回帰テストを追加。既存7件は残す。
- 原本GLBの自動編集、アドオンコード修正、許可やマージは行わない。私有GLBの公開GitHubへのアップロードも行わない。

**検証状態**：追加19件のCI実走とBlender実機・Windowsでの現在のPR headの成功は未確認。合格記録は以前の実測release v0.17.0を維持（GLB-005: not_tested）。

### v0.18 GLB-005 — 実測CI検証結果（2026-11-06）

PR #25の実装コミット `e971b784e5f6694252e924c0b8183dd393aa3860` に対するGitHub Actionsで次を確認。

- Python 3.11/3.12/3.13: 全ジョブ成功（run [42202420004](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42202420004)）。GLB数値診断の追加19回帰テストを含む。
- Windows PowerShell 3.11/3.13: 全ジョブ成功（run [42202419886](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42202419886)）。
- Blender 4.4.3/4.5.15/5.2.1: 全ジョブ成功（run [42202419874](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42202419874)）。形状差分fixtureの診断レポートについて対象視点・最悪IoU・error件数と非自動承認をCIで検証した。
- Windowsキット生成: 成功（run [42202419926](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42202419926)）。
- 永続引き継ぎチェック: 成功（run [42202419869](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42202419869)）。

**境界**：これは上記コミットの実測。検証記録を追記する後続のドキュメント変更やユーザー個別GLBの再現率まで保証しない。PR #25はドラフト、mainに統合していない。`last_verified`の正式v0.17.0は変更しない。

## v0.18 開発中 — 2026-11-06（形状原因から設定候補へ）

- `cbdk/glb_repair_plan.py` 新規実装。既存のGLB診断から、原因カテゴリ別の設定候補群、確認項目、対象部品、該当視点、最悪IoU、観測誤差の主軸を出力。ボール・ソケット・ヒンジの部品名を手がかりにした候補は、あくまで未確認の推測として表示する。
- CLI `python -m cbdk glb-repair-plan <comparison.json> --output reports/latest/glb_repair_plan.json` を追加。入力を再診断してから候補計画に変換し、元のユーザーGLBやアドオンコードは実行しない。
- `cbdk/glb_regression.py` に `repair_plan.json` の自動出力を統合。比較・診断・修正確認プランの3つのJSONをまとめて記録できる。
- `tests/test_glb_repair_plan.py` に20件追加。部品別候補、軸方向の観測値、安全フラグ、未知差分、入力不正、CLI、出力と元データ不変性を回帰確認するテストを用意。`tests/test_glb_regression.py` も統合検証を追加。
- Blender 4.4.3 / 4.5.15 / 5.2.1 のGLB差分fixtureで`glb-repair-plan`を実行し、レビュー専用・未承認・影響視点・最悪IoUを検査するCIを追加。Blender 4.5.15ではe2eの`repair_plan.json`も検査する。
- 正本STATE.json/引き継ぎの新要件`GLB-006`、新設計判断`DEC-018`、次タスク`NEXT-009`を登録。

**実測CI結果（2026-11-06）:** PR #25のコードHEAD `d9c5c92590759faac158824d84e4f8ca94c7c5bb` で、次のGitHub Actionsが全成功。

- Python 3.11/3.12/3.13：[run 42204425313](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42204425313)。新規20回帰テストを含む。
- Windows PowerShell 3.11/3.13：[run 42204425351](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42204425351)。
- Blender 4.4.3/4.5.15/5.2.1：[run 42204425335](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42204425335)。GLBの同外寸・異輪郭fixtureから比較・診断・設定候補プランを生成し、安全フラグ・最悪IoU・対象視点を検証。
- Windowsキット：[run 42204425475](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42204425475)。
- 引き継ぎ検証：[run 42204425288](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42204425288)。

これを根拠にGLB-006は実装済/Blender CI検証とする。参照GLBと生成GLBの完全一致、内部空洞、実アドオンの設定と候補名の合致は未検証。後続の記録更新コミットのCI成功とは区別する。PR #25は未マージ、正式last_verified=v0.17.0を維持。

## v0.18 開発中 — 2026-11-06（GLB-007: 静的プロパティ照合）

- `cbdk/glb_property_map.py`を新規実装。`ast.parse`のみでBlender `bpy.props`のクラスレベル宣言を列挙し、GLB修正プランの候補群へ名前完全一致で対応付ける。import別名に対応。実際のBlenderアドオンをインポート・実行しない。
- CLI `python -m cbdk glb-map-properties <repair_plan.json> --source <local-addon.py> --output reports/latest/glb_property_mapping.json` を追加。入力Pythonファイルは明示指定のみ（最大16、各1MiB）。プランJSONは安全フラグ/候補名/件数を照合する。
- 出力は`cbdk_glb_property_mapping` JSON。完全一致した宣言と未一致候補を分離。匿名ファイルラベル、クラス、行、Property種別だけを出力し、私有コード本文・デフォルト値・実ファイル名・絶対パスは含めない。
- `tests/test_glb_property_map.py`に24件の回帰テストを追加。AST注釈型/通常代入、import別名、偽のFloatProperty、関数ローカル変数の誤検出、トップレベル副作用の非実行、私有データ遮断、入力異常、symlink、無害な結果、CLIを検証する。
- Blender CIへ合成プロパティ定義ファイルを作成するステップを追加し、GLB差分fixtureの`glb-repair-plan`に含まれる候補名へAST照合する。**合成ソースは実行しない**。
- `docs/GLB_PROPERTY_MAPPING.md`を作成、STATE.jsonへ`GLB-007`、`DEC-019`と進行中タスク`NEXT-009`を記録し、引き継ぎを同期。

**検証境界:** このコードの追加時点での静的記録。最新headのPython/Windows/Blender CIは実際の成功ジョブを見てから検証状態を更新する。GUI上の登録確認・実アドオンのジオメトリ変化・ユーザー私有GLBでの完全一致は未検証。正式v0.17.0のlast_verifiedは保持。

### GLB-007の実測CI（2026-11-06）

実装コミット `c36350754770e54ed30695b63661382bf815682c` に対して、次の5ワークフローが実際に全成功。

- Python 3.11/3.12/3.13： [run 42206398064](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42206398064)。新規24回帰テストを含む。
- Windows PowerShell 3.11/3.13： [run 42206398098](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42206398098)。
- Blender 4.4.3 / 4.5.15 / 5.2.1： [run 42206398080](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42206398080)。合成GLBから得た原因候補と合成Pythonファイル内のBlenderプロパティをASTのみで照合し、名前一致・未実行・未適用の安全フラグを確認。
- Windowsキット： [run 42206398068](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42206398068)。
- 引き継ぎ： [run 42206398078](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42206398078)。

GLB-007は実装済/Blender CI確認済みとして記録。正式バージョンはv0.17.0のまま、v0.18 PR #25はドラフト。**未検証:** 個人用アドオンに実際に登録されたプロパティか、その値が形状に影響するか、ユーザーのGLBが正確に再現できるか。元私有ソースはコミット・実行していない。

## v0.18 開発中 — 2026-11-06（GLB-008：プロパティ参照のAST静的追跡）

- `cbdk/glb_property_usage.py` 新設。宣言名と同じ属性に対するread/write/read_write/deleteの4種をASTで識別し、関数・クラス・行番号・匿名ソースラベルをレポートに収録する。受け手の型・登録状態は**未検証**と明示。
- `cbdk/glb_property_map.py` に `exact_name_matches[].possible_code_references` を統合。宣言がない同名のアクセスだけではプロパティが存在する扱いにしない。`static_possible_attribute_references_found` は宣言と同名属性のAST出現総数。
- `tests/test_glb_property_usage.py` に新規23回帰テストを追加。読み取り/代入/拡張代入/削除、関数・クラス・複数ソース、動的getattrの未検出、機密値遮断、ソース副作用の未実行、上限超の拒否、マッピング連携を検証する。
- Blender 3バージョンの合成fixtureを拡張し、静的参照読み書き・未検証フラグをCLIから検証するワークフローを追加。
- 引き継ぎ仕様の`GLB-008` / `DEC-020` と `NEXT-009` の進捗記録を追加。

**実測CI検証（GLB-008）**：実装コミット `c640ad06e5f55bf5a4112ba3bb5635751f2023a7` について、次のGitHub Actionsで全成功を確認。

- [Python run 42208333161](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42208333161)：3.11 / 3.12 / 3.13。新規23回帰テストを含む。
- [Windows run 42208333343](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42208333343)：PowerShell 3.11 / 3.13。
- [Blender run 42208333010](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42208333010)：Blender 4.4.3 / 4.5.15 / 5.2.1。合成GLBから作った修正候補と合成PythonのAST読み書きを照合して成功。
- [Windows kit run 42208333310](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42208333310) と [引き継ぎ run 42208332987](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42208332987) も成功。

**未検証範囲**：ユーザー私有アドオンの実際のBlender登録、プロパティの受信元オブジェクトとの結びつき、メッシュ形状への効果。上記は実装コミットに対する実測であり、後続ドキュメント更新のコード実行結果とは区別する。PRはドラフト、正式版`last_verified=v0.17.0`を保持。

## v0.18 開発中 — 2026-11-06（GLB-009: 受け手の構文上の関連）

- `cbdk/glb_property_usage.py` にクラスと匿名ソース別の `self.<prop>` 参照の集計を追加。ASTのみを読むため元アドオンの実行はなし。16件の表示サンプルと集計件数を切り離した。
- `cbdk/glb_property_map.py` に `same_class_reference_review` を追加。宣言クラスと一致するselfアクセス候補/他の受け手・別クラス・別ファイル由来の候補を分離し、`read/write/read_write/delete`を集計。クラス名匿名化の誤衝突を除外。
- `tests/test_glb_property_binding.py` に14件の回帰テストを追加。別クラス・別ファイル同名クラス・ローカルの`self`・動的getattr・19件以上の例示上限、プライバシーと非実行/非承認を確認。
- Blender 4.4.3/4.5.15/5.2.1の合成GLBと合成アドオン宣言を用いるCIに、同クラスself属性参照を見付けても実行時登録・geometry効果は未確認とするチェックを追加。
- STATE.json: `GLB-009`、`DEC-021`、`NEXT-009`更新。引き継ぎ文書を同期。

**検証状態:** 上記テストとCIのコードは追加済み。成功した最新実ジョブを確認するまではGLB-009を一部実装・未検証のまま管理。実ユーザーアドオン/GLBの動作、GUI、コードの自動修正は対象外。

### GLB-009 実測CI（2026-11-06）

実装コミット `2c000dad0980ee76562576ba63c0e7b568284748` に対して、GitHub Actions 5ワークフローの成功を確認。

- Python 3.11/3.12/3.13： [run 42210546730](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42210546730)。GLB-009の新規15回帰テストを含む。
- Windows PowerShell 3.11/3.13： [run 42210546742](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42210546742)。
- Blender 4.4.3/4.5.15/5.2.1： [run 42210546751](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42210546751)。合成GLBから候補を出し合成プロパティの同クラスself参照の集計と`binding_verified=false`等をチェック。
- Windows kit： [run 42210546861](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42210546861)。
- GitHub handoff： [run 42210546734](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42210546734)。

この実測に基づき、GLB-009を「実装済/Blender CI確認」としてSTATE/HANDOFFへ記録した。これは**実装コミット**の証拠。後続ドキュメント更新コミットの成功と混同しない。PR #25は未マージ・ドラフトで、正式リリース`last_verified`はv0.17.0のまま。実私有アドオンでの正しいクラス・受信実体・形状効果は未検証。

## v0.18 開発中 — 2026-11-06（GLB-011: モディファイア候補経路）

- `cbdk/glb_geometry_flow.py`に安全側の `MODIFIER_FIELDS` を追加。Blenderプロパティ式/直線的ローカル別名から `width`, `thickness`, `segments`, `levels`, `operation`, `object` などの属性代入・複合代入への構文上の経路を `possible_modifier_setting_assignment` として報告する。
- `tests/test_glb_modifier_flow.py`の専用15回帰テストを追加。既存メッシュ経路テストは維持。Blender3版CIの合成ソースに `modifier.width` と `modifier.thickness` の候補を追加してチェックする。
- 元アドオンソースはAST解析のみ。実Blenderモディファイアかどうか、モデルへの効果と適正値は未検証。候補を原因確定・自動修正には使わない。
- `GLB-011`と`DEC-023`をSTATE/HANDOFFに記録。

**検証境界:** 追加コード・テスト/CI定義のGitHub保存は完了。現headのCI成功を確認するまではGLB-011を一部実装・未検証とし、正式v0.17.0の`last_verified`を変更しない。

### GLB-011 CI結果（2026-11-06）

実装コミット b1a57e5789cacd5e1e07ae1ee17ce364fd4e1fb1 で、Python 3版（run 42214954563）、Windows 2版（42214954671）、Blender 4.4.3/4.5.15/5.2.1（42214954642）、Windowsキット（42214954657）、引き継ぎ（42214954600）の全ジョブが成功。GLB-011は実装済・Blender CI検証。実アドオンの型・ジオメトリへの効果は未検証。PRドラフト、正式v0.17.0は維持。

## v0.18 開発中 — 2026-11-06（GLB-012 頂点移動量の実測）

- CBDK自作の合成Blenderアドオンを用いた3条件（基準、球半径だけ変更、Bevel幅だけ変更）のGLB実験を定量化。
- `cbdk/parameter_experiment_metrics.py` 新規: 同一頂点順・有限XYZの比較に限り平均/最大局所移動距離、変化頂点数を算出。頂点数不一致・NaN・異常入力は拒否。一般GLBへの形状一致証明を明示的に否定。
- `scripts/blender_parameter_experiment_smoke.py` 改善: 生成直後・GLB再読込後の2段階で比較対象と無変更対照の頂点移動量を計測し、個別に影響対象だけが動いたことをアサート。レポートには生の頂点リストを含めず集計値のみ残す。
- `tests/test_parameter_experiment_metrics.py` に10件の純Python回帰テスト追加。`.github/workflows/blender-smoke.yml` で全Blender版の定量チェックを追加。
- 要件GLB-012、設計判断DEC-024、NEXT-010をSTATE.json/PROJECT_HANDOFF.mdへ追加。

**状態:** 最新コミットのCI合否を観測するまでGLB-012は部分実装/未検証。PR #25ドラフト、正式版v0.17.0維持。実ユーザーアドオンを実行しない。

### GLB-012 CI実測成功（2026-11-06）

実装コミット `04526f1ddd9f336df16d2841ccafc278cd8edf4f` に対する次の5ワークフローがすべて成功した。

- Python 3.11/3.12/3.13： [42220053230](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42220053230)（10件の新規定量測定テストを含む）。
- Windows 2環境： [42220053331](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42220053331)。
- Blender 4.4.3/4.5.15/5.2.1： [42220053332](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42220053332)。球の半径とBevel幅をそれぞれ変え、生成・GLB再読込後の頂点移動量と無変更対照を計測、すべて合格。
- Windows kit： [42220053222](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42220053222)。
- 引き継ぎ： [42220053158](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42220053158)。

GLB-012を実装済/Blender CI検証、NEXT-010をdoneとしてSTATE/HANDOFFに記録した。証拠はこの**実装コミット**の結果であり、後続の文書更新のCIとは分ける。PR #25はドラフトで、正式v0.17.0の`last_verified`は維持。任意GLBの表面距離や他者アドオンの効果は未検証。

## v0.18 開発中 — 2026-11-06（GLB-013 設定値上下の実測）

- `cbdk/parameter_direction.py`追加。固定された参考形状に対する基準・増加・減少の距離からレビュー専用`increase/decrease/inconclusive`を判定。不正値、同点、差が小さい状況は修正方向を断定せず、数値設定値と自動適用は返さない。
- `scripts/blender_parameter_experiment_smoke.py`のCBDK製合成アドオン実験を3→7 GLBへ拡張。球半径とBevel幅の既知参考値に対し、基準より増加プローブが近く、減少プローブが遠いことを、生成直後・GLB再読み込み後に比較。
- 両方向プローブについて無関係の部品の頂点変化件数が0であることを独立チェック。出力は距離集計のみで頂点XYZ生配列は保存しない。
- `tests/test_parameter_direction.py`に純Python回帰テスト11件追加。3版Blender CIで7 GLBの実出力と方向・無変更対照・非自動承認フラグをチェック。
- 要件GLB-013・設計判断DEC-025・タスクNEXT-011をSTATE.json/HANDOFFで管理。

**検証境界:** 最新PR headのCIを見てからGLB-013の検証状態を更新する。これは合成メッシュの頂点順不変な局所半径分布による実験であり、一般GLBの表面一致や実ユーザーアドオンの最適設定値の証明ではない。PRはドラフト、正式last_verified v0.17.0維持。

### GLB-013 CI実測結果（2026-11-06）

コード・仕様の検証コミット `e73f7eba0cd0bd5ceafacab53b64c397a7bd45a4` に対して、次の5ワークフローの全成功を観測した。

- Python 3.11/3.12/3.13: [run 42223468580](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42223468580)。方向判定11件＋頂点並び順に依存しない半径分布の追加5件を含む。
- Windows PowerShell 3.11/3.13: [run 42223468045](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42223468045)。
- Blender 4.4.3/4.5.15/5.2.1: [run 42223468513](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42223468513)。7種類の実GLBを出力し、参照を固定した上下プローブで増加側が改善、減少側が悪化、非対象部品は不変、GLB再読込後も方向が一致した。
- Windows kit: [run 42223468046](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42223468046)。
- GitHub handoff: [run 42223468069](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42223468069)。

初回のBlender5.2検証では、GLBインポートによる頂点番号の変更がindex-aligned局所距離を歪めて誤判定した。そこで**局所原点からの頂点半径をソートして比較する合成モデル専用の指標**に切り替え、変更後の3版Blender CIはすべて成功。頂点順不変である一方、別形状で同じ半径分布のケースは区別できず、一般GLBの形状同一性を証明しない。

Blender4.5.15の実測例（生成・再読込とも同じ値）：球半径は基準誤差0.4000002、増加0.2、減少0.6。Bevel幅は基準0.240685、増加0.1308848、減少0.2875242。いずれも非対象部品の頂点変化数は0。

これを根拠にSTATE/HANDOFFのGLB-013を実装済/Blender CI確認、NEXT-011をdoneへ更新。記録変更後のコミットのCI結果とは区別する。PR #25はドラフトで正式release last_verified v0.17.0維持。実ユーザーアドオン/私有GLBの実行とアップロード、自動パラメータ修正なし。

## v0.18 開発中 — 2026-11-06（GLB-014: 頂点順非依存の3D表面距離）

- `cbdk/glb_surface_distance.py` を新規実装。面積重み付きのサンプル点→相手三角形への最近接3D距離を双方向で集計。頂点順/三角分割は不一致でも可能。上限128面、24 Halton点/面。
- `tests/test_glb_surface_distance.py`に13件の単体テストを追加。同面の別三角分割/頂点順変更=ゼロ、Z+0.25、同外寸の中央開口、片方向では見逃しうる違い、異常数値・退化面拒否・完全一致を主張しないことを検証。
- 初回のPython CIが中央開口テスト失敗を検出。相関の強い12点/面のサンプリングが中央の穴を外していた。base2/3 Halton列24点/面へ変更後、Python3版CI成功を確認。
- `scripts/blender_surface_distance_smoke.py`を新規追加。CBDK自身が生成する4 GLBをBlenderで実書出/再読込し、異三角分割・開口・Z移動を比較するCIを3版Blenderで追加。
- `docs/GLB_SURFACE_DISTANCE.md`を作成。GLB-014/DEC-026/NEXT-012をSTATE/HANDOFFへ記録。

**制限:** 現時点は小規模でレビュー専用の合成モデル検証。小さな穴・内部空洞や大規模実モデルの比較を保証しない。Blender実機CIの成功を実測するまではGLB-014は一部実装/未検証。PRドラフト、正式v0.17.0維持。

### GLB-014 実測CI（2026-11-06）

変更コード/仕様書コミット `f7e9e114e3484da650044737189ae20395a53e74` に対し、次の全ワークフロー成功を観測した。

- Python 3.11/3.12/3.13: [run 42235161491](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42235161491)、新規13件の表面比較テストを含む。
- Windows PowerShell 3.11/3.13: [run 42235161515](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42235161515)。
- Blender 4.4.3/4.5.15/5.2.1: [run 42235161529](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42235161529)、合成4 GLBを実生成・再読込して計測。4.5.15で別三角分割の対称距離0、中央開口0.0081329、Z方向0.25差0.25を観測。各3版のテストは成功。
- Windows kit: [run 42235161511](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42235161511)。
- Durable handoff: [run 42235161506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42235161506)。

初期サンプリング12点/面は中心開口を見逃してPython CIで失敗。原因を確認し、相関の少ないHalton24点/面へ変更した後に3版Pythonと3版Blenderで成功。この実測からGLB-014はimplemented/blender_ci、NEXT-012はdoneとしてSTATE/HANDOFFへ反映した。これは実装/仕様書コードコミット`f7e9e114`の観測であり、後続の記録更新HEADのCIとは別に扱う。

**検証の限界:** 0のスコアは形状が数学的に完全一致する証明ではなく、小さな穴・内部空洞や大規模な実ユーザーGLBの形状比較は未検証。サンプル距離の最大値は真のHausdorff値ではない。PR #25はドラフト、正式リリースlast_verified v0.17.0のまま。

## v0.18 開発中 — 2026-11-06（GLB-015：BVH最近接面探索）

- `cbdk/glb_surface_distance.py` にAABB-BVHを導入。決定的な中央値分割で三角形を木構造に整理し、AABBの下界距離で遠方の三角面候補を省く。採用面では従来同様の正確な点→三角形距離を算出。
- 1メッシュの上限を128→512三角面へ拡張。`triangle_distance_evaluations` と `brute_force_evaluations` を方向別に記録。これは計算回数の削減指標であり、実測時間の高速化ではない。
- `tests/test_glb_surface_bvh.py` を新規10回帰テスト追加。総当たりと結果一致、400/512面、4分の1未満の評価回数、面順・向き変更、距離の非承認などをチェック。
- `scripts/blender_surface_distance_smoke.py` にCBDK製の256三角面`grid_256.glb`を追加。4→5種類の合成GLBを生成/再読込して距離0とBVHによる計算回数削減を調べる。Blender 4.4.3/4.5.15/5.2.1 CIへ統合。
- GLB-015 / DEC-027 / NEXT-013をSTATE.json/HANDOFFに記録。手引き文書をBVH・上限512・5GLBに更新。

**状態:** 最新コミットの実CIの成功を確認するまで一部実装・未検証。512面は初期の128面から4倍の上限だが、一般的な大規模モデルへの適用能力を保証しない。PRドラフト、正式v0.17.0を維持。

### GLB-015 BVH高速化・実測CI成功（2026-11-06）

実装・仕様書コミット `bcef8572994065f73d05e2e9c37245d64a13035e` に対して、次のGitHub Actions 5ワークフローすべてがsuccess。

- Python 3.11/3.12/3.13: [run 42238115233](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42238115233) — BVH/総当たりの結果一致、400/512面の上限、別順序、非承認など新規10件を含む。
- Windows PowerShell 3.11/3.13: [run 42238115886](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42238115886)。
- Blender 4.4.3/4.5.15/5.2.1: [run 42238114860](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42238114860) — 合成GLB5種類を生成・再読込し、256面の`grid_256.glb`を使って誤差0と総当たり比較回数25%未満を全バージョンで検証。
- Windows kit: [run 42238115035](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42238115035)。
- Durable handoff: [run 42238115141](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42238115141)。

Blender4.5.15の`CBDK_SURFACE_DISTANCE_PASS`実機ログにて、**256面、総当たりの精密距離計算1,572,864回→BVH方式49,152回（32分の1、96.875%削減）**、同一表面距離0を観測。他の合成条件も従来同様、別三角分割誤差0、開口誤差0.0081329、Z+0.25誤差0.25を維持。

これは**精密三角形距離の計算回数**の削減を示すもので、ウォールクロック時間での32倍速・大規模実GLBの完全対応を証明しない。表面サンプリングの粗さ、密閉空洞、真のHausdorff距離、ユーザー私有GLBなどは未検証。

STATE/HANDOFFのGLB-015を`implemented/blender_ci`、NEXT-013を`done`へ更新。上記は実装/文書コミットのCIであり、その後の記録更新コミットは別CIで検証する。PR #25ドラフト、正式v0.17.0維持。

## v0.18 開発中 — GLB-016: ウォールクロックの実測

- `cbdk/surface_benchmark.py`を追加。ウォームアップ後にBVH・総当たりを交互順序で計測し、繰り返し3回の実行時間中央値をmsで保存する。BVH木構築・表面サンプリングを含む。64面では同一入力のスコア一致を確認し、512面ではBVHのみを観測。最小/最大時間、面数、精密三角形距離の評価回数も記録する。
- `tests/test_surface_benchmark.py`に10回帰テストを追加。大きな入力で総当たりを許可しない安全制限、正常/不正入力、測定時間の非移植性、非公開データを出さないことを検証する。
- `scripts/blender_surface_distance_smoke.py`のCBDK製合成fixtureを5→6 GLBへ拡張、512三角面のGLBを実出力・再読込。既存256面BVH計算回数の検証も維持。
- `.github/workflows/blender-smoke.yml`でBlender 4.4.3/4.5.15/5.2.1上、64面BVH/総当たりのタイミング記録、512面BVHのみのタイミング、スコア0・速度比をCI閾値としないことをチェック。
- 正本STATE.jsonにGLB-016、DEC-028、NEXT-014を追加してPROJECT_HANDOFFと同期。実測CIの合否は現在のコミットが完了した後に記録する。

**検証境界:** CPU・Blender・ランナー負荷が異なるとミリ秒や速度比は変わる。計算回数32分の1と実行時間32倍速は別概念。512面は一般的な高密度メッシュへの実用性を保証しない。PRはドラフト、正式v0.17.0は保持。

### GLB-016 実時間比較結果（実装コミット 9581ab20、2026-11-06）

CBDK製の6種類の合成GLBを実際に書き出し/再読み込みするBlender 4.4.3・4.5.15・5.2.1のCI [run 42240589340](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42240589340) はすべて**成功**。64面の共通入力でBVHと総当たりのウォームアップ後3回の実行時間中央値（ms）を測った。512面ではBVHの時間のみを計測。

| Blender | 64面BVH | 64面総当たり | 512面BVH |
|---|---:|---:|---:|
| 4.4.3 | 35.510505ms | 161.156313ms | 352.050953ms |
| 4.5.15 | 19.356758ms | 86.027068ms | 192.798623ms |
| 5.2.1 | 32.467850ms | 149.716417ms | 321.247609ms |

両方式は64面の表面誤差について同じ数値を返し、512面合成GLB同士のサンプル距離は0。既存の256面での精密三角形距離回数削減と、中央開口・高さ変位の検査も維持。Python [run 42240590020](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42240590020)・Windows kit [42240588950](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42240588950)・handoff [42240588940](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42240588940) も成功。Windows PowerShell [42240588999](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42240588999) も成功。

3バージョンでBVHの64面処理時間が総当たりより短いことを**観測**した。ただしCIランナーのCPU/負荷に依存して数値が変動し、全PCへの性能保証や実製品用大規模GLBの処理能力は意味しない。速度比をCIの合否閾値にはしていない。正本STATE/HANDOFFでGLB-016をimplemented/blender_ci、NEXT-014をdoneへ更新。v0.18ドラフトPR #25内の作業で、正式v0.17.0のlast_verifiedは変更なし。

## v0.18 開発中 — GLB-017: 粗8点→選択面48点の多解像度比較

- `cbdk/glb_multires_surface.py`新規。粗8 Halton点/面、差分の疑いがある最大8面＋面積上位の探索2面を48点まで増やし、両方向のサンプル距離を集計。BVHは再利用し、追加の精密距離評価回数と変更面数を出力。上限512面/メッシュを維持。
- `tests/test_glb_multires_surface.py`に13回帰テストを追加。従来の固定24点では見逃す幅0.44の中央開口を、48点の選択精査が検出するケース、異三角分割・順序入替・高さ変位、探索枠、上限・非公開入力拒否を確認する。
- `scripts/blender_surface_distance_smoke.py`へ`with_narrow_hole.glb`を追加し合成6→7 GLB。新旧方式の差をBlender4.4.3/4.5.15/5.2.1で実出力/再読込して検証するCIを追加。512面・BVH実時間テストは残す。
- GLB-017 / DEC-029 / NEXT-015を正本STATE.jsonとPROJECT_HANDOFF.mdへ記録。

**境界:** 完全形状一致の証明ではない。サンプルがない面や小穴・内部空洞はまだ見逃し得る。最新headのCI実測が揃うまで一部実装・未検証、PR #25ドラフト・正式last_verified v0.17.0維持。

### GLB-017 多解像度表面比較・実測CI成功（2026-11-06）

実装・仕様書コミット `4c7248c853047b1f21088e01441a6c5fed9ca4b2` の5ワークフロー全成功を観測した。

- Python 3.11/3.12/3.13: [run 42244257474](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42244257474) — 13件の新規多解像度回帰テストを含む。
- Windows PowerShell 3.11/3.13: [run 42244257438](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42244257438)。
- Blender 4.4.3/4.5.15/5.2.1: [run 42244257499](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42244257499) — 自作合成GLB7種を実生成・再読込。**幅0.44の中央開口**で従来固定24点/面のサンプル最大距離0、新方式粗8点/面も0、精査で選んだ面を48点/面まで増やすと最大距離**0.0657466**。3版すべて同値。
- Windows kit: [run 42244257461](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42244257461)。
- Durable handoff: [run 42244257445](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42244257445)。

本成果は**限られた合成モデル**における見逃しを改善した実測であり、完全な穴の網羅性、密閉空洞やトポロジ正しさは保証しない。精査しなかった面にある異常は依然見逃し得る。GLB-017をimplemented/blender_ci、NEXT-015をdoneとしてSTATE/HANDOFFに記録した。これは4c7248c8のCI結果であり、後続の記録更新コミットのCIは別途観測。PR #25はドラフト、正式v0.17.0のlast_verifiedは変更なし。

## v0.18 開発中 — GLB-018: 幾何ヒントを使った精査の優先順位

- `cbdk/glb_feature_priority.py`を追加。メッシュ内の境界/外寸内にある境界、面同士の折れ角、面積が相対的に小さい領域、共通頂点が多い領域、非多様体の疑いを**確認候補**として抽出。
- `cbdk/glb_multires_surface.py`で、粗8点で差が出た面は最優先のまま、追加探索2面のうち1面を上記ヒントから、1面を面積順から選ぶ。旧方式`feature_aware=False`も維持。精査48点、BVH、上限512面は継続。
- `tests/test_glb_feature_priority.py`に新規13件の回帰テスト追加。大きな板に埋もれた小部品の穴、鋭角・外寸内部の境界、細かい三角形、別三角分割・頂点順、実行/公開/自動承認なしを検証。
- Blender合成GLBに`panels_filled.glb`/`panels_narrow_hole.glb`を追加し9種を実出力/再読込するCIを追加。旧面積方式と新特徴方式を同一入力で比較する。
- 正本STATE.jsonにGLB-018/DEC-030/NEXT-016を登録して、PROJECT_HANDOFFを同期。

**境界:** 幾何特徴は優先候補であり欠陥の確定ではない。新方式は小部品を優先できても、未選択領域の穴を見逃し得る。公開CIにユーザーの非公開GLB・アドオンは入れず、自動修正もしない。最新headの実CIを確認するまではGLB-018は部分実装/未検証。v0.18ドラフト、正式v0.17.0維持。

### GLB-018 特徴ヒント優先・合成9 GLB実測成功（2026-11-07）

コード・仕様・引き継ぎコミット `676e92f8cc4ad48774ea6e0702710576fe97a286` に対して、5つのGitHub Actionsワークフローは**すべて成功**した。

- Python 3.11/3.12/3.13: [42246918798](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42246918798)（新規13件の特徴優先回帰テスト含む）。
- Windows PowerShell 3.11/3.13: [42246918818](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42246918818)。
- Blender 4.4.3/4.5.15/5.2.1: [42246918883](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42246918883)。CBDK製合成GLB9種を実際に生成・再読み込み。大型板2枚と中央小部品の開口差は、面積のみを追加調査する旧方式で**サンプル最大距離0**、特徴優先方式では**0.0657466**。3版のログで同値を確認。
- Windows kit: [42246918868](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42246918868)。
- Durable handoff: [42246918953](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42246918953)。

既存の7 GLB検証、GLB-017の狭穴検出、256/512面BVHの精密距離・ウォールクロック測定、非公開データを実行/公開しないチェックも成功。GLB-018を`implemented/blender_ci`、NEXT-016を`done`としてSTATE/HANDOFFに反映した。

**結果の解釈**：これは特定の自作合成モデル上での改善証拠。開放辺が本物の穴かどうか、粗いサンプルの未調査箇所に欠陥がないこと、すべての小部品/内部空洞が見つかることを意味しない。計算優先順位のヒューリスティックであり完全な表面一致は未証明。上記は実装コミットのCIであり、後続の記録更新コミットの再CIとは区別する。v0.18はドラフトPR #25、正式v0.17.0の`last_verified`は保持。

## v0.18 開発中 — GLB-019（実2GLB表面比較への統合）

- `cbdk/glb_surface_pipeline.py`新規。ローカルGLB2個の静的preflight、外部URI・大型入力拒否、factory-startup/disable-autoexecで固定Blenderスクリプト実行。結果JSONのschema/kind/status/privacy flags/最大サイズを検証し、不正な結果を採用しない。
- `scripts/blender_glb_surface_review.py`新規。各GLBを別の初期化シーンでインポートし、全メッシュのworld-space三角形を比較。既存GLB-014の固定24点BVH距離＋GLB-017/018の特徴優先多解像度をまとめて計算し、集計のみ出力。512面を超えた場合は`skipped`、一致や合格とは呼ばない。
- CLI `glb-surface-review`追加。既存`glb-regression`には`--surface-review`（明示任意指定）を追加。従来の`comparison.json`/`diagnosis.json`/`repair_plan.json`とは別に`surface_review.json`を出力し、`passed_is_metadata_only`を返す。
- `tests/test_glb_surface_pipeline.py`に新規12件と`tests/test_glb_regression.py`に新規3件の回帰テスト追加。Blender 3版CIで自作合成GLBを読み込む新CLI・旧regression opt-inの統合試験を追加。
- 正本STATE.json/PROJECT_HANDOFF.mdにGLB-019、DEC-031、NEXT-017を登録。利用手順と制限は`docs/GLB_SURFACE_PIPELINE.md`へ保存。

**未検証境界:** GitHub CIの本head結果を観測するまでGLB-019を部分実装/未検証とする。512面超の実GLB、個別オブジェクト名対応、未知GLBのBlender輸入リスクゼロ化、内部空洞などは未対応。ユーザーの非公開GLBを公開GitHub/CIに含めない。v0.18 PR #25はドラフト・正式last_verified v0.17.0を保持。

### GLB-019 実GLB比較の統合検証（2026-11-07）

**実装コミット `ec13972f45f73617536d718491eee57f98a21e26` で観測した結果:**

- Python 3.11/3.12/3.13: [run 42257317519](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317519) **成功**。12件の新しいpreflight/レポート/サブプロセス安全回帰テストと、3件の既存回帰への任意統合テストを含む。
- Blender 4.4.3/4.5.15/5.2.1: [run 42257317535](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317535) **3版すべて成功**。CBDK製の実GLB `filled_main` vs `with_open_hole`で`sampled_difference_detected`、`filled_main` vs `filled_other`で`no_difference_observed_at_samples`を新CLIから確認。元の`glb-regression --surface-review`との共存もBlender4.5.15で検証した。
- Windows kit: [run 42257317475](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317475) **成功**。
- GitHub durable handoff: [run 42257317601](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317601) **成功**。
- Windows PowerShell: [run 42257317637](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42257317637) は後続コミットによる新たなCI起動で**cancelled**となり、上記コミット単体での成功は未確認。先行するWindowsテストのパス区切り問題はプラットフォーム非依存な`Path(...).name`チェックに修正した。

`glb-surface-review` は非公開モデルをネットワークへ送らず、Blenderの局所読み込みで比較する。外部URI・過大入力を拒否し、512面超は`skipped`、完全一致の証明はしない。集計結果のみJSONへ残す。

この証拠に基づきSTATE/HANDOFFのGLB-019を**implemented / blender_ci**、NEXT-017を**done**に更新。後続の記録更新HEADのCI結果とは区別する。正式release last_verified v0.17.0維持、PR #25はドラフト。

### GLB-019 最終再CI（2026-11-07）

実装と記録のコミット`5b6196a59f86318128c768507fea53237e3a6e11`では、**全5ワークフローがsuccess**：Python3版 [42258076642](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42258076642)、Windows PowerShell2版 [42258076781](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42258076781)、Blender4.4.3/4.5.15/5.2.1 [42258076658](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42258076658)、Windows kit [42258076681](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42258076681)、引き継ぎ [42258076822](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42258076822)。旧Windows専用テストのパス区切り前提は修正済み。

`glb-surface-review`の2種類の実GLBペアで、開口の検出と同じ形の別三角分割に差がないことを確認。GLB-019は実装済/Blender CI確認済み。報告の`status=review_only`は「観測した形状差のサンプル結果」であり、0も完全一致・内部空洞なし・安全な自動修正を意味しない。512面超はskippedであり大規模GLBの自動解析は今後の課題。これはコミット5b6196a5の実測であり、後続の文書記録コミットのCIとは区別する。PR #25ドラフト/正式v0.17.0維持。

## 2026-11-07 GLB-020 — 形状差分の3D可視化（試作実装）

- `cbdk/glb_diff_colors.py`: 既存の安全制限付きBVH距離測定により、元の三角面順を保って参照→生成／生成→参照の方向ごとに24点サンプル最大誤差を集計。共有AABB対角線1%未満=灰、1〜5%=黄、5%以上=赤。サンプル密度・見逃し制約を明示。
- `cbdk/glb_diff_visualize.py`, `scripts/blender_glb_diff_visualize.py`: オプトインの`glb-diff-visualize`CLIから、固定Blenderスクリプトだけを実行し2つの着色GLBと生座標なし`review.json`をローカル新規フォルダに生成。元GLB・私有アドオンは変更せず、レビュー専用。
- `tests/test_glb_diff_visualize.py`: 同一形状／位置ずれ／面順／無効入力／プライバシー／上書き防止／ランナー検証のテストを追加。Windowsパス区切りのテスト差異を修正。
- `.github/workflows/blender-smoke.yml`: CBDK自作の合成2組のGLBを色分け、統計検証後、着色出力をBlenderへ再インポートして材料を確認。既存GLB-019の計測と併走。
- 実装コードのテストSHA `01fff17403b931390c1813dcce4577363eb9077f` で[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143616) / [Blender 3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143956) / [Windows kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143564) / [handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143732) **成功**。Windowsテストは同SHAでパス区切り差異により失敗（[run 42264143652](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42264143652)）。その後コミット `91e8b6a2` でテストのパス扱いを修正し、最新HEADのCI再確認を行う。
- **ステータスは一部実装**。色付きGLB書き出しは動いたが、オブジェクト別選択・連動比較ビュー・未測定部の表示・より大きな実ユーザーGLBは未実装。正式リリースはv0.17.0、ドラフトPR #25維持。

## 2026-11-07 GLB-020 — 匿名部品別カラー差分（第二段階）

- `scripts/blender_glb_diff_visualize.py`: 初版の「全部の面を1メッシュに統合」を改良。入力GLBの個々の**非空メッシュ**を保持して、`CBDK_Reference_Part_001` / `CBDK_Candidate_Part_001` のような匿名の部品に分けて着色GLBを出力。元の部品名は出力しない。
- `cbdk/glb_diff_colors.py`: `summarize_anonymous_parts` を追加。部品ごとの赤/黄/灰の面数と三角形数を集計し、入力順・合計・最大64部品の整合を検証。部品名・元頂点座標・私有ファイルパスはJSONに保存しない。
- `cbdk/glb_diff_visualize.py`: 返却JSONの部品ID順、面数、集計合計、匿名化フラグ・64部品制限をチェック。`cross_file_part_identity_proven=false` を固定して、双方の同じ番号が対応部品だと誤認しない。
- `tests/test_glb_diff_visualize.py`: 部品集計や不正な部品構造のPythonテスト。`scripts/blender_make_glb_diff_parts_fixture.py` で意図的に非公開風の名前を持つ2部品の合成GLBを生成し、`scripts/blender_verify_glb_diff_visualize.py` で別部品・色付け・元名称の非継承を実機再読込で確認するCIを追加。
- CI対象: コード・テストSHA `7365828b287e08046d66d62fc01c5fcfc2457fed`。Python/Windows/Blender実機は全5系統成功を確認。`[skip ci]`文書コミットは同SHAのテスト結果として扱わない。
- Code SHA `7365828b287e08046d66d62fc01c5fcfc2457fed`: [Python 42265921528](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921528), [Windows 42265921533](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921533), [Blender 4.4.3/4.5.15/5.2.1 42265921506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921506), [kit 42265921516](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921516), [handoff 42265921493](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921493): **all five completed/success**.
- **部分実装を維持**：出力GLBの部品はBlenderで個別に選択・非表示可能となる想定だが、元の対応部品を自動で結び付ける機能、同期カメラ、未測定領域の厳密表示、512三角形を超えるデータは未対応。安全なローカル比較と公開GitHubへの非公開モデル混入防止を優先。


## 2026-11-07 GLB-020 — ローカルHTMLの3D連動比較（第3段階・検証中）

- `cbdk/glb_diff_viewer_template.html` に外部依存のない左右2画面を追加。マウスドラッグで両方の3D視点を同時回転、Shift+ドラッグで平行移動、ホイールでズーム。各画面は匿名部品を独立選択でき、灰色の面を隠せる。左右の共通中心・縮尺を維持し、位置ズレが自動正規化で隠れないようにする。
- `cbdk/glb_diff_viewer.py` は有限・最大512三角面/GLBの**数値形状のみ**をHTMLに埋め込み。JSONレポートには生頂点や元部品名を含めず、HTML自体は非公開の派生ジオメトリを含むことを明示。
- `scripts/blender_glb_diff_visualize.py` が従来の着色GLB2件・集計JSONに加えて`compare_viewer.html`を作成。`cbdk/glb_diff_visualize.py`が出力存在/フラグ/容量/テンプレートを検証、CLIに閲覧パスを表示。`pyproject.toml`でテンプレートをパッケージ化。
- テスト: PythonでJSON埋め込みとプライバシー/安全上限・HTML構造を検証。Blender3版CIの合成2部品GLBでHTML生成とJSON安全フラグ、NodeでインラインJavaScript構文を確認する追加ゲートを用意。
- **未完了**: ブラウザ実機での回転・部品切替・ズームの操作検証、Canvas 2Dの奥行き描画の正確さ、正確なクロスGLB部品対応、未解析領域の明示、大規模な実データ検証。完成扱いではなく一部実装を継続。正式v0.17.0/ドラフトPR #25は維持。

### GLB-020 第3段階 CI実測（2026-11-07）

- 実装・テストSHA `b5d1d27f5e7834fa22faeefb02792091c1ac87d0`：Python [42268089086](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268089086)、Windows [42268088883](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088883)、Blender 4.4.3/4.5.15/5.2.1 [42268088779](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088779)、Windowsキット [42268088823](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088823)、引き継ぎ [42268088869](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088869) **全成功**。これはHTML生成とJS構文のCIであり、ブラウザ実機の操作試験ではない。
- `compare_viewer.html`はローカルでの2画面比較用。**ブラウザ操作・表示の正確さ・任意実ユーザーGLBの検証は未実施**。`GLB-020`は引き続き一部実装、v0.18 PR #25はドラフト。

## 2026-11-07 GLB-020 — 空間的な部品対応候補とChromium実操作CI（第4段階）

- \`cbdk/glb_part_match.py\`：各GLBの匿名部品のワールド座標AABB中心・寸法・三角形数から、参照→生成の**部品対応候補**をヒューリスティックに推定。相互最近傍・距離上限・第2候補との差の閾値を満たすものだけ\`suggested\`、同位置等の区別不能は\`ambiguous\`、遠すぎれば\`unmatched\`。同一部品の確定、コード修正、自動パラメータ調整は禁止。
- 既存のローカルHTML比較画面に「候補を右側に表示」ボタンを追加。ユーザーが押した場合にだけ右側の部品表示が切り替わり、曖昧な場合は無効。JSONには候補の匿名ID・集計スコアのみを記録し、生座標・元部品名・私有パスは含めない。
- \`tests/test_glb_part_match.py\` に部品の順番入替、同位置の曖昧性、未対応部品、軽微移動、異常データの回帰テストを追加。既存の\`tests/test_glb_diff_visualize.py\`も候補表示・安全フラグを確認。
- \`scripts/glb_viewer_browser_fixture.py\` でCBDK自作の入替2部品モデルからテストHTMLを生成。Playwright/Chromiumによる\`scripts/glb_viewer_browser_smoke.mjs\`で左右のカメラ連動、ズーム、候補ボタン、灰色面表示、HTTP通信禁止をチェックするCIを追加。Ubuntu 26.04非対応のPlaywrightブラウザインストーラ問題を避けるため、ブラウザCIランナーをUbuntu 24.04に固定。
- **開発中・リリースはまだv0.17.0。** ブラウザでの実操作検証とBlender3版CIの最新版SHAの結果が出たら、状態台帳・Notionに正確な成功/失敗を追記。部品の因果・一致判定、未知領域、大規模GLBは未解決。

### GLB-020 第4段階：CI検証結果（2026-11-07）

コードSHA `72e9bd4e4ad2cb9b9716ee0cb5ea10de60cd779e` では、[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183982)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184368)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184086)・[Windowsキット](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184021)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183990)・[Chromium実ブラウザ操作](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183979)が**全6系統success**。

Chromium CIはUbuntu24.04でPlaywrightを導入し、CBDK自作の合成2部品モデルから生成したHTMLで、左右回転/ズーム・部品候補の手動表示・灰色面切替・HTTP通信の不発生・JS例外なしを確認。Ubuntu26.04でのPlaywright1.56.1インストール不対応による初回CI失敗はUbuntu24.04固定で解消。**部品の本当の対応関係や任意の実GLB精度はまだ未検証**。GLB-020は一部実装を維持。

## 2026-11-07 GLB-020 第5段階：追加測定で見逃しに注意する面を可視化

- `cbdk/glb_sampling_audit.py` を追加。従来の24点/三角面に加え、重複しないHalton24点でも相手のBVH面までの距離を調べる。追加測定で観測誤差が共有AABB対角線の0.5%以上増えるか、灰/黄/赤の閾値を横断した面を**「サンプリング感度あり」**とする。
- ローカルの`compare_viewer.html`では、該当面に**紫色の枠**を重ねる。チェックボックスから表示切替が可能。通常の面の赤/黄/灰の色は従来24点の指標を維持。
- `review.json`はセンシティブな面の総数と匿名部品別の集計のみ保存。個別のフラグは**元の3D形状が含まれるローカルHTML側のみ**。公開GitHub/Notionには私有モデルを書き出さない。
- `tests/test_glb_sampling_audit.py`と既存テストを更新し、異常数値・部品境界・HTMLの不正フラグを拒否する。Blender CIは集計・フラグの保守的な定義を確認し、Chromiumの合成HTML試験は紫枠表示切替による描画変化を検査。
- **重要**：紫枠がない部分も未観測領域が残る可能性がある。これは未知部分の完全な特定でも、元アドオン設定を自動修正する機能でもない。GLB-020は一部実装のまま、正式v0.17.0とドラフトPR #25を維持する。

### GLB-020 第5段階CI結果（2026-11-07）

コードSHA `38057b1da49eeb61020664c4923ced2b2bad8406`： [Python 42279824321](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824321)、[Windows 42279824307](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824307)、[Blender 4.4.3/4.5.15/5.2.1 42279824378](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824378)、[Windows kit 42279824398](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824398)、[引き継ぎ 42279824427](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824427)、[Chromium GUI 42279824304](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824304) **全6系統success**。

合成GLB上で追加24点の数値監査と匿名部品別統計の整合が確認できた。ヘッドレスChromiumで、人工的に感度フラグを付けた合成ビューの紫枠表示切替を実際に検証。**フラグなしを全域検証済みと主張しない**。私有大規模モデル/小穴・空洞の完全検出/真の部品同一性は未検証。GLB-020の一部実装を維持。

## 2026-11-07 GLB-020 第6段階 — 境界エッジの補助解析

- `cbdk/glb_boundary_audit.py` を追加。各匿名メッシュ部品の三角形を世界座標で近接統合し、1面だけが接する境界エッジ、2面が共有する辺、3面以上が共有する非多様体候補を**数値として観測**する（512面/64部品の上限維持）。
- `cbdk/glb_part_match.py`：位置や大きさが似ていても境界の有無・非多様体の観測が食い違う場合、単独の対応候補を確定的に提示せず `ambiguous` に降格する。`topology_review_required`を明示し、候補が複数・不在の場合と区別する。
- `scripts/blender_glb_diff_visualize.py` / `cbdk/glb_diff_visualize.py` / `cbdk/glb_diff_viewer.py`：参照・生成の匿名部品別エッジ集計を`review.json`に加え、ローカルHTMLの部品選択に境界数と注意表示を追加。JSONには元頂点、元部品名、パスは含めない。
- `tests/test_glb_boundary_audit.py` / `tests/test_glb_part_match.py`：閉じた四面体0本、1面欠損の四面体3本、非多様体候補、近接頂点、部品不整合入力をテスト。
- `scripts/blender_make_glb_boundary_fixture.py` と Blender CI：自作の閉/開四面体を実GLBとして書き出し、再読込して境界数と、対応候補を曖昧と判定することを検証。Chromium CIで部品セレクターの境界数表示も確認。
- **注意**：境界エッジ0本は閉曲面や穴無しの証明ではない。近接座標の統合は数値近似であり、意図的な開口とバグは区別できない。対応部品の同一性・内部空洞・完全体積一致も未検証。正式v0.17.0、ドラフトPR #25、GLB-020一部実装を維持。詳しくは`docs/GLB_BOUNDARY_AUDIT.md`。

### GLB-020 第6段階 — 検証記録

コードSHA `2cec6c99082107a4f2a65459f36f641b189f3bc5` の [Python 42284401645](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401645)・[Windows 42284401719](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401719)・[Blender 4.4.3/4.5.15/5.2.1 42284401757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401757)・[Windowsキット 42284401594](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401594)・[引き継ぎ 42284401833](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401833) は全て success。 [Chromium 42284401610](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401610) は別途結果確認中。

closed/open 四面体のBlender3版での差分と、元ソースを公開しない匿名集計が確認できた。これをもってGLB-020全体を完成とはせず、手動レビュー・モデルの細部や本当の部品同一性は未解決のまま維持する。

## 2026-11-07 GLB-020 第7段階 — 境界線の位置を3D比較画面に表示

- `local_boundary_segments`で座標近接統合後の**境界エッジ両端の世界座標**を、匿名部品番号付きでローカル画面専用に出力。既存の境界集計との本数一致を必須とし、最大512三角面由来の1536線分に制限。公開レポートには座標を出さない。
- `compare_viewer.html`に水色の境界線オーバーレイと表示切替を追加。参照/生成の独立した部品選択・同期カメラに追従。Canvas 2Dの描画は**奥側の線も見えるX-ray的な近似**で、正確な遮蔽判定や実物の穴位置の証明には使わない。
- `tests/test_glb_boundary_audit.py`と`tests/test_glb_diff_visualize.py`で閉/開四面体の線分座標・非公開HTMLの保持・匿名部品ごとの分離を検証。Chromium GUIで左右の境界線の表示切替と、Blender3版CIでGLB由来HTMLの境界線0対3本を検証するゲートを追加。
- これは**形状の検査を補助する表示**であり、内部空洞の一致・小穴の完全検出・元アドオンの自動修正は行わない。GLB-020部分実装、GLB-021/022未実装、正式版v0.17.0のまま。

### GLB-020 第7段階・CI検証結果（2026-11-07）

テスト対象のコードSHA `2a2bc8c33aaf4d11811e7892a8bbc51542b316b4`： [Python 42286544157](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544157)、[Windows 42286544061](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544061)、[Blender 4.4.3/4.5.15/5.2.1 42286543992](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543992)、[Windowsキット 42286543968](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543968)、[引き継ぎ 42286543977](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543977)、[Chromium実GUI 42286544018](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544018) **全6系統成功**。

合成GLBで「閉四面体の推定境界線は0本、1面欠損では3本」を実表示用のHTMLデータでも検証。実Chromiumで線のオン/オフ・左右両方の描画変化を確認。試験用HTMLはCBDK合成モデルのみで私有GLBを含まない。第7段階もレビュー補助の部分実装であり、v0.18正式マージ・リリースは行わない。

## 2026-11-07 — GLB-020レビューMVP総合受け入れ（スコープ凍結）

- BlenderでCBDK自作の3部品（12分割中空ソケット、8三角形ボール、端面付き12分割軸）を作り、**正常・開口狭窄・ボール移動・ソケット面欠損**の4条件でGLB実出力→読込→比較→集計検証。
- 初回の「正常なのに開放境界がある」失敗はテスト形状の軸が開いていたことによる。軸の端面を修正し、**正常モデルの誤検出0**を確認。変更した部品を検出し、変更していない他部品は誤検出しない条件も成功。
- ソケット上端リップの2三角面を抜くと**観測境界4本**を検出。ソースGLBのSHA256一致、私有データ非含有の集計JSON、生成HTML/GLBのローカル扱いも確認。
- 最終テスト対象コード SHA `db33ce4242bbe98b3c5f9ac43d89bf21c3657089`：
[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898364)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898499)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898512)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898604)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898325)・[Chromium実GUI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898701) **全6系統成功**。
- スコープ判断：`GLB-020`は**レビューMVPの受け入れ合格**として細かな機能増築を凍結。ただし実GLB・完全精度が未保証なので機能全体は`partial`を維持。`NEXT-018`を`done`、**次は`GLB-021`の改善候補レビュー連携**を優先し、その後`GLB-022`へ。詳細 [受け入れ条件](GLB020_MVP_ACCEPTANCE.md)。

## 2026-11-07 GLB-021 第1段階 — 形状差分からASTプロパティ候補へ接続

- `cbdk/glb_visual_property_review.py`と`glb-visual-property-review` CLIを追加。GLB-020の匿名部品別の赤/黄の観測数と境界エッジ数を、既存のASTプロパティ宣言・参照・形状フローと**レビュー専用で照合**。
- 候補名は汎用設定ファミリに限定。使用者が`--role part_003=socket`などを明示した場合だけ、その役割に紐付く設定名を候補に含める。ソースの実行・修正、設定値の推測、原因や部品の真の対応の断定は禁止。
- コマンド出力はignored `reports/latest/*.json` の新規ローカルファイルのみ。標準出力は匿名集計の概要に限定し、候補プロパティ名・元アドオンパス・設定値を漏らさない。
- Pythonテストで悪意のある安全フラグ/異常なJSON/偽の部品役割/元ソース副作用の非実行/出力非上書きを検証。Blender3版ではCBDK合成の正常/ソケット狭窄/ボール移動/リップ欠損の4比較結果を実際にGLB-021へ入力する。
- コードSHA `8c51a867415738dcca6616a4a197b62a105075e5`： [Python 42292708122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708122)、[Windows 42292708128](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708128)、[Blender 4.4.3/4.5.15/5.2.1 42292708248](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708248)、[Windows Kit 42292708114](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708114)、[引き継ぎ 42292708111](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708111)、[Chromium実GUI 42292708124](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708124) **全6系統success**。
- **GLB-020のMVPスコープ凍結は維持**。GLB-021は`partial`、次の`NEXT-019`は`in_progress`、GLB-022は未実装、正式版v0.17.0は変更しない。詳細： [GLB-021仕様](GLB021_VISUAL_PROPERTY_REVIEW.md)。

## 2026-11-07 GLB-021 第2段階：非公開の人間向けレビューシート

- `cbdk/glb_visual_review_markdown.py` を追加。GLB-020からの匿名差分（黄/赤面数・観測境界辺）と、ASTの宣言名一致/参照件数/構文上の形状処理経路を**「観測」「候補」「未確認」の区別付き**の日本語Markdownで表示する。
- 新しいCLI `python -m cbdk glb-visual-property-review ... --markdown` は、元のJSONに加えて、同名の`.md`をローカルのignored `reports/latest`に新規作成。Markdownにも候補名と宣言行が含まれるので**私有データ**として扱い、GitHub/Notionへのアップロードは禁止。
- 正常合成GLB（候補0件）、開口狭窄、ボール移動、リップ欠損に対し、コード実行/値の自動適用をせずに人手のチェックリストを生成。公開パス・元ソース本文/既定値の不掲載、既存ファイル非上書き、シンボリックリンクや不正な安全フラグ拒否を回帰テストへ追加。
- 人の役割ラベルは未確認。部品の本当の対応・設定の実行時登録・差分の原因や修正値は**未証明**。`GLB-021`は一部実装、`GLB-022`は未実装、`GLB-020`の細かな機能増築は引き続き凍結。
- 詳細：[GLB-021のレビューシート仕様](GLB021_VISUAL_PROPERTY_REVIEW.md)。検証証拠は対象コードのSHAとGitHub Actionsの結果を確かめた後で別途追記する。

## 2026-11-07 GLB-021 第2〜3段階：日本語レビューシートの確認順とCI実測

- GLB-020の差分集計とAST設定名候補を、ローカル`reports/latest/*.md`の人手向けチェックシートへ整理。コードの宣言・参照・形状処理への構文上の経路を分けて表示。確認する順は形状経路→参照→宣言名のみであり、原因の確信度順ではない。
- `tests/test_glb_visual_property_review.py`に順序の回帰テストを追加。元ソース/非公開JSON/MDのプライバシーを維持し、設定値・因果関係を自動決定しない。
- コードSHA `af8e873a613b6b3075448db11f8f26c860dba2a4`：[Python 42296654049](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654049)、[Windows 42296653825](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653825)、[Blender 4.4.3/4.5.15/5.2.1 42296654171](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296654171)、[Windows Kit 42296653959](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653959)、[引き継ぎ 42296653876](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653876)、[Chromium 42296653807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42296653807) **全6系統成功**。
- GLB-021は`partial`のまま。次は許可された合成検証で本当の因果関係の可能性を調べ、実ユーザーデータは事前許可のない実行や公開をしない。

## 2026-11-07 GLB-021 第4段階：固定合成設定の因果・無関係対照テスト

- CBDK独自生成の3部品モデルで、**ソケット開口径0.78→1.70**に戻したときの差分消失を確認するケースと、**ソケット0.78のままボール位置だけ変えてもソケット差分が残る**反証ケースを追加。
- 数値は合成専用の明示的allowlist。ユーザーアドオンのAST静的設定候補が本当に形状へ影響するかの証明ではない。入力GLBはSHA-256が一致し、元コード変更なし。
- テストコードSHA `3b553039968e982e973d10d3427bf0607bbad88d`：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028446)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028346)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028811)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028286)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028673)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028338) **全6系統成功**。
- GLB-021は`partial`のまま、NEXT-019は進行中。GLB-020 MVP凍結を維持し、GLB-022の一般的な自動反復は未実装。

## 2026-11-07 GLB-021 第5段階：合成変更効果の履歴比較

- CBDK合成試験`narrow`、`narrow_placebo`、`identical`について、匿名のボール/軸/ソケットの黄＋赤の観測面数を比較する**新しい履歴レジャー**`cbdk/glb_synthetic_trial_history.py`を追加。
- **合成ソケットを既知の正常な1.70へ戻すと観測差分0、0.78のままボールだけ動かしてもソケットの差分は残る**ことを履歴形式に保存。ユーザーへの設定値推薦・実アドオンの因果保証はなし。
- 履歴出力はCIのローカル`synthetic_trial_history.json`と`synthetic_trial_history.md`のみ。個別GLB座標・元ソース・私有ファイルパスは含めない。入力・出力安全性と既存ファイル不変性をPython単体・Blender実GLB比較で検証。
- テスト対象コード SHA `ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f`：[Python 42299997255](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997255)、[Windows 42299997246](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997246)、[Blender4.4.3/4.5.15/5.2.1 42299997251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997251)、[Windows Kit 42299997311](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997311)、[引き継ぎ 42299997254](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997254)、[Chromium 42299997355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997355) **全6系統成功**。
- [詳細な受け入れ基準](GLB021_TRIAL_HISTORY.md)。GLB-021は引き続き一部実装。GLB-022の許可済み合成反復変更エンジンはまだ未実装、GLB-020 MVPの凍結も維持。

## 2026-11-07 GLB-022 第1段階：Blender実再生成＋差分比較の2試行ループ

- `scripts/blender_make_glb_joint_mvp_fixtures.py`に固定合成条件の`--single`書き出しを追加。既存フォルダ・モデルの上書きを拒否し、任意のアドオンコードや数値パラメータを受け付けない。
- `scripts/run_glb022_synthetic_iteration.py`が許可済みスクリプトで基準GLBと候補GLBを**試行ごとに再生成**し、`cbdk/glb_diff_visualize.py`で実比較。`cbdk/glb_synthetic_iteration.py`の状態機械がソケットの観測誤差面数を厳密に減らし、他部品の観測悪化がない変更だけを採用。
- 初期の狭窄モデル→無関係なボール移動（不採用）→合成モデルの既知正常寸法へ復帰（採用）の2試行に限定。サンプリングでの異常面が0になれば停止し、各試行・採否・理由・停止条件をローカル`synthetic_iteration_history.json`および日本語`.md`へ保存。ユーザーの実データやアドオンは使用しない。
- 厳格な単体テストで誤採用、偽の因果断定、未許可試験、数値矛盾、上書きを拒否。合成GLBとジェネレーターのSHA-256不変も検証。
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`：[Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)・[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)・[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)・[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)・[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)・[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- GLB-022は**一部実装**。固定2試行の合成MVPが成立しただけで、任意パラメータ探索/実ユーザーアドオンでの動作は未保証。GLB-020レビューMVPとGLB-021レビュー機能の安全境界は維持。[詳しい仕様](GLB022_SYNTHETIC_ITERATION.md)。

## 2026-11-07 GLB-022 第1段階 — 合成GLBの生成→比較→採否→自動停止

- `cbdk/glb_synthetic_iteration.py`と`scripts/run_glb022_synthetic_iteration.py`を追加。元データを読み直すだけでなく、**CBDK合成の試験条件をBlenderで新しくGLB出力し、GLB-020で再計測して差分を判断**。
- 初期：狭窄ソケット。試行1：無関係なボール位置移動（ソケット差分が残り棄却）。試行2：合成の既知正常状態へ復帰（観測差分0、他部品悪化0で採用・停止）。最大2試行の上限を設け、JSON/日本語Markdownに匿名の結果を保存。出力は`reports/ci`内の新規フォルダのみ。
- 許可済みのリポジトリ自作生成スクリプトだけを実行。任意のユーザーアドオン、私有コード・GLBの無断実行/変更/公開はせず、合成GLBとジェネレーターのSHA256を比較。
- テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`： [Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)、[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)、[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)、[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)、[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)、[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。
- **GLB-022は一部実装（合成モデル限定）**であり、自由な最適値探索・実アドオンの自動修正・完全な形状同一性は未実装。GLB-021も一部実装。詳細：[第1段階検証仕様](GLB022_ALLOWLISTED_ITERATION.md)。

## 2026-11-07 GLB-022 第2段階：合成3候補の部品間退行防止

- `cbdk/glb_synthetic_multi.py`を追加し、固定条件`narrow_placebo`→`shifted`→`identical`をCBDK自作GLBで実生成・比較。**ソケット改善なし**と**ソケット改善でもボール悪化**の双方を棄却、他部品の悪化がない既知正常モデルのみ採用・観測差分0で停止。
- 既存の2候補`--protocol basic`は維持し、`--protocol cross_part`を追加。試行予算1/2/3、変造された採否履歴、不正な安全フラグと試験名、ローカル上書き防止をPythonで検証。
- コードSHA `d8d233e801b4da33f5f79cf6983818cefdca918c`：[Python 42305594556](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594556)、[Windows 42305594566](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594566)、[Blender 4.4.3/4.5.15/5.2.1 42305594589](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594589)、[Windows Kit 42305594635](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594635)、[引き継ぎ 42305594684](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594684)、[Chromium 42305594551](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594551) **全6系統成功**。
- GLB-022は`partial`のまま。**任意の私有アドオンの自動修正ではなく、CBDK合成3部品の固定3候補**だけを試した。細かな誤差の連続的最適化や形状の完全一致は未検証。[合成3候補の仕様](GLB022_MULTI_CANDIDATE.md)。

## 2026-11-07 GLB-022 第3段階：中間改善を数値で採用

- CBDK合成ソケットの中間開口直径1.24と、ボール移動を組み合わせた対照ケースを追加。GLB-020の全体双方向最大サンプル距離を利用し、**0.78→1.24で距離が減る（ただし差分は残る）状態を途中改善として採用**。
- 同時に、ボール位置が悪化する候補は距離の改善とは関係なく棄却。最後はCBDK既知正常の1.70で観測距離0のため採用・停止。`basic`/`cross_part`の既存プロトコルも維持。
- 最大3試行、予算1/2での未完成打切り、欠損レビュー/不正数値/安全フラグの拒否、ユーザー非公開データを出力しないことをPythonとBlender実GLBで検証。
- テスト対象コードSHA `44e15f8f6664fe29e06810fd06d8d73dda70bec6`：[Python 42307811087](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811087)、[Windows 42307810687](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810687)、[Blender4.4.3/4.5.15/5.2.1 42307810797](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810797)、[Windows Kit 42307810828](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810828)、[Handoff 42307811040](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307811040)、[Chromium 42307810743](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42307810743) **全6系統成功**。
- GLB-022は`partial`。全体サンプリング最大値は厳密な部品別誤差・完全幾何一致ではない。実ユーザーアドオンの原因/適切な設定値は依然未検証。[詳細](GLB022_PROGRESSIVE_SYNTHETIC.md)。

## 2026-11-07 GLB-022 第4段階 — 数値候補の算術生成とBlender実比較

- 合成ソケット開口の0.78〜1.70を算術4分割して**1.01/1.24/1.47/1.70**の数値候補を計算。候補を手書きで固定した試験IDへ変換するだけでなく、CBDK生成器が検証済みの小数値を受け付け、それぞれBlenderで新規GLB出力・再比較。
- 双方向の全体サンプル最大距離が減り、他部品の分類面数が増えない候補だけ採用。途中で改善が止まれば棄却、予算1/2/3の打切りでは未完了を保存。合成既知正常の1.70では観測0で停止。
- JSON/日本語Markdown履歴はローカル新規ファイル、候補値の安全範囲・未知入力・上書き禁止・SHA-256不変を確認。旧3プロトコルもCIに保持。
- テスト対象コード SHA `23e9dec5d313468a70cc3bab7a5bb57fc090a8b3`：[Python 42309145079](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145079)、[Windows 42309145003](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145003)、[Blender4.4.3/4.5.15/5.2.1 42309145076](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145076)、[Windows kit 42309145019](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145019)、[引き継ぎ 42309145005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145005)、[Chromium 42309145006](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42309145006) **全6系統success**。
- **GLB-022はpartialのまま**。これは自作合成モデルの固定格子探索であり、実アドオンの自由最適化や厳密な距離・完全幾何一致ではない。[第4段階仕様](GLB022_GENERATED_GRID.md)。

## 2026-11-07 GLB-022 第5段階 — 実測フィードバックで次候補を変える合成探索

- CBDK自作合成ソケットの安全範囲0.78〜1.70（0.01刻み）で、GLB-020の**双方向サンプリング最大距離が合成専用目標0.12以内か**を使って次の二分区間・開口径を更新。前回の固定格子と異なり、実測の分岐結果で試行順が変わる。
- 実Blenderの3バージョンで **1.24→1.47→1.35→1.41**を生成・比較。1.47を目標内候補として記録、最小の合格値の確定はせず最大4回で停止。測定を変えると1.24→1.01と分岐することもPythonで検証。
- 他部品悪化の拒否、未知値・不正入力・偽の改善履歴の拒否、入力ジェネレーター/GLB SHA-256不変、新規ローカルJSON/日本語MDのみ保存。既存のbasic/cross_part/progressive/generated_gridもCIで維持。
- テスト対象コードSHA `37ee124aabb44df5ad9cb246342712bd9e0eb2ef`：[Python 42311608904](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608904)、[Windows 42311608916](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608916)、[Blender4.4.3/4.5.15/5.2.1 42311608910](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311608910)、[Windows Kit 42311609353](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609353)、[引き継ぎ 42311609070](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609070)、[Chromium 42311609211](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42311609211) **全6系統success**。
- GLB-022はpartial。距離は全体のサンプリング最大で厳密Hausdorffや部品別誤差ではなく、0.12も実物の製造公差ではない。[詳細](GLB022_ADAPTIVE_SYNTHETIC.md)。

## 2026-11-07 開発引き継ぎ：証拠整合性と現在のロードマップ

- 指定ブランチHEAD `7a021f5`から継続。正式v0.17.0、ドラフトPR #25、未マージ。最新コード/テスト`e254aa7`の6系統CI成功をAPIと実ジョブで確認（Python 42357800567、Windows 42357800581、Blender3版 42357800595、Kit 42357800603、Handoff 42357800626、Chromium 42357800564）。docs-only後続SHAの成功とは混同しない。
- 開始時Python 3.12.14で701件成功。GLB-019の匿名部品一覧/弱い候補がSTATEに未反映だったため現状と全体計画を`DEVELOPMENT_PLAN.md`へ記録。
- **実装:** 候補再計算時のJSON型一致、途中省略した一覧からの総面数範囲、skip時の完全一覧合計、上限超過がないskipと空シーン測定の拒否。新規6回帰テスト（関連27件成功）。既存の合成探索/GLB-020凍結を維持。
- **実機:** ローカルBlender4.3.2で自作GLB4ケース（ユニーク、曖昧、33部品、33部品561面）を生成→実ランナーで再読込→台帳/候補/skip/入力SHA256不変を確認。対象3版の成功に代用しない。同じスクリプトを既存3版CIへ追加。
- **状態:** GLB-019の今回の補強は対象CI完了までpartial/python。GLB-021/022は引き続きpartial、正式last_verified維持。人間の判断が必要なGUI操作/権利/正式公開の境界も計画書へ記録。
- **Notion:** 既存プロジェクトと4タスクの読取成功。新規ページは作らない。GitHub保存後に既存要約/状態/検証/予定を同期するまでpending。私有ソース、GLB、ローカルレポート、個人情報は同期しない。

### 引き継ぎ後の補強：対象CI実測成功

- コードSHA `31bf3de18c357d796194dcac369c66e55b3973bf`： [Python 42359722780](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722780)（707件×3.11/3.12/3.13）、[Windows 42359722774](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722774)（3.11/3.13）、[Blender 42359722777](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722777)（4.4.3/4.5.15/5.2.1）、[Kit 42359722842](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722842)、[Handoff 42359722778](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722778)、[Chromium 42359722853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42359722853)の**全6系統success**。
- 全Blender版の追加`Verify anonymous inventory and weak hints through real GLB imports`工程成功。ユニーク/曖昧/33部品/561面skip、元GLB SHA256不変を実際に検証。GLB-019をimplemented/blender_ciへ戻し、NEXT-021をdoneへ。一般の部品同一性や完全形状保証は追加しない。
- Notionの既存プロジェクト/4タスクは中間状態を同期済み。このGitHub記録後に最終CI成功を反映する。正式v0.17.0、PR #25ドラフト、未マージ・未公開を維持。

### Notion最終同期完了

GitHub実測記録`c7306ce`を正本として、既存CBDKプロジェクトとGLB-019/020/021/022の4タスクへ現在の要約・ステータス・CI・今後の予定を反映。最終更新はすべて警告なし成功。GLB-019完了、020/021/022作業中。ページ新規作成なし、私有コード/GLB/個人情報なし。同期先リンクと結果は`docs/NOTION_SYNC.md`、正本STATEのmaintenance_policyへ保存。常駐ジョブは設置していない。次はNEXT-019/020の合成反復の失敗/打切り診断と人手レビュー。コード検証SHAは31bf3deで固定し、この同期受領は文書のみ。

## 2026-11-07 GLB-022第6段階：途中失敗と人手レビューを一括実装

- 開始HEAD `110c7b2`、既存ロードマップNEXT-019/020に沿い、合成適応探索の失敗時に履歴が残らない問題を優先。範囲は自作合成モデル・最大4試行のまま。
- `glb_synthetic_adaptive.py`へ未完了prefixの構築/検証を追加。従来の完了履歴APIは未完了を拒否する境界を維持。
- `glb_synthetic_run_review.py`と既存ランナーへ、工程前の上書きしないチェックポイント、最終JSON/日本語MD、固定失敗分類、検証済み履歴保存、入力SHA256照合、読取専用CLIを追加。失敗候補は採用せず、目標内観測と実行完了を分離。例外自由文/私有パスを記録せず、自動再開もしない。
- 新規20件の回帰テストを含む関連56件がPython3.12.14で成功。ローカルBlender4.3.2で予算1の実生成→比較→完了レビュー成功。合成GLB実生成・基準比較後に候補比較のタイムアウトを**模擬注入**し、失敗終了と基準履歴保存も成功（自然ハングの再現ではない）。
- 対象3版CIへ通常4試行/14チェックポイント検査と明示的な模擬タイムアウト工程を追加。新CI未実施のため現時点で合格とは記録しない。詳細`GLB022_RUN_REVIEW.md`。
- GLB-022全体partial、NEXT-022 in_progress。正式v0.17.0/PRドラフト/GLB-020凍結を維持。GitHubへ保存し実測後に既存Notionへ同期する。
- 節目のローカル全体検証：Python3.12.14で**727件成功**。STATE validate / handoff write・check / diff checkも成功。次にこのコードの対象GitHub CIを1回実行して実測を確認する。

### GLB-022第6段階のCI実測成功

- コードSHA `5dc799ac6dd46ed27f249dfea694c67644d4ab22`： [Python 42361082109](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361082109)（727件×3.11/3.12/3.13）、[Windows 42361081999](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361081999)（3.11/3.13）、[Blender 42361082117](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361082117)（4.4.3/4.5.15/5.2.1）、[Kit 42361082094](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361082094)、[Handoff 42361082165](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361082165)、[Chromium 42361082252](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42361082252)の**全6系統success**。実装pushに対する全体CIは1回で完了し、再実行なし。
- 全Blender版で従来の4試行/採否/停止履歴に加え、14チェックポイントと最終レビューを実検査。基準GLB生成・比較と候補生成を実Blenderで行い、候補比較のタイムアウトのみを明示的に模擬注入した工程も全版成功。自然ハング再現や実ユーザー検証ではない。
- NEXT-022をdoneへ、GLB-022はpartial/blender_ci。新しいLIM-014に強制終了・書込み障害時の最終保存限界と手動確認を記録。次はNEXT-023の同条件複数合成実行の比較レビュー。任意コード実行・自動採用/再開・正式公開/マージなし。
- この実測をGitHubへ保存後、既存NotionプロジェクトとGLB-022タスクへ同期する。後続文書コミットはコードCI対象SHAと区別。

### 第6段階のNotion同期完了

GitHub正本の実測記録`c575834`を既存CBDKプロジェクト/GLB-022タスクへ反映。現在要約・全体partial/作業中・NEXT-022完了・6CIリンク・LIM-014・次のNEXT-023を更新し、全応答警告なし成功。新規ページ・私有ソース/GLB/個別レポート・個人情報の同期なし。コード検証SHAは5dc799aで固定し、受領記録は文書のみ。

## 2026-11-07 現行ロードマップ継続：NEXT-023 同条件複数実験比較

- 開始HEAD87ceb5d、前段階コード5dc799aの全6CI成功を再確認。既存NEXT-023/NEXT-020を対象とし、新しいNEXT番号や無関係な構想は追加しない。
- 新規`glb_synthetic_conditions.py`で固定プロトコル・ソース集約SHA・Blender版・基準/初期GLB SHA・初期観測を記録。`glb_synthetic_run_review.py`は旧schema1を維持し、新しい条件付き記録をschema2とする。ランナーは比較/検証ソース変更と候補測定版の不一致も拒否。
- `glb_synthetic_run_compare.py`の読取専用CLIと日本語レビューを追加。失敗/未完了/入力改変/旧条件なし/条件・予算不一致を成功比較から除外し、距離と面数の反対変化を混在扱い。任意ラベル/パス/不正本文を出力しない。自動採用・実行・再開なし。
- 新規15回帰テストを含む関連71件成功。ローカルBlender4.3.2で独立した予算1の2実験を実生成・比較し、条件一致/観測差なし、模擬タイムアウト実行除外を確認。開発途中の古いローカルJSON（未コミット形式）は厳格読取で拒否し、現行形式で再生成した。
- 比較のみのウォームアップ後3回の中央値：2件2.416704ms/割当ピーク20,225bytes、16件17.300782ms/145,632bytes。16件は証拠を複製した負荷試験で16独立実験ではない。ディスク/Blenderは計測外。速度保証/最適化採用はしない。
- CIへ独立4試行の再実行を1回追加し、通常実行と条件比較・失敗除外・時間/割当ピークを実測予定。対象CI未実施。GLB-020/021/022はpartial、NEXT-023 in_progress、正式v0.17.0/PRドラフトを維持。詳細`GLB023_RUN_COMPARISON.md`。
- 節目の最終ローカル検証：Python3.12.14で**742件成功**。関連71件、新規15回帰を含む。STATE validate / handoff write・check / diff checkも成功。このまとまりの対象GitHub CIを1回実行する。

### 初回CI失敗と修正（NEXT-023）

- コードf4130ffのPython742件×3/Windows2/Kit/Handoff/Chromiumは成功。一方[Blender run42363769064](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42363769064)は4.4.3成功、4.5.15/5.2.1失敗。既存比較/固定反復までは通り、新しい適応探索の条件構築で停止。
- 実ログの`bpy.app.version_string`は`4.5.15 LTS`/`5.2.1 LTS`。新規版名検査が数字3要素しか許可していなかった。LTS接尾辞だけを明示許可し、生の版名を条件として保持。2つのLTS版を含む正常ランナー回帰を追加。任意文字列を許可して回避しない。
- 最終点検で親シンボリックリンクにより出力先がignored領域外へ解決される余地も発見。正規のrepo内reportsパスに限定し、Windows権限に依存しないパス解決回帰で拒否を確認。
- GitHub CLIの失敗artifact取得はリダイレクト先403。GitHub連携では取得可能で、診断は実ジョブログのLTS版名と再現回帰に基づく。私有データは扱っていない。
- 関連71件は成功。初回失敗を合格扱いせず、上記の実際の修正を含むコードで必要な最終CIを行う。

### NEXT-023/NEXT-020の実測完了と既存NEXT-005の検討完了

- 修正コード`2867ab31cf355486232f1f1b257315c9e73146a1`：[Python742件×3版42364086005](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364086005)、[Windows2版42364086014](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364086014)、[Blender3版42364085988](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364085988)、[Kit42364085981](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364085981)、[Handoff42364085980](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364085980)、[Chromium42364085989](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42364085989)の全6系統success。
- 全Blender版で独立した通常4試行2回の条件一致/観測差なしと、模擬タイムアウト失敗の除外を実検査。LTS版名を拒否した初回失敗を記録し、実修正後に合格。単純な再実行で合格扱いにしていない。
- 比較の2件中央値2.152477〜2.914226ms、Python割当ピーク40,961〜40,981bytes。16件複製負荷は17.286411〜23.695476ms、215,491〜215,581bytes。ディスク/Blender除外、ホストPython3.11.18、速度保証なし。詳細GLB023_RUN_COMPARISON.md。
- 既存NEXT-005の3版監査/メモリ/Undo検討をAUDIT_RUNTIME_REVIEW.mdへ記録して完了。追加最適化や上限緩和の根拠なし。背景Undoは全版unavailable、Redo未試行、GUI未検証。NEXT-002やGUI要件は完了へ変更しない。
- 完了NEXT-023/020/005。作業台帳23件＝完了16/継続6/保留1。要件43件＝実装済26/一部13/未実装3/保留1。次は既存NEXT-019/009のGLB-021レビューと許可済み合成反復の対応。新規NEXT番号なし、正式v0.17.0/ドラフトPR/未マージを維持。
- このGitHub正本保存後、既存Notionへ節目同期する。同期受領・文書コミットは上記コードCIの対象SHAと区別する。

### 現行ロードマップ単位のNotion同期受領

実測正本566bfbbを既存プロジェクト/GLB-022へ同期し、全3更新応答が警告なし成功。NEXT-023/020/005、CI6系統、時間/割当ピーク、GitHub作業台帳16完了/6継続/1保留と要件43件の状態、次の既存NEXT-019/009を反映。NEXT-005単独ページは既存タスク検索で見つからず、プロジェクト要約に分析文書をリンクして重複ページを作らなかった。私有データ・生成レポート・個人情報の同期なし。検証対象コードは2867ab3、この受領は文書のみ。

## 2026-11-07 現行v0.18継続：NEXT-019 / NEXT-009の測定元一致レビュー

- 開始HEADc4dcbca、現行タスクを優先。新しい次期NEXT番号や現行優先順位の追加はしない。
- GLB-022の省略可能条件に初期GLB-020集計の正規化SHAを記録。旧schema1/2読取・成功履歴の互換性を維持。
- `glb_visual_experiment_review.py`の読取専用CLIで、測定元一致を検査してから明示ソースをAST-onlyで読み、候補宣言/参照/構文経路と完了/未完了/失敗prefixを私有JSON/日本語MDに整理。人の役割＋完全一致名は確認用の合成操作リンクであり、実プロパティ効果/因果・推奨値ではない。
- 新規10回帰成功、既存合成71件と可視候補群26件も成功。ローカルBlender4.3.2の実生成/比較を使い、完了/未完了/模擬タイムアウトの連携、異なる測定元拒否、元ソース/JSONのSHA不変、私有候補名のstdout非表示を確認。自然ハングや実ユーザー因果を検証したものではない。
- `verify_glb021_experiment_link.py`を既存3版CIへ追加。自作ソースはASTのみ、私有シートはartifact対象外reports/latest。新対象CIは未実施、NEXT-019/009はまだ継続、GLB-021 partial。
- 次期承認はdocs/futureの独立JSON/MDにAPPROVED_WAITING_FOR_V018_GATESとして保存。現行STATEの要件/NEXT/優先順位へ未来の項目は追加しない。自動化残作業と人間ブロッカーはV018_COMPLETION_GATES.md。移行開始の承認は取得済みだが、現行自動化未完了のため未有効。main/公開/未承認採用/私有データは別承認。
- 節目のローカル全体テスト：Python3.12.14で752件成功。STATE validate / handoff write・check / diff check、独立した未来計画JSONの承認済み・未有効/版順も確認した。次にこの実装の対象GitHub CIを実行する。

### 測定元一致の候補・実験連携：実測CI成功

- コード`79fea17e70665392731780ed5a518982530b7323`：[Python752件×3版42366055143](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055143)、[Windows2版42366055138](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055138)、[Blender3版42366055131](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055131)、[Kit42366055135](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055135)、[Handoff42366055133](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055133)、[Chromium42366055162](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42366055162)全6系統success。実装push1回で完了、CI再実行なし。
- 全Blender版の新しい連携工程が成功。初期集計SHA一致、完了/未完了/制御された模擬失敗の表示、別集計拒否、元ソース/JSON不変、私有候補のstdout非表示を検証。AST fixtureは未実行、実プロパティの因果は未証明。
- NEXT-019完了。NEXT-009は自動化部分を拡充したが実データ実体/登録/効果未確認のため継続。GLB-021/022全体partial、正式v0.17.0・PRドラフト/未マージを維持。作業23件＝完了17/継続5/保留1、要件43件の状態区分は不変。
- 次は既存NEXT-003の登録/依存/レシピ検査の残りを優先。人間ブロッカーはV018_COMPLETION_GATES.md。次期は承認済み・未有効、開始の承認を取り直さず条件達成後に進むが、現行自動化未完了のため有効化しない。未来の要件/NEXTを現行STATEへ追加していない。

### 今回のNotion同期受領と再開地点

GitHub実測正本421e23aを既存プロジェクト/GLB-021/NEXT-009へ反映し、全6更新応答が警告なし成功。NEXT-019完了、NEXT-009継続・実データ未確認、6CI、作業17完了/5継続/1保留、次の既存NEXT-003を同期。承認済み未来計画は別リンクで未有効として表示し、現行優先順位は変更しない。重複ページ・私有シート/ソース/GLBのアップロードなし。検証コード79fea17、受領記録は文書のみ。次回は登録/依存/レシピ検査の残りから開始する。

## 2026-11-07: NEXT-003 登録整合性 / NEXT-002 制御Undo/Redo

`python -m cbdk.registration_audit` は既存6レシピを一時ディレクトリへ実生成し、独立したレシピ期待値、信頼済みカタログ、実機smokeのKNOWN機能一覧、Blender CIの明示レシピループを照合する。生成ZIP作成前にも、同梱PythonをASTだけで解析し、相対importの閉包/静的helper export、明示OPERATOR_CLASS、CBDK operator ID/クラス名重複を拒否する。任意ソースをimport/実行しない。動的export/動的登録の一般的証明ではなく、固定自作プレビューの整合性検査である。新機能追加時は一覧・依存・実機テストを一緒に更新する。静的成功は承認/権利/実機成功ではない。

Undo schema2は旧schema1読取互換を維持し、通常背景プローブと`explicit_ed_undo_push`制御条件を分離する。単一頂点1操作と複数頂点2連続操作について各段階をNative Undo/Redoし、座標・辺/面の接続順・全選択状態を完全比較する。ゼロoffsetのCANCELLEDで無変更も検査。毎回BMeshを再取得し、スナップショットでUndoを代用しない。手動pushの成功は通常の自動履歴、GUIショートカット、実ユーザープロジェクトの証拠にならない。

今回ローカルPython765件成功、Blender4.3.2の明示履歴2ケースUndo/Redo成功・通常背景Undo不能。対象4.4.3/4.5.15/5.2.1とWindows CIはまだ未実行。最新の実測結果はSTATEの今回節目を参照する。

### NEXT-003 / NEXT-002 最終CI判定（2026-11-07）

実装コードc80f2a0a174a37074c283641ce288a378261e92dのBlender4.4.3/4.5.15/5.2.1・Kit/Handoff/Chromium成功。テストだけUTF-8指定を修正したb5d32734d4a74e6acd7ff896baeb3aa3088e661aのPython767件×3版・Windows2版成功。両SHA間の変更はtests/test_registration_audit.pyだけで実装は同一。対象6系統の結果は[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368307965)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368305584)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190461)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190510)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190490)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190614)。

NEXT-003完了。NEXT-002は制御履歴2ケースの成功を確認したが通常背景Undo不能・GUI未検証で継続。初回Windowsのパス/文字コード失敗を修正し、テストだけの再実行はPython/Windowsへ限定。6レシピの生成ZIPは新AST検査の有無で同じSHA。負荷・既知制限・再開点は[検証記録](REGISTRATION_UNDO_VALIDATION.md)を参照。
