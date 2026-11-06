# CBDK 開発仕様（現行版）

このファイルは、以前の `docs/SPEC.md` に残っている初期計画を置き換える**現行の設計方針**。機能ごとの実装状態・未実装・制約・次の作業・テストへのリンクは `docs/project/STATE.json` を正本とし、読みやすい要約を `docs/PROJECT_HANDOFF.md` に自動生成する。

## 目的と対象

- 自作Blenderアドオンを**実行せず**にAST解析し、関数・クラス・依存関係・重複候補を整理する。
- 権利と動作を明確にした自作再利用部品に固定IDを割り当てる。
- 検証可能なレシピから**開発用レガシーアドオン**を作成する。現在の自作部品は7個、UI搭載機能は5個。
- Python 3.11〜3.13 / Blender 4.4.3、4.5.15、5.2.1でコードと生成アドオンのCIを実行する。
- チャットの長さ・表示不良・履歴の消失に影響されず、**GitHubの保存情報だけで継続開発**できるようにする。

## データの区分

| ファイル | 目的と変更ルール |
|---|---|
| `docs/project/STATE.json` | **正本**。要件・実装/未実装状態・問題・優先タスク・決定事項・最後の確認済みテストURL |
| `docs/PROJECT_HANDOFF.md` | 上記から自動生成。新チャットが最初に読む |
| `docs/project/LAST_CI.json` | 自動ワークフローがmainのPythonテスト通過時にのみ更新する観測記録。Blender CIの合格を勝手に代弁しない |
| `docs/PROGRESS.md` | バージョン別の時系列・原因分析などの過去履歴。古い内容を上書きしない |
| `catalog/authored_parts.json` | 自作部品のID、ソース、採用/権利確認状態 |
| `catalog/addon_features.json` | 生成レシピから呼び出せる機能と依存関係 |
| `AGENTS.md` | すべてのAI開発作業に適用する安全性と引き継ぎ手順 |

## 実装状態と検証状態

**実装状態**：`implemented`（実装済）、`partial`（一部実装）、`not_implemented`（未実装）、`deferred`（保留）。

**検証種別**：`python`（Python単体）、`blender_ci`（Blenderヘッドレス実機）、`manual_pending`（画面操作の確認待ち）、`not_tested`（未検証）。

この2つは独立。実装済が完全な実機保証・利用許諾・正式採用を意味することはない。CIに実際に対応するコミット、日付、Blenderバージョン、ワークフローURLを記録する。失敗/保留/未実施のテスト結果を成功と記録しない。

## 開発の節目ごとの作業契約

1. 新チャットではまず `docs/PROJECT_HANDOFF.md`、`docs/project/STATE.json`、`AGENTS.md` を読む。
2. 実装に着手する前に現在のブランチ・バージョン・要件ID・未解決の問題を確認する。
3. 機能を増やす/変える場合は対応する要件・検証種別を台帳へ反映し、コードと回帰テストを実装する。
4. 失敗したテストは問題・原因・対応策・実行URLを記録。実行待ちは「未検証」のまま扱う。
5. ブランチ上で `python scripts/project_handoff.py --validate` と `python scripts/project_handoff.py --write` を実行して、台帳と引き継ぎを同期する。
6. Pull RequestのGitHub Actionsを検査。必要なPython/Windows/Blenderテストが実際に成功してから、`last_verified`・次の作業・進捗履歴を更新する。
7. mainへのマージ後、`CBDK durable handoff`ワークフローが再度Pythonテストを実行し、実測を `docs/project/LAST_CI.json` に、引き継ぎを `docs/PROJECT_HANDOFF.md` に同期する（GitHubの権限/ブランチ保護により自動pushできない場合はCI成果物を確認）。

## 現行の安全上の制約

- ユーザーの元アドオン、個人の .blend、認証情報、プライベートな抽出レポートをGitHubへ自動でコミットしない。
- プレビューアドオンは明示的に `--preview-unapproved` を指定。承認済みの公開Blender Extensionと呼ばない。
- BMesh加工の監査と座標復元は完全な原子性・クラッシュ耐性を保証しない。
- Blender GUIの見た目・マウス操作・Ctrl+Zの実際の操作感はヘッドレスCIだけでは検証できない。
- GitHubからBlenderへの直接インストール・更新機能は**ユーザー希望で保留**している。

## 再開のための最小コマンド

```bash
python scripts/project_handoff.py --validate
python scripts/project_handoff.py --write
python scripts/project_handoff.py --check
python -m unittest discover -s tests -v
```

最新の「既知の問題」と「次にやること」は `docs/project/STATE.json` を確認すること。過去のチャットを再読する必要はない。


