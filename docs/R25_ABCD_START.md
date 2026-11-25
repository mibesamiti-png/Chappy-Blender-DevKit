# CBDK R25 — F020-03 同一生成物の検証証拠とUndo境界（C/D）

2026-11-26 JST。既承認v0.20計画・継続指示。**この割当候補とfuture JSONのdev統合・独立7CI成功・Issue #125の新revision active化まで専門実装禁止。** B待機、GL/DIL独立。v0.21/R26自動開始なし。

## 基点・既存資産
R24節目#171 dev 54bfd42b5e5b466b284f066e1411e13ea4f9d147 独立7CI成功（Python45712768029、Windows45712768042、Blender45712768257、Chromium45712767969、Handoff45712767974、Kit45712767942、Skill45712768072）、Notion既存ページ同期済み、#125 rev17 paused。F020-01/02限定受入、F020-03 partial。既存の6 legacyレシピ＋R18追加・R23 read/edit/grouped・R24 dependencyの静的/実機試験は再利用。blender_undo_redo_smoke.py は単一/複数頂点の明示ed.undo_pushと正確な座標/接続/選択・取消不変を検証済み、通常背景Undoはunavailableの実績。undo_probe_report.py はschema1/2互換とGUI未確認を強制。extension_preflight.py の安定した失敗category/code、recipe_matrix.py の静的証拠、extension_recipe_preview.py の決定的生成・承認false、verify_recipe_extension_runtime.py の固定ZIP再生成照合・隔離実行を再利用する。既存の成功を再実装しない。

## 共通固定契約
R23 grouped（2panel/4機能/2型、実カタログ変更なし）の既存信頼済みrecipeを同一ZIP縦断の主対象にする。read/editは既存回帰を保持。既存CI内部の合成fixtureのみ。記録単位は固定case ID、対象Blender正確版、同一実行内の生成ZIP SHA-256、stage。成功stageは生成、公式validate、隔離enable、基本read/edit、cleanup/disable、入力SHA不変。Undoは自然な背景履歴と明示pushの制御実験を分離し、GUI未確認固定。failure stageは後続成功にできない。欠損/重複/不一致/未知値は検証不能または拒否、失敗理由を固定語彙化。ハッシュ一致は同一バイトの照合であって真正性/ライセンス/承認ではない。任意外部ZIP・コード・root・ログを実行許可に変換するAPIは作らない。

## C — native Undo/Redoの再利用と境界
branch work/v020-ui-builder-r25、専門PR1件。C所有は既存 scripts/blender_undo_redo_smoke.py、cbdk/undo_probe_report.py、専用tests/docs・必要なテスト専用helper。既存単一legacy ZIPのprobeとschema1/2、既存CI markerを保持。実機で既存固定生成物から単一/複数頂点（2操作）と取消の完全状態を照合。既存run_caseの再利用を優先、隔離Extensionの既存登録済みoperatorにも呼べる内部helperを用意しAへ渡す（独自installerや公開入口なし）。対象は同一grouped ZIPを登録中のvertex_nudge、通常背景履歴と明示pushは別条件、利用不能ならunavailable/not_attemptedを正しく記録。Undo/RedoごとにRNA/BMeshを再取得、座標・接続・全選択・未選択不変、取消と cleanupを検証。明示push成功で通常履歴・GUI Ctrl+Z/Redo成功を主張しない。旧report schemaを壊さない。実際に再現した問題以外の製品コード修正なし。5CI・Blender3版の明示証拠で停止。

## D — 固定生成物の証拠集約と失敗理由
branch work/v020-extension-quality-r25、専門PR1件。D所有は新規の小さな内部 evidence reducer/validator（既存preflight/manifest診断を再利用）、D専用tests/docs。Aの共有CLI/CI・CのUndo実装を変更しない。共通契約をもとに固定信頼済みCI実行で得るstage recordを構造化し、版・case・artifact digestの一致、成功順序、欠落/重複/矛盾、後続stageのnot_run、承認false、GUI/公式installer/権利/配布未確認を検証。固定分類例 generation_rejected / validate_failed / enable_failed / operation_failed / cleanup_failed / evidence_mismatch / incomplete_evidence。生ログ・例外任意文字列・パスを公開レポートへ転記しない。失敗は合成制御負例としてPythonで再現、実際のBlenderでは固定groupedと既存read/editの独立stage観測を3版で照合可能にする。未知の実行入力や任意ログの真正性を保証しない。Aへ固定recordの契約と集約関数を渡す。5CI・3版native証拠で停止。

## A — 統合・限定フェーズ判断
C/Dの結果を同一固定grouped ZIPの既存official validate→隔離offline bl_ext登録→read/edit→Undo制御実験→解除・SHA不変に接続し、旧read/edit/grouped/dependency markerを保持。既存 scripts/verify_recipe_extension_runtime.py / scripts/verify_extension_manifest.py と共有CI・証拠保存はA所有、必要最小限のみ変更。別プロセスのUndo実測を同一artifactとして流用しない。失敗・未実行・GUI人手確認を成功に集計しない。各担当5CI、A結合5CI、dev独立7CI、全3版marker/構造化report・同一SHA・cleanupの証拠を確認。F020-03の限定受入とv0.20終了は実証後に別判断。main/正式v0.17.0/last_verified/44要件/24 NEXT/私有データ/権利/配布は不変。公式installer・GUI実操作・任意コードは対象外。
