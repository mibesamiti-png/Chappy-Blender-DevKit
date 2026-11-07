# Chappy Blender DevKit (CBDK)

> **開発ライブボード:** [ブラウザ用HTML](docs/dashboard/index.html)（ファイル保存→Edge/Chrome等で開く。GitHub Pages公開は未設定。読み取り専用・5分自動/手動更新）
>
> **現在の開発状態を見る:** [新チャット用の引き継ぎ](docs/PROJECT_HANDOFF.md) · [正本の開発状態台帳](docs/project/STATE.json) · [現行仕様書](docs/PROJECT_SPEC.md)
>
> **v0.15.0以降、最新の進捗とテスト結果は上記が優先。** 以下にはv0.1から積み重ねた説明・旧計画が混在するため、古い「未実装」欄を最新版とは判断しないでください。

**ChatGPT / Codex向け Blenderアドオン開発資産ライブラリ・静的解析ツール**

初期記録: **v0.1 — Phase 1の基礎 + Phase 2の重複候補抽出（プロトタイプ）**。現在のバージョンは上記の開発状態台帳を参照。
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


## v0.6 — Blender helper candidates and test contracts

**New original helper modules (not yet Blender-verified):**
- `parts.blender.context`: explicit context and mesh-selection helpers; no implicit mode changes.
- `parts.blender.edit_mesh`: read-only BMesh selection counters in `EDIT_MESH`.
- `cbdk.contracts`: derives per-candidate *review-only* test requirements from the existing Blender API audit. Mode hints are not proven preconditions.

```bash
python -m cbdk scan input_sources_private --output reports/latest
python -m cbdk audit-blender --catalog reports/latest/catalog.json --output reports/latest/blender_audit.json
python -m cbdk contracts --audit reports/latest/blender_audit.json --output reports/latest/blender_contracts.json
python -m unittest discover -s tests -v
# Only on a PC where a trusted Blender executable is installed:
python -m cbdk.blender_test blender --suite parts
```

The optional `parts` Blender smoke suite uses only **CBDK-authored code**, runs with a factory-startup scene, tests object vs. edit mode and selected vertices/edges/faces, and saves its JSON result under `reports/latest/blender_smoke.json`. It does not automatically certify extracted candidate code. The default `basic` smoke suite remains unchanged.

The contracts report contains **metadata only** (`verification=static_only`, `approved=false`). Do not commit private, source-derived reports without checking provenance and rights. See `parts/blender/README.md` for candidate IDs, prerequisites, and verification distinctions.


## v0.7 — Blender部品のテスト証拠を安全に管理

v0.6で作成した3つの読み取り専用ヘルパー部品に対し、**Blender本体を使った個別チェックと、その実行環境の記録**を追加しました。元アドオンを自動実行する仕組みではありません。

```bash
# Python単体テスト（Blender不要）
python -m unittest discover -s tests -v

# BlenderがインストールされているPCのみ
python -m cbdk verify-parts --blender blender --output reports/latest/parts_evidence.json

# テスト記録が現在のコードに対応しているか確認
python -m cbdk evidence-status --evidence reports/latest/parts_evidence.json
```

`verify-parts` は信頼済みの `scripts/blender_parts_smoke.py` のみ実行します。BLCTX-001、BLCTX-002、BME-001 の所定のチェックが揃い、Blenderが正常終了した場合に限り `blender_smoke_passed` を記録します。部品・テストスクリプトのSHA-256、Blenderバージョン、実行日時、各テスト結果を保存します。失敗時は検証済部品を0件として扱います。

`evidence-status` は現行コードのハッシュとの整合性チェックです。**署名・証拠の真正性を保証するものではありません。** 外部から受け取ったJSONを実機検証済みの証明として信頼しないでください。 `catalog/authored_parts.json` は初期台帳で、実機テストを実行するまでは `not_recorded` のままです。テスト成功後も使用許可・ライセンス確認・正式採用は別途必要です。

