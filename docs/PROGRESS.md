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
