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

## v0.18 / GLB-015 — 三角面への最近接探索のBVH高速化

GLB-014のサンプル点→三角形面距離に、決定的な重心中央値分割のAABB-BVHを導入し、総当たり全三角面の精密距離計算を空間的に絞り込む。三角形ごとの距離関数は従来と同一であり、BVHが探索対象を省いても最近接三角形の値は総当たりと一致するべきである。表面サンプリングの精度自体は変更しない。三角形数の安全上限は128→512、1面当たり24 Haltonサンプルを維持。

方向別の`triangle_distance_evaluations`と`brute_force_evaluations`を出力し、**正確な三角形距離の計算回数**の削減を計測。ウォールクロック時間・実ユーザーの高密度GLB処理速度は未測定。Python純粋回帰テストを10件追加し、総当たりとの一致、400/512面受理、上限超拒否を検査。Blender3版の合成CIで256面`grid_256.glb`を追加生成・再読込し、同一表面のスコア0と精密距離評価回数4分の1未満をチェックする。ユーザーGLBの任意解析CLIにはまだ接続しない。

BVHは小さな穴の見逃し・内部空洞の未検証・数学的な完全一致の非保証を解決しない。詳細は`docs/GLB_SURFACE_DISTANCE.md`。

## v0.18 GLB-016 — BVHの実時間計測と合成512面GLB

`cbdk/surface_benchmark.py`は、明示的に制限した合成メッシュに対してBVH構築・サンプリングを含む1方向の処理時間を`time.perf_counter_ns`でウォームアップ後3回測り、中央値（ms）を算出。64面の同一入力に限り総当たりとの実時間比較と結果一致を実施し、512面はBVH単独を計測する。速度の倍率は観測値でありランナー負荷に依存するためCIの合格閾値に使わない。タイミング情報・面数・計算回数のみ出力し、私有メッシュ頂点やソースは出力しない。

合成Blender CIの表面距離テストを5→6 GLBへ拡張し、`grid_512.glb`を実生成・再読込して比較対象512面を確認。実質的な大規模モデルの処理速度や正確な体積・内部空洞を保証しない。テストは`tests/test_surface_benchmark.py`を追加。詳細は`docs/GLB_SURFACE_DISTANCE.md`。

## v0.18 GLB-017 — 粗/精2段階の3D表面比較

`cbdk/glb_multires_surface.py`を追加。最初に各三角面8 Halton点を比較し、粗い誤差最大の疑わしい面を上限8面/方向選択。誤差0であることが証明ではないため、未選択の面積上位2面も探索枠として追加選定。選択した面のみ48点まで精査する。各段階の面積重み付き平均と最大観測距離、追加サンプル点数と調べていない面数を返す。未検出箇所の取りこぼしが可能なため、完全形状一致を主張しない。

Blender CIには幅0.44の開口を持つ新しい合成GLBを追加。従来24点固定の見逃しと、多解像度48点の発見を実出力・再読込で比較する。既存BVHの計算回数と実時間比較、広い開口、Z移動、512面ベンチも維持。実装範囲は合成トポロジのレビュー用であり、私有アドオン実行/GLB公開・自動設定変更なし。詳細は`docs/GLB_SURFACE_DISTANCE.md`。

## v0.18 GLB-018 — 特徴優先による多解像度調査

GLB-017の追加探索を「面積上位2面」のみに固定せず、最大1面を特徴候補の上位から選び、もう1面は従来の面積ベース探索として必ず保持する。候補ヒントはメッシュの境界辺（外寸内側かどうかは投影的な簡易近似）、共有辺の面法線変化、三角面積中央値比、共通頂点の近傍数、共有辺の過剰接続。粗い8点で実際の差を見つけた面は従来どおり優先し、既存のサンプリング・BVH・512面上限は変更しない。

面積探索のみの`feature_aware=False`と比較するPython専用回帰テストを13件追加し、Blender4.4.3/4.5.15/5.2.1の公開CIではCBDK自作の合成GLBを7→9種へ拡張。大型板に囲まれた小さな開口を新方式が発見できるか検証する。境界・鋭角・細かさ・密集はレビュー候補であって、欠陥・穴・閉じた空洞の存在は認証しない。詳細は`docs/GLB_SURFACE_DISTANCE.md`。