この開発環境にはBlender実行ファイルがないため、v0.7ではPythonモックテストのみ確認しています。Blender本体の実機成功はまだ確認していません。


## v0.8 — Windowsワンクリック＆クラウドBlender実機テスト

- Windows：`run_blender_tests_windows.bat` をダブルクリック。Blender・Pythonを自動検出し、Pythonテスト → Blender実機テスト → 証拠の整合チェックを実行する。
- GitHub：`.github/workflows/blender-smoke.yml` が公式Blender 4.5.15 LTSをSHA-256検証後に起動し、3部品を検証。PRで自動実行、Actionsから手動実行も可能。JSON/ログをArtifactsに14日保持。
- Blenderは別プロセスの `--background --factory-startup` で実行し、既存の.blendやユーザー設定は変更しない。
- 証拠やログはGitの対象外。外部アドオンの原本をアップロード・実行しない。正式承認（`approved=false`）は別の手続き。

詳細は [docs/TEST_ENVIRONMENT.md](docs/TEST_ENVIRONMENT.md) を参照。


## AI開発スキル：Chappy Blender DevKit v1.0

`.agents/skills/chappy-blender-devkit/SKILL.md` を追加。ChatGPT/Codex向けに「再利用候補の確認 → 安全な実装 → Python・Blender検証 → GitHub PR → 進捗記録」の手順を標準化します。

導入・使用方法: [docs/SKILL_SETUP.md](docs/SKILL_SETUP.md)  
スキルZIP生成: `python scripts/package_skill.py`（`dist/` にスタンドアロン／プラグインの2形式を生成）

**注意:** スキルが存在してもChatGPTへの自動インストールはされません。既存のBlender実機テストは指定の3つの自作部品に限定されています。


## v0.9 — 部品別のBlenderバージョン検証マトリクス

Windows実機テストやGitHub Actionsが残した `parts_evidence*.json` を、SHA-256と部品IDごとに検査し、**どのBlender版でテストできたか**一覧化します。

```bash
python -m cbdk part-matrix --evidence-dir reports/latest
# 個別ファイルを指定する場合
python -m cbdk part-matrix --evidence reports/latest/parts_evidence_Blender_4_4_3_3.json
```

出力は `reports/latest/parts_matrix.json` と `parts_matrix.md`。Windowsのワンクリックテストでは検証後に自動作成します。古い・壊れた証拠は除外理由を表示し、集計コマンドは失敗を返します。**自作部品の台帳は変更せず、正式採用・ライセンス確認・検証記録の真正性を自動認定しません。**


## v0.10 — CBDK Mesh Inspectorアドオンを自動生成

レシピから安全側の自作部品3個を選び、Blender 4.4+向けの**プライベートなレガシーアドオン開発プレビュー**を自動生成できるようになりました。

```bash
python -m cbdk build-addon --recipe recipes/mesh_inspector.json \
  --preview-unapproved --output dist/CBDK_Mesh_Inspector_Preview.zip
```

Blenderの **3D View > Sidebar > CBDK** に「Mesh Inspector」が追加され、選択メッシュ/頂点/辺/面の数を検査する読み取り中心のサンプルです。部品の正式採用・配布許諾は未確認のため、`--preview-unapproved` を指定した個人開発用途に限定します。

導入・テスト方法: [docs/ADDON_BUILDER.md](docs/ADDON_BUILDER.md)


## CBDK v0.11 — 部品を選べるモジュラー・アドオン生成

これまでの固定サンプル（v1レシピ）を残したまま、**v2の宣言的レシピ**から必要な機能だけを組み込むようになりました。

```bash
python -m cbdk build-addon --recipe recipes/modular_objects.json --preview-unapproved --output dist/CBDK_Objects_Preview.zip
python -m cbdk build-addon --recipe recipes/modular_edit.json --preview-unapproved --output dist/CBDK_Edit_Preview.zip
python -m cbdk build-addon --recipe recipes/modular_combined.json --preview-unapproved --output dist/CBDK_Combined_Preview.zip
```