## v0.16: メッシュ編集監査の性能・安全基準

- 監査前の要素数を直接読み取り、上限超はデータコピーや変更の前に中断する。
- 選択頂点の編集結果はライブBMeshから読み取り、未選択頂点・移動量・選択・辺/面接続の異常を拒否する。
- 世界座標が巨大でも、差分の許容誤差は期待移動量基準で判断する。浮動小数点精度の限界で期待差分を確認できなければ安全側に拒否する。
- Python/Windowsの回帰テストに加え、3バージョンのBlenderで中規模格子を用いた時間・メモリ観測、制限超過時の変更前拒否を確認する。
- 観測値は該当するGitHub Actionsとコミットに結び付ける。環境をまたぐ絶対性能保証はしない。



### 非有限座標からの復元契約（v0.16追補）

- 異常なBMesh座標の復元前に、頂点/辺/面の接続関係だけを検査する。NaN/Infを含む元データをスナップショット化し直して復元を妨げない。
- 元の座標・選択の書き戻し後に再検証し、誤った成功報告を避ける。完全に戻らない場合は「復元不完全」として明示。
- トポロジーが変わっている場合は座標復元による修復を保証せず中断。
- Blenderの致命的クラッシュや外部データを含む完全トランザクションを保証しない。


### 旧・新監査方式の判定整合性（v0.16追補）

- `audit_vertex_translation` と `audit_live_vertex_translation` は、入力された移動量が有限の3数値タプルであること、予定外の移動を拒否すること、非ゼロ移動なのに一つも頂点の変化を観測できない場合は成功扱いしないことについて同じ基準を使用する。
- Blenderのfloat32座標で極小移動が丸められる場合も、編集されたと誤認しない。誤差は要求した移動量を基準に評価し、ワールド座標の絶対値で閾値を不当に拡大しない。
- 本補強の確認はローカルPython単体テスト。GitHub Actionsランナーが起動せず、最終CIの成功や正式マージは未実施。


### 数値監査のXYZ軸別安全契約（v0.16追補）

- 操作前に要求されたローカル座標移動のXYZ各軸を独立に検証する。非ゼロ指定軸は実際に変化し、その変化が指定距離の許容誤差内にあることが成功条件。
- ゼロ移動指定の軸や未選択頂点の座標は完全一致を求める。微小な誤変更も正当化しない。
- 非ゼロ軸の差分誤差は、既存の絶対/差分連動閾値と要求距離の15%を比較し、小さい方で判定。float32精度で表現できない要求は成功扱いしない。
- 監査違反ではBMeshの更新後スナップショットから可能な限り復元するが、Blender本体のクラッシュやトポロジー再構築までは保証しない。


## v0.17 開発検証：Undo/Redo証拠の取り扱い

- Native Undo/Redoは、CBDK生成プレビューだけをBlender `--background --factory-startup` 上で有効化して検査する。外部アドオンやユーザーの.blendを実行しない。
- 正確な頂点移動と選択/トポロジー不変を最初に確かめる。`bpy.ops.ed.undo.poll()` または `redo.poll()` が偽なら、その工程を検証成功と記録しない。
- 取得したレポートは `cbdk.undo_probe_report` でスキーマ・状態整合性を検証する。実行不能時の状態は `unavailable_in_background` であり、「Undoの成功」ではない。
- GUI Ctrl+Z / Ctrl+Shift+Z、実際のUI操作感、ユーザーデータ上での互換性はヘッドレスCIでは保証しない。別途Windows GUIで検証する。
- この節の実装は開発ブランチ上の未検証作業であり、v0.16のPR #18の未解決CI問題を解消するものではない。正式な合格実測が取れるまでmainへマージしない。

## v0.17 ドラフト：レシピ依存関係の一括監査

`cbdk/recipe_matrix.py` は6つの信頼済みレシピを固定の期待機能IDと突き合わせる。登録済み5機能/7部品が`modular_all`も含む6レシピで漏れなく参照されること、カタログ/モジュールの対応・静的Blender対象版・ファイル存在を検査する。原本の実行・依存コードのインポート・ビルドや公開はしない。

実行例：`python -m cbdk.recipe_matrix --output reports/ci/recipe_matrix.json`

新しい機能を登録したときは、`TRUSTED_FEATURES`/`TRUSTED_PART_SOURCES`、カタログとレシピ、独立した`EXPECTED_RECIPES`、生成テンプレートと各テストを同時更新する必要がある。静的マトリクス成功はBlender実機・Windows GUIやライセンス認定の代わりにならない。

