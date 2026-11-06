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

## v0.18 開発中：GLB修正候補と実アドオンのAST静的プロパティ照合（GLB-007）

`python -m cbdk glb-map-properties <repair_plan.json> --source <local.py> --output reports/latest/glb_property_mapping.json` を追加。GLB-006の原因別設定候補群について、**ユーザーが明示指定したローカルPythonファイル**だけを`ast.parse`で構文解析し、Blender `bpy.props` のクラスレベル宣言を照合する。最大16ファイル、各1MiB。ディレクトリ全自動走査や元アドオンのimport/exec、Blenderでの未確認コード実行は禁止。

照合は候補名と宣言プロパティ名が**完全一致**した場合だけ`exact_declaration_name_only`と記録。別名importと`bpy.props`形式にも対応。報告には匿名ファイルラベル（`source_1.py`）、クラス名・行番号・Property種別を付け、コード本文、デフォルト値、ソース絶対パス・実ファイル名は記録しない。名前が一致しても実際のBlender登録やジオメトリへの影響、正しい修正値を保証しない（`registered_in_blender: not_checked`、`validated_geometry_effect: false`）。見つからなくても設定がないとは断定しない。

レポート保存先はGit管理対象外の`reports/latest/`のみ。絶対出力パス・上位参照・既存ファイル上書き・symlink外部出力を拒否。現在のプランが改ざんされている場合、承認済み偽装フラグや不正な候補名・巨大ソースを拒否する。私有ソース本文/値は公開GitHubにコミットしない。

`tests/test_glb_property_map.py`の24件回帰テストと、3版Blenderの合成GLBから生成した修正プランに**合成**Blenderプロパティ宣言を照合するCIを追加。詳細は`docs/GLB_PROPERTY_MAPPING.md`。次タスクは人手でレビュー済みの宣言と実際の形状への影響を確認することであり、自動変更ではない。

## v0.18 GLB-008：AST属性参照の証拠記録

`cbdk/glb_property_usage.py` は、ユーザーが明示指定したPythonソースを`ast.parse`だけで読み、GLB-007で名前完全一致したProperty宣言の識別子をASTの属性アクセスと照合する。関数スコープ内で同名属性を見つけた場合、読み取り・代入・拡張代入（`+=`など）・削除の4分類、匿名ソース名、クラス/関数名、行番号、受け手の粗いパターンを記録する。

見つかるのは**同名属性アクセスの可能性**だけである。オブジェクトの本当の型やproperty登録との接続、メッシュ生成への寄与は実行時に確認した証拠ではない。受け手の結びつきと幾何影響はfalse/not_verifiedとして固定する。動的参照は検出対象外、1ファイル4096件超の参照を拒否し、各設定の例示は16件に制限する（全件数は保持）。ユーザーコードは実行も改変もしない。

`glb-map-properties`のレポート`exact_name_matches[].possible_code_references`に追跡結果を統合し、今後の手動レビューと安全な実機確認に備える。新規回帰テスト23件と合成Blender CIを追加。私有コード・定数・元パスはレポートに含めず、ignored`reports/latest/`の外へ出力しない。

## v0.18 GLB-009 — 属性参照とプロパティ宣言クラスの構文上の関連

GLB-008の属性名参照証拠はBlenderプロパティとの結び付きを一切確認していないため、GLB-009では同じ匿名ソースIDとクラス名における `self.<名前>` の参照を別に集約し、無関係な受け手 `other.<名前>`、別クラス・別ファイルからの参照と区別する。読み・書き・複合書き・削除の件数を保存例最大16件とは独立に正確に集計する。

`same_class_reference_review`の判定は**構文上の関連ヒント**であって、レシーバーが実際にプロパティ所有インスタンスであることや、Blenderへ登録されたこと、ジオメトリへの効果や動作確認を意味しない。クラス名が匿名化された場合は誤関連を避けて一致候補から除外する。外部ソースのimport/execや設定の自動適用、私有ソースのアップロードは行わない。

テストは `tests/test_glb_property_binding.py` とBlender3版の合成fixtureで行う。詳細は `docs/GLB_PROPERTY_MAPPING.md`。

## v0.18 GLB-011 — モディファイア設定への候補経路

GLB-010の直線的ASTデータフローに、Boolean/Bevel/Solidify関連で使われ得る `width`/`thickness`/`operation`/`object`/`segments`/`levels` 等の属性代入、および複合代入を追加する。宣言された `self.<プロパティ>` や検証範囲内のローカル別名からその値が代入式に現れる場合のみ `possible_modifier_setting_assignment` として報告。別オブジェクト由来、関数内共起のみ、分岐/ループ/ネストなどは因果経路と認定しない。