有効な機能は `object_selection`（選択メッシュ数）と `edit_selection`（編集中メッシュの頂点・辺・面の選択数）。レシピが指定したものだけZIPに封入します。実装はCBDKが作成した固定の安全側モジュールを再利用します。**任意の外部アドオンを自動実行・自動組み込みする機能ではありません。**

3つとも同じ開発用アドオン識別子 `cbdk_modular_preview` を使うので、**同時インストールせず、前のプレビューを無効化してから差し替える**想定です。正式な配布用Blender Extensionは未対応。詳細は [docs/ADDON_BUILDER.md](docs/ADDON_BUILDER.md)。


## CBDK v0.12 — 許可済み機能カタログ・依存関係検査

`catalog/addon_features.json` に、既存の自作機能2種類の部品依存・機能依存・Blenderの最低対応バージョンを記録。**レシピの入力だけで、必要部品を解決し、互換性を確認**できるようになりました。

```bash
python -m cbdk feature-list
python -m cbdk addon-plan --recipe recipes/modular_combined.json --target-blender 4.4.3
python -m cbdk build-addon --recipe recipes/modular_combined.json --target-blender 4.4.3 --preview-unapproved --output dist/CBDK_Combined_Preview.zip
```

`feature-list` は機能の一覧、`addon-plan` は機能・部品の依存閉包と最低対応バージョンを表示し、ZIPは生成しません。`--output reports/latest/addon_plan.json` でJSON保存可能。

カタログは宣言的データです。JSONだけを編集して任意のPython実装や外部アドオンを取り込むことはできません。新しい機能は**安全なコード側の許可リスト・出典・専用テストを追加してから**登録する設計。循環依存や存在しない部品、Blender互換性の不整合は拒否します。正式承認・再配布ライセンス認定は行いません。


## CBDK v0.13 — メッシュの寸法とモディファイアを確認

Blenderの実用的な読み取り部品を2件追加しました。自作の固定部品5件と、宣言的レシピから選べる4機能になりました。

| 機能 | 操作 | 部品ID |
|---|---|---|
| `mesh_bounds` | メッシュのワールド軸に沿った寸法を表示（未適用モディファイアは含まない） | `BLGEO-001` |
| `modifier_summary` | アクティブメッシュのモディファイア数と種類を表示 | `BLMOD-001` |

```bash
python -m cbdk addon-plan --recipe recipes/modular_all.json --target-blender 4.4.3
python -m cbdk build-addon --recipe recipes/modular_all.json \
    --target-blender 4.4.3 --preview-unapproved \
    --output dist/CBDK_All_Tools_Preview.zip
```

従来の `modular_objects` / `modular_edit` / `modular_combined` に加え、`modular_geometry`（新しい2機能）と `modular_all`（計4機能）のレシピを追加。Blender 4.4.3 / 4.5.15 / 5.2.1で、それぞれのヘッドレス操作・登録解除を検査する仕組みです。

**両機能とも基本は読み取りのみ**。Active Object・選択・モード・メッシュ形状・モディファイア設定を変更しません。検査結果の表示用Scene文字列プロパティだけを更新します。レガシー形式の個人プレビュー用であり、正式な配布・採用・ライセンス承認は含みません。


## CBDK v0.14 — 編集モードの安全な頂点移動（開発プレビュー）

`BME-002` / `vertex_nudge` を追加。Edit Modeで選択した頂点だけをローカル座標で少し移動できるようになりました。デフォルトはZ方向 +0.1 Blender単位、操作実行時にはX/Y/Zのオフセットを変更可能です。

```bash
python -m cbdk build-addon --recipe recipes/modular_nudge.json \
  --target-blender 4.4.3 --preview-unapproved \
  --output dist/CBDK_Vertex_Nudge_Preview.zip
```

NパネルのCBDKタブに `Nudge Selected Vertices` を表示する開発用レガシーアドオンです。`recipes/modular_all.json` にも追加したので、他の4機能と一緒に生成できます。