## v0.18 GLB-019 — 実GLB入力からの表面距離レビューを既存パイプラインに統合

`cbdk/glb_surface_pipeline.py` と `scripts/blender_glb_surface_review.py` を追加し、ローカルの参照GLBと生成GLBを読み込む明示コマンド `python -m cbdk glb-surface-review reference.glb generated.glb --blender <trusted blender>` を実装。静的glb_inspectorで外部URI禁止・入力24MiB以下・頂点参照概数10万以下を確認し、信頼済みスクリプトのみを`--factory-startup --disable-autoexec`で起動。全メッシュのワールド座標三角形を一時メモリ上で比較し、固定24点BVH表面距離と特徴優先多解像度の結果を集計JSONに出力する。**三角面512超は間引かずにskipped**とする。生頂点座標/絶対入力パスは報告に保存せず、元GLBとPythonアドオンは変更・実行しない。

既存の`glb-regression --surface-review`で従来の比較・診断・修正候補JSONに`surface_review.json`を任意で追加できる。未指定なら従来の振る舞いを維持。`passed`は従来のメタデータ比較専用と明記し、表面距離0を立体一致の証拠として扱わない。

Python側に12件のpreflight/安全ランナー/報告/スキップテストと3件の回帰統合テストを追加。Blender 4.4.3/4.5.15/5.2.1 CIでは**CBDK自作GLB**を使用し、同じ面の異三角分割と同外寸の開口差を新CLIで実読込比較する。一般ユーザーGLBでの性能や部品マッピングは未検証。詳細は`docs/GLB_SURFACE_PIPELINE.md`。

## GLB-020（試作）: 双方向の形状差分を色付き3Dモデルで出力

- 新CLI: `python -m cbdk glb-diff-visualize reference.glb generated.glb --blender <trusted_blender> --output reports/latest/glb_diff_visualization`。明示実行のみ。出力先は存在しない新規ディレクトリに限定。
- 各GLBの世界座標三角形について、相手側の三角面BVHへの固定24点サンプル距離を評価。参照側・生成側を**別々**に灰色（対角線比1%未満）/黄色（1〜5%）/赤（5%以上）で表示するローカル`reference_diff.glb`/`candidate_diff.glb`を生成する。しきい値・各色の面数・サンプル最大距離を`review.json`へ記録。
- 入力の静的preflight、外部URI拒否、各512三角形上限、24MiB上限、固定Blenderスクリプト・`--factory-startup --disable-autoexec`、元アドオンコード非実行、ネットワークアップロード禁止、元GLB不変を維持。派生GLBには元の形状座標が含まれるためローカル保存専用。
- **検証**: Python単体テスト、3版Blenderで自作合成GLBの差分/同等分割を比較して色付きGLBを出力し、Blenderへ再インポートするCIを追加。テスト成功はSHAに紐づけて記録する。
- **未完了**: 元オブジェクトの識別/選択、複数モデル同時ビュー・カメラ連動、未知領域の独立色、細部の検出率向上、大型GLB。灰色/誤差0は幾何完全一致や内部空洞無しの証明ではない。新しい手動修正候補の自動適用も行わない。詳細: `docs/GLB_DIFF_VISUALIZATION.md`。

## GLB-020 第2段階：匿名部品別の着色GLB（試作）

参照・生成それぞれに最大64個の非空メッシュを保持したまま、匿名の`CBDK_Reference_Part_###` / `CBDK_Candidate_Part_###`として3D色分けモデルを書き出す。`review.json`の`parts.reference`/`parts.candidate`に部品別の三角面数と色の枚数を記録するが、元の部品名や生頂点座標は出さない。元GLBは書き換えず、派生モデルはローカル保存限定。**双方の同じ部品番号は対応関係の証明ではない。** 連動比較UIや未知領域の表示・大規模GLBは未完成。