Python任意オブジェクトの同名属性でも候補になるため、`modifier` の本当の型、Blenderモディファイア設定が適用されたこと、実ジオメトリに効果があったことは**一切未証明**。自動修正やコード実行はしない。詳細・利用上の制約は `docs/GLB_PROPERTY_MAPPING.md` に記録。

## v0.18 GLB-012 — 安全な合成アドオンによる定量パラメータ実験

CBDKがリポジトリに自作した合成アドオン `fixtures/cbdk_parameter_experiment.py` のみを、Blender実機CIで実行する。基準・球半径変更・Bevel幅変更の3種類についてメッシュ生成→GLB書出→再読込を実施し、頂点位置の差を数値化する。`cbdk/parameter_experiment_metrics.py`は同じ頂点順の2メッシュについて局所頂点移動距離の平均・最大・変更頂点数を計算する。計測は**頂点順と頂点数が一致する自作合成fixtureに限定**し、別メッシュ/一般GLBの最短表面距離などは証明しない。球半径だけを変えた場合は球だけ、Bevel幅変更では立方体だけが変わることを、生成直後とGLB再読込後の両方で確認する。

CIはBlender 4.4.3/4.5.15/5.2.1の合成テストに定量アサーションを追加。Python純粋関数の10回帰テストを追加する。合成fixture以外のユーザーアドオンやコード・GLBは実行、公開、修正しない。生成された合成頂点座標はCIの出力JSONに保存せず、集計値のみを記録する。結果はユーザーの任意アドオンの修正適否や完全な幾何一致を保証しない。

## v0.18 GLB-013 — CBDK製合成モデルの上下プローブと方向判定

GLB-012で構築した**自作・事前許可済みの合成Blenderアドオン**だけを対象に、基準1条件、球半径の参照・上下各条件、Bevel幅の参照・上下各条件の計7 GLBをBlenderで生成して再読込する。各パラメータの参照メッシュに対して、同じ頂点数の合成メッシュについて、頂点順を並べ替えても変わらない局所原点からの半径分布（昇順ソート）の平均絶対差を基準、増加プローブ、減少プローブで測る。両方の差が十分離れ一方が基準より改善した場合だけ`increase`または`decrease`を示し、差が小さい・曖昧・改善なしは`inconclusive`。**最適な数値は自動推定しない**。

`cbdk/parameter_direction.py`の純関数`choose_review_direction`は有限で非負の同一指標を要求し、`auto_apply:false`、`suggested_numeric_value:null`、`verified_for_arbitrary_user_addons:false`を返す。Blender実験では変更対象外の部品を正負対照として持ち、変更0の確認に失敗すると実験全体を不合格とする。生成直後とGLB再読み込み後の両段階の方向が一致することを確認する。

`tests/test_parameter_direction.py`に11回帰テストとBlender 4.4.3/4.5.15/5.2.1 CIの7 GLBチェックを追加する。実行するコードはCBDKがリポジトリで作成したfixtureだけ。ユーザーの私有アドオン/GLBはGitHubに保存・実行しない。同じ半径分布を持つ異なる形状も存在するため一般GLBの表面一致には適用できず、最適数値や実ユーザーアドオンの修正方向を保証しない。

## v0.18 / GLB-014 — 三角面による双方向の表面ズレ指標（初期実装）

`cbdk/glb_surface_distance.py` は、明示的な共通座標系で与えられた三角形配列の**面上サンプルから相手メッシュの三角形面への最近接ユークリッド距離**を両方向で測る。平均値は各面積で重み付けし、サンプル中の最大値も記録。頂点番号・同面の対角線の分割に依存しない。現在は最大128面/mesh、base2/3 Halton列24点/面、非有限座標と退化面は拒否。

Blender CIはCBDK製の合成4 GLB（平面2通りの三角分割、中央に開口がある平面、Z+0.25移動）を実生成→再読込して比較。全外寸が同じでも開口の有無が異なるケースを、片方向だけでなく**両方向**の距離から検出する。初期相関サンプリング12点/面が穴を見逃したため、Halton24点/面に修正した。

検出できるのは離散的にサンプリングした表面だけ。**真のHausdorff距離・完全な形状等価性・内部密閉空洞/閉体積/非多様体を証明しない**。大規模な実ユーザーGLBの比較パイプライン/CLIにまだ接続していない。非公開ソースやGLBをCIへ渡さず、元アドオンを実行・自動修正しない。仕様詳細は`docs/GLB_SURFACE_DISTANCE.md`。