現段階では開発ブランチの未検証変更。GitHub Actionsの実行前障害Issue #19が解決するまでは、CIの実行結果を成功とは書かない。

## v0.17 開発中：新機能・部品の安全な登録準備

新規機能の登録候補は `python -m cbdk registration-draft` で**レビュー専用JSON**として生成できる。既存台帳とコードallowlistの整合性、提案IDの重複、新規ソース予定パスの衝突、部品依存を静的に検査し、マトリクス・CI・ライセンス・引き継ぎ更新の手順を出力する。

例：`python -m cbdk registration-draft --feature-id align_vertices --requires-part BLCTX-001 --requires-part BME-004 --new-part-id BME-004 --new-part-module edit_align`

`--output` を明示した場合だけ `reports/latest/` 以下にJSONを新規保存。既存ファイルの上書き、私有ソースのインポート/実行、カタログやコードの自動変更、権利認定、実機テスト成功の自動認定は**禁止**する。出力は登録の提案であり、パーツ採用や公開を許可するものではない。

実際の組み込みには、原本/権利を人手で確認したうえで台帳・許可リスト・コード・レシピ・スモークテストを別PRで更新する。全体Python/Windows/Blender CIの実測完了までは `main` へマージしない。参照：`docs/REGISTRATION_DRAFT.md`。

## v0.17 開発中：登録ドラフトからレビュー用Pythonテストの自動ひな形

`registration-draft --output reports/latest/registration_draft.json` で保存した提案を、`python -m cbdk registration-tests --draft reports/latest/registration_draft.json` で読み込む。提案の全項目を現行の信頼済み台帳から再生成して比較し、期限切れ相当の不一致、改変されたID/依存/承認フラグ、重複JSONキー、危険な出力パスを拒否する。

生成される `reports/latest/scaffolds/test_<feature_id>_review.py` はプライベートな非追跡領域のみ。既存ファイルは上書きしない。想定テスト5項目は初期状態ですべて `self.fail("TODO: ...")` とし、未完成なのに成功するテストは生成しない。生成されたファイルや元ソースはCBDKから自動でインポート・実行しない。公式 `tests/`、台帳、許可リストへ移動/登録するのは人手レビューと実装・実測の後。

**CI/Blender実機成功・公開ライセンス承認・UI品質を意味しない。** v0.16/0.17の未検証コードは安定版mainにマージしない。詳細：`docs/REGISTRATION_DRAFT.md`。

## v0.17 追加仕様：宣言された動作種別でテストのひな形を切り替える

`python -m cbdk registration-draft --feature-id ... --requires-part ... --behavior read_only` または `--behavior mesh_edit` で、開発者が新機能の動作種別を申告する。種類の判定に未確認コードを実行したり、機能名だけで勝手に推定したりしない。

保存される `behavior` は省略可能なスキーマ1の補助フィールド。従来の省略状態は `unspecified` として扱い、既存の保存済み計画と共通5件のTODOを維持する。`read_only` と `mesh_edit` は共通5項目に各3件の専用TODOを追加する。読み取り専用では座標・選択・モディファイア・変換・Undo履歴の不変性を確認する。メッシュ編集では選択範囲のみの変更、入力エラー時のロールバック、ネイティブUndo/Redoによる再現を確認する。

`behavior` はあくまで**申告されたテスト計画上の分類**であり、コードが本当に読み取り専用/編集可能であることを認証・自動判定するものではない。生成先は従来どおり無視対象の `reports/latest/scaffolds/` に限定、全TODO失敗・非実行・非上書きを維持。Blender実機確認・ライセンス審査・正式採用を自動化しない。

CIブロッカー Issue #19 のため、この追加機能のPython/Windows/Blenderの全テスト合格は未実測。v0.17ドラフトPR #20に留め、安定版と `last_verified` を変更しない。


## GLB形状確認の証拠経路

参考モデルやアドオン生成物をGLBで受け取る場合、ファイル名・会話文・画像生成AIの再構成だけから形状を断定しない。

- `glb-inspect` はGLB 2.0のJSON構造を静的に読み、node/mesh名とprimitive/accessor情報を記録する。
- `glb-quick-preview` はBlenderが使えない環境向けの任意fallback。trimesh+matplotlibで実GLB形状から7方向/部品単独画像を生成するが、Blender実レンダリングより低精度と明記する。外部URI参照は事前拒否する。
- `glb-preview` は信頼済みBlenderをfactory-startupの別プロセスで起動し、front/back/right/left/top/bottom/iso PNG、最大32個の部品単独画像、import後のscene metadataを生成する。
- Blender実レンダリング画像とmetadataを、元GLBの形状理解の主要証拠とする。
- 画像生成AIは設計説明図や提案の可視化には使えるが、元GLBを忠実に表示した証拠として扱わない。
- ユーザーGLBや生成レポートはGitHubへ自動コミットしない。CIでは専用の自作fixtureだけを使う。