合成2部品GLBの実書出・再読込と色別材料の維持はBlender4.4.3/4.5.15/5.2.1でCI成功。検証: [Blender run 42265921506](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42265921506)、実装テストSHA `7365828b`。正式v0.17.0/ドラフトPR #25維持。

## GLB-020 第3段階：オフライン連動比較HTML

2つのGLBを比較するローカル`compare_viewer.html`を出力。外部フロントエンド依存なしのCanvas 2Dソフトウェア3D投影で、左右視点の同期回転・ズーム・平行移動、左右独立した匿名部品の選択、灰色面の表示切替ができる。共通中心と世界単位の縮尺で位置ズレの隠蔽を避ける。元コードは実行しない。

このHTMLには派生三角形の座標が含まれ、非公開モデルの場合はローカル専用。JSONには形状座標を書かない。CSPでネットワークへの接続と外部スクリプトを拒否。元GLB不変、最大512面・64部品を維持。

実装テストSHA `b5d1d27`：Python [42268089086](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268089086)、Windows [42268088883](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088883)、Blender3版 [42268088779](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088779)、kit [42268088823](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088823)、handoff [42268088869](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42268088869) 全成功。

実ブラウザ操作・正確な遮蔽判定・別GLB間の部品対応・未観測面の確定、512面超は今後の開発タスク。GLB-020は一部実装、正式v0.17.0/ドラフトPR #25を維持。

## GLB-020 第4段階：匿名部品の対応候補（非確定）・Chromium GUI検証