保護策：**Edit Mode・メッシュ1個・選択頂点あり・有効な有限オフセット**を満たさない場合は編集前に拒否。共有メッシュ/シェイプキー/リンクデータを拒否し、選択/トポロジー/モードは変更しません。例外が発生した際は元の頂点座標へ復元を試み、復元できなかった場合は明示的にエラー表示します。オペレーターにはBlender標準の `REGISTER` / `UNDO` を設定しています。自動テストはオペレーター設定と前後の頂点座標を確認しますが、**ヘッドレスではGUIのCtrl+Z操作感まで保証しません**。

公開用の完成アドオンではなく、未承認部品を含む個人開発用プレビューです。重要な本番作業の.blendファイルでは試さないでください。


## CBDK v0.15 — 編集前後のメッシュ差分監査と自動復元

`BME-003 / edit_audit.py` を追加。Edit Modeの加工前後にBMeshの頂点座標・頂点選択・辺/面の接続関係を記録し、**指定した編集以外の差分が発生していないか**を検査します。

`vertex_nudge` は、移動後の監査が成功しない限り編集成功と扱いません。想定外の座標変更ならスナップショットから復元し、復元不能・トポロジー変更が疑われる場合は**明示的に中断**します。安全な最大容量は頂点＋辺＋面で20万要素まで（開発プレビューの暫定制限）。Blender標準のUndoにも引き続き対応しています。

```bash
python -m cbdk build-addon --recipe recipes/modular_nudge.json --target-blender 4.4.3 --preview-unapproved --output dist/CBDK_Audited_Nudge_Preview.zip
```

**注意**：この検査はクラッシュ時まで保証するトランザクションではありません。実際のCtrl+ZのGUI操作感、致命的なメモリ障害、スナップショット外のデータまで修復できるわけではありません。公開用Extensionではなく個人開発用プレビューです。


## CBDK v0.16 — メッシュ監査のメモリ負荷軽減

v0.15で加工前後のメッシュを丸ごと複製していた方式を変更し、**加工前の記録を保持したまま加工後の頂点座標・選択状態はBMeshから直接検査**するようになりました。辺/面の接続と失敗時復元の検査は維持しています。

- 要素数チェックをコピー前に行い、頂点＋辺＋面が20万を超えたら変更前に拒否。
- 巨大なワールド座標が小さな編集ミスを隠すことを防ぐため、差分許容誤差を要求移動距離に基づいて判定。
- Blender 4.4.3/4.5.15/5.2.1上で70×70格子メッシュを使い実行秒数・Python追跡メモリのピークを記録し、上限超過時に元メッシュが変わらないことを確認。

旧capture_edit_snapshot/audit_vertex_translation APIや既存レシピは維持。20万要素の上限は解除しておらず、性能の観測値は環境依存。個人開発用プレビュー・未承認状態・GitHubからの直接インストール保留も継続。


## v0.17 draft — GLB Visual Inspector

参考3Dモデルやアドオン生成物をGLBで受け取ったとき、画像生成AIの再構成に頼らず、構造JSONとBlender実レンダリングを作る開発機能です。

```bash
# Blenderなし: node/mesh/material/primitiveを静的解析
python -m cbdk glb-inspect model.glb --output reports/latest/glb_structure.json
pip install -e ".[glb-quick]"
python -m cbdk glb-quick-preview model.glb --output reports/latest/glb_quick_preview

# 信頼済みBlenderあり: 構造JSON + front/right/top/iso PNG + scene metadata
python -m cbdk glb-preview model.glb \
  --blender /path/to/blender \
  --output reports/latest/glb_preview
```

静的解析はGLBのBIN payload、外部URI、画像を読み込まず、JSON構造だけを確認します。ユーザーGLBや生成レポートはGitHubへ自動コミットしません。詳細は `docs/GLB_VISUAL_INSPECTOR.md`。