## v0.18 GLB shape regression

- Blender scene metadataは各Mesh Objectのworld-space boundsを記録する。
- `glb-compare` はreference/candidate metadataを読み、全体bounds、部品bounds、配置、任意のトポロジー差を構造化JSONで返す。
- `shape` profileは見た目/機構の近似比較向けで、トポロジー差は非致命。`strict`は名前・トポロジーも一致条件にする。
- `glb-regression` は2つのGLBを信頼済みBlenderで別々にpreviewし、そのmetadataを比較する。ユーザー私有GLB・生成previewはreports配下のローカル証拠として扱い、公開repoへコミットしない。
- 比較失敗は自動コード採用を意味しない。差分は次の修正候補を決める証拠であり、修正後は通常のPython/Windows/Blender CIを再実行する。


### Silhouette regression

GLB scene metadata schema 4では、Blender実メッシュを固定正射影して32x32 binary silhouette signatureを記録する。sceneは7方向、部品はfront/right/top/isoを対象とする。`glb-compare` はIoUを計算し、既定0.90未満を形状差として扱う。signatureは証拠用であり、画像生成AIの推測ではない。三角形数上限を超えたsignatureは`available=false`として明示し、成功扱いにすり替えない。

## v0.18 GLB形状診断：量的な根拠と未対応データの扱い

`glb-diagnose` は `glb-compare`/ `glb-regression` の比較JSONだけを入力とする**レビュー用原因仮説**。シーンの複数方向に現れたシルエット差分を一つの全体候補へ集約し、部品の輪郭差は部品ID/名前ごとに区別する。`hypotheses[].evidence_summary` に影響視点、最悪IoU、最大相対誤差、欠落部品の相対体積割合、各severityの差分件数を出力する。

正常性判定は比較側の`passed`（bool）・`summary.errors`と`differences`の重大度集計が一致する場合だけ受け付ける。未知のコードも捨てずに`unsupported_difference_codes`に記録し、警告や情報だけでもレビュー対象とみなす。重複JSONキー、非有限/負の指標、0..1域外のIoU・体積割合、異常なサイズの証拠は拒否する。

生成されたレポートは**原因候補であり、元形状との完全一致の証明ではない**。32x32シルエットは細穴・内部空間・サブグリッドの差分を見逃し得る。結果を根拠にコードを自動変更/承認/マージする機能は作らず、ユーザーのGLBデータはGitHubに上げない。v0.18 PR #25のコードcommit e971b784で、Python 3版・Windows 2版・Blender 3版のGitHub CIが実測成功したためGLB-005は実装済・Blender CI検証として管理する。ただしPRは未マージ、最後の正式リリースはv0.17.0であり、実ユーザーGLBでの同等性証明も別課題。

## v0.18 開発中：GLB診断→アドオン設定候補のレビュー計画（GLB-006）

`python -m cbdk glb-repair-plan reports/latest/glb_compare.json --output reports/latest/glb_repair_plan.json` は、既存の比較結果を厳密に検証して診断を再構築し、`cbdk_glb_repair_plan` JSONを出力する。既存の `glb-regression` は比較・診断に加え `repair_plan.json` を生成する。

対象部品・原因カテゴリ・比較数値から、存在しそうな設定**候補群**、確認チェックリスト、該当視点、最悪IoU、観測差分の代表軸を提示する。Ball/Socket/Hingeの名前は弱いロール推測としてのみ扱い、そのアドオンの実際のプロパティ名・設定値とは断定しない。実数値からの自動設定や補正はしない。`unit=unknown_from_comparison`を明示し、参考と候補GLBの値は証拠であって修正指示ではない。

原因仮説に未知カテゴリが含まれたら人手確認、比較差分に未対応コードが含まれたら`unmapped_difference_codes`として残す。設定候補のない状況でも「根拠がない」と正直に示す。レビューが必要な場合は「確認→人手で1箇所修正→GLB再生成→比較→Python/Windows/Blender CI」というチェック手順を提示する。

新たな20 Python回帰テストと3版Blenderの合成GLB CIを追加。未知の元アドオン実行、コード修正、自動承認、GitHubへの私有GLBアップロードは禁止。正式リリースv0.17.0の`last_verified`は、v0.18の正式リリースまで変更しない。