参照/生成GLB間の匿名メッシュ部品について、世界座標バウンディングボックスの中心・寸法・三角面数を相対スコア化して相互の候補を表示する。相互最近傍・分離マージンを満たせば\`suggested\`、重複/近接で曖昧なら\`ambiguous\`、弱い関連は\`unmatched\`。**どの場合も「同一部品である証明」ではない。** ローカルHTMLの候補ボタンはユーザーが押すまで表示を切り替えず、元GLBやアドオン設定は変更しない。

新CI \`.github/workflows/glb-viewer-browser.yml\` では本物のヘッドレスChromiumを用い、CBDK自作の入替2部品モデルをローカルHTMLで表示し、回転/ズーム・候補選択・面フィルタ・通信なし・JS実行例外なしを検証する。外部ブラウザ試験環境の導入時にはUbuntu 24.04を固定する。テスト成功と実ユーザーGLBの形状認識精度を混同しない。

正式リリースv0.17.0とドラフトPR #25は維持。Python、Blender、WindowsおよびブラウザのCIは、それぞれ実際に確認されたコミットSHAと結果を別に記録する。

### GLB-020 第4段階の検証（2026-11-07）

コードSHA `72e9bd4e4ad2cb9b9716ee0cb5ea10de60cd779e` では、[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183982)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184368)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184086)・[Windowsキット](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274184021)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183990)・[Chromium実ブラウザ操作](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42274183979)が**全6系統success**。

各テストはCBDKが作った合成データのみ。HTML表示・操作の成功は、3D形状の完全一致や本当の部品同一性、特定のアドオン設定の原因特定の証明ではない。

## GLB-020 第5段階：追加サンプリング感度の表示

2つのGLBの面について、基本の24点/面の測定とは異なる24点を追加で測り、追加点の観測誤差が大きく増えたり従来の色閾値を越えたりした面を**紫の輪郭**で示す。ローカル比較HTML内で紫枠の表示を切り替えられる。

- 指標は`extra_halton_24_probe_sensitivity_v1`。追加の点と元の点はHalton列の異なる区間を使用。増大基準は共有AABB対角線の0.5%以上、または既存の1%/5%色閾値横断。
- **赤/黄/灰の元色は変更しない**。紫枠は追加プローブで差の増加が実際に観測された事実のみを意味する。紫でない面は「全域を検証済み」ではない。
- 匿名部品ごとの紫枠対象面数と全体件数は集計JSONに、個別の面フラグは私有形状を含むローカルHTMLにのみ保存。元GLBやユーザーのアドオンを実行・変更・アップロードしない。
- 完全形状一致・内部空洞一致・未サンプル領域の自動特定・実ユーザーモデルの性能・GLB-021設定原因同定は未検証。BlenderとChromiumの合成CIはその試験範囲内の証拠として扱う。

### GLB-020 第5段階の検証結果（2026-11-07）

コードSHA `38057b1da49eeb61020664c4923ced2b2bad8406`： [Python 42279824321](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824321)、[Windows 42279824307](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824307)、[Blender 4.4.3/4.5.15/5.2.1 42279824378](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824378)、[Windows kit 42279824398](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824398)、[引き継ぎ 42279824427](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824427)、[Chromium GUI 42279824304](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42279824304) **全6系統success**。

テストで紫枠オン/オフを確認した合成ブラウザ画面のフラグはUI試験専用に明示的に注入しており、「実物の小穴を新手法が検出した」とは主張しない。数値監査の追加点はPythonテストで別途検証。無印の面は依然として部分サンプルのみ。

## GLB-020 第6段階：境界エッジの観測と部品候補の慎重化

各匿名メッシュ部品の三角面を世界座標で近接統合し、1面しか接しない境界辺、2面で共有される辺、3面以上の非多様体辺を集計する。`world_space_quantized_triangle_edge_incidence_v1`、相対統合許容差`1e-7`、最小`1e-9`。実データでは表示や境界状態が座標精度・面の分割方法の影響を受けることを明記し、完全な多様体・穴無し・内部空洞無しの証明とはしない。

JSONは匿名部品別・全体の**件数のみ**、元頂点/名前/元GLBパスは出さない。ローカルの比較HTMLに部品別境界数を表示し、境界の有無・非多様体候補が異なる部品対応候補はレビュー対象に格下げする（`topology_review_required=true`）。自動コード修正、元GLB上書き、対応確定は行わない。

合成GLBの閉四面体（4面）と1面取り除いた四面体（3面）を各Blender CIで実読込し、境界数0と3、部品候補は`ambiguous`になることを検証。詳細は`docs/GLB_BOUNDARY_AUDIT.md`。GLB-020は一部実装、GLB-021/022は未実装。

### GLB-020 第6段階・実測CI

コードSHA `2cec6c99082107a4f2a65459f36f641b189f3bc5` の [Python 42284401645](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401645)・[Windows 42284401719](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401719)・[Blender 4.4.3/4.5.15/5.2.1 42284401757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401757)・[Windowsキット 42284401594](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401594)・[引き継ぎ 42284401833](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401833) は全て success。 [Chromium 42284401610](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42284401610) は別途結果確認中。

今回の境界エッジ数は数値的近似による観測のみで、穴や内部形状の完全検出の意味ではない。対応候補を曖昧に降格しても因果関係の特定や補修は実行しない。

## GLB-020 第7段階：境界エッジのローカル位置表示

匿名部品の`boundary_edge_audit`で観測された境界線を、**ローカル`compare_viewer.html`の左右3Dビューへ水色線として重ね描き**する。チェックボックスで表示を切り替え、独立の部品セレクターと同期カメラに追従。

`boundary_overlay`は匿名部品番号＋線分両端の数値座標（7要素/本）を含み、**公開可能な集計`review.json`へ保存してはならない**。近接統合の数値誤差とCanvas2DのX-ray的な重ね描きを説明し、実際の穴・完全閉曲面・精密な遮蔽・部品同一性を確定しない。外部通信・ユーザーコード実行・元GLB改変は引き続き禁止。詳細：`docs/GLB_BOUNDARY_AUDIT.md`。

### GLB-020 第7段階・確認済みテスト（2026-11-07）

テスト対象のコードSHA `2a2bc8c33aaf4d11811e7892a8bbc51542b316b4`： [Python 42286544157](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544157)、[Windows 42286544061](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544061)、[Blender 4.4.3/4.5.15/5.2.1 42286543992](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543992)、[Windowsキット 42286543968](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543968)、[引き継ぎ 42286543977](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286543977)、[Chromium実GUI 42286544018](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42286544018) **全6系統成功**。

GUI試験は合成モデルのみ。水色境界線は近接統合とCanvas2D X-ray表示による推定であり、実モデルの穴や閉曲面の証明ではない。

## GLB-020レビューMVP受け入れ・次段階への移行（2026-11-07）

[GLB-020 MVP受け入れテスト仕様](GLB020_MVP_ACCEPTANCE.md)に従い、CBDK自作の3部品GLBで同一モデル・開口縮小・ボール移動・リップ面欠損の4条件をBlender 4.4.3/4.5.15/5.2.1で実テスト。最初の正常モデルに軸の開放端があることを発見し、合成モデルを閉鎖したうえで再検証。

最終テスト対象コード SHA `db33ce4242bbe98b3c5f9ac43d89bf21c3657089`：
[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898364)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898499)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898512)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898604)・[引き継ぎ](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898325)・[Chromium実GUI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42289898701) **全6系統成功**。

**GLB-020のMVPは合格**だが、正確な実モデルの穴・内部空間・完全一致や大規模メッシュは未保証。状態は`partial`、詳細機能追加は凍結。次は`GLB-021`を開始予定（この時点では未実装）。ユーザー私有アドオンの無断実行/編集なし、v0.18ドラフトPRを維持。

## GLB-021 第1段階：GLB-020観測から設定候補レビューへ（2026-11-07）

GLB-020の匿名部品ごとの集計JSON（赤/黄の観測面数・開放境界数）を、既存の`glb_property_map.py` / ASTによる構文参照・形状フロー照合へ接続。利用者の明示的な`--source` PythonファイルのみをASTで構文解析し、**ソースコードを実行しない**。任意の`--role part_003=socket`は**人手で付けた未認証の部品役割**であり、GLBメッシュ名から推測しない。

候補の設定名・宣言行・構文的な使用箇所はレビュー用の**非公開ローカルJSON**に限定し、CLI標準出力やGitHub/Notionに元ソース本文/パス/既定値を送らない。原因・真の部品対応・正しい修正値・Blender登録状態の自動確定はしない。コードSHA `8c51a867415738dcca6616a4a197b62a105075e5`： [Python 42292708122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708122)、[Windows 42292708128](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708128)、[Blender 4.4.3/4.5.15/5.2.1 42292708248](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708248)、[Windows Kit 42292708114](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708114)、[引き継ぎ 42292708111](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708111)、[Chromium実GUI 42292708124](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42292708124) **全6系統success**。

状態はGLB-021`partial`/BlenderCI、GLB-022`not_implemented`。GLB-020の高精度化は凍結を維持し、次のGLB-021の人間レビューと許可済み合成検証を優先。[仕様](GLB021_VISUAL_PROPERTY_REVIEW.md)。

## GLB-021 第2段階：日本語のレビューチェックリスト（非公開）

`glb-visual-property-review --markdown` により、従来のreview-only JSONと同じ名前のMarkdownをローカルの `reports/latest` に**新規作成のみ**で出力する。観測した黄/赤面数・境界辺数と、ASTで完全一致した候補名、クラス名・匿名化されたソースラベル・宣言行、構文的な参照/形状処理経路の件数を分離して表示し、人手での再確認事項を添える。

コードの実行、値の変更、設定の因果判定や推奨数値の作成は行わない。「同じ名前のプロパティが存在する」と「これが原因」を同一視しない。Markdownは候補プロパティ名を含むため**プライベート**であり、公開GitHub/Notion、標準出力、成果物アップロードには使用しない。出力先のパストラバーサル、既存ファイル、外部へ解決されるシンボリックリンクは拒否する。

GLB-021のステータスは一部実装のまま。詳細：[GLB-021仕様](GLB021_VISUAL_PROPERTY_REVIEW.md)。

## GLB-021 第5段階：合成モデル変更履歴

CBDK自作の合成3部品GLBに限り、**狭窄0.78、無関係なボール移動、既知正常1.70への復帰**の固定試験を匿名部品の差分集計としてJSON＋日本語Markdownに記録。入力は既存GLB-020のレビュー集計のみで、任意のユーザーアドオンの実行・値変更を禁止する。

テスト対象コード SHA `ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f`：[Python 42299997255](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997255)、[Windows 42299997246](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997246)、[Blender4.4.3/4.5.15/5.2.1 42299997251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997251)、[Windows Kit 42299997311](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997311)、[引き継ぎ 42299997254](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997254)、[Chromium 42299997355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997355) **全6系統成功**。

機能全体は`GLB-021 partial`を維持。変更効果の履歴はサンプリングした面の集計であって、実アドオン設定の原因・正しい設定値・完全な幾何一致は証明しない。GLB-022の汎用反復実験は未実装。[第5段階の仕様](GLB021_TRIAL_HISTORY.md)。

## GLB-022 第1段階：許可済み合成モデルの固定2試行ループ

CBDK自作合成GLBに対してのみ、明示的に許可した`narrow`→`narrow_placebo`（観測誤差が減らないため不採用）→`identical`（合成モデルの既知正常値へ復帰して採用）の反復処理を実装。各候補でBlenderを`--factory-startup --disable-autoexec`で起動し固定合成GLBを新規生成し、GLB-020の集計差分で判定。観測異常面が減り、他部品の新たな悪化がない場合だけ採用。最大2試行、観測差分0または予算切れで終了。

テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`：[Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)・[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)・[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)・[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)・[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)・[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。

安全性：元GLB/既存ファイルの上書き禁止、実ユーザーアドオンの自動実行・修正・公開禁止、合成入力のSHA-256不変、匿名集計のみローカルJSON/日本語Markdown履歴に記録。固定2試行の合成試験であり、任意値の探索・実GLBの完全一致・本物のユーザー製アドオンの因果特定は未実装。GLB-022`partial`。詳細は`docs/GLB022_SYNTHETIC_ITERATION.md`。

## GLB-022 第1段階：許可済み合成モデルだけの2段階反復（2026-11-07）

CBDK自作生成器の固定値だけでGLBを実際に再生成・比較し、無関係な変更は**棄却**、既知の正常形状復帰は**採用**、観測差分0または最大2試行で停止する試作を実装。入力GLB/ジェネレーターはSHA-256で不変を確認し、匿名の試行・採否・停止理由をローカルJSON/Markdownへ記録。

テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`： [Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)、[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)、[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)、[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)、[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)、[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。

**GLB-022はpartial**。合成モデル専用の固定2候補に限定し、実アドオンのパラメータを自由に探索・適用したものではない。実ユーザーデータ・因果関係・幾何の全域一致は未検証。GLB-020の追加機能は凍結を維持、GLB-021はpartial、v0.18はPR #25ドラフトのまま。[詳細](GLB022_ALLOWLISTED_ITERATION.md)。

## GLB-022 第2段階：他部品悪化を防ぐ複数合成候補（2026-11-07）

CBDK自作ボール/軸/ソケットの3部品だけをBlenderで毎回新規生成し、3候補の差分を再測定。**ソケット改善なし**、**ソケット改善だがボール悪化**は採用せず、ソケット改善と他部品の非悪化を同時に満たす既知正常候補だけを採用。打切り上限とサンプリング差分0の停止を明示。

コードSHA `d8d233e801b4da33f5f79cf6983818cefdca918c`：[Python 42305594556](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594556)、[Windows 42305594566](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594566)、[Blender 4.4.3/4.5.15/5.2.1 42305594589](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594589)、[Windows Kit 42305594635](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594635)、[引き継ぎ 42305594684](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594684)、[Chromium 42305594551](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42305594551) **全6系統成功**。

出力はローカルの匿名JSON・日本語Markdownのみで、合成モデル以外のアドオンやGLBは実行/変更しない。GLB-022 `partial`を維持し、実アドオンのパラメータ自由探索・因果や全形状一致は未保証。[詳細](GLB022_MULTI_CANDIDATE.md)。
