# CBDK R27 — F021-02 固定合成ソースの単一変更候補・復元・再生成比較

2026-11-26 JST。**本割当とfuture JSONのdev統合・独立7CI成功・Issue #125 revision 22 active化までは専門実装禁止。** R28/F021-03自動開始なし。GL/DIL独立、正式v0.17.0/main/last_verified/44要件/24 NEXT不変。

## 既存資産・新規範囲

R26節目#183 dev 0b0418729295649c2cadd7bdacb1ca9fe8cfb64b、独立7CI成功（Python45752209622、Windows45752209655、Blender45752209618、Chromium45752209661、Handoff45752209582、Kit45752209700、Skill45752209593）、Notion同期済み、#125 rev21 paused。F021-01限定受入。GLB-012/R26は固定fixtureのRNA・7 variant・GLB再import・定量計測・診断照合を既に持つ。GLB-021は初期集計SHA連携、GLB-022は固定/適応試行・他部品悪化拒否・予算打切り・checkpointを既に持つ。これらを作り直さない。R27は未検証の**ソース差分の生成・作業コピーの保全/復元・実際の既定値から再生成**に集中する。

## 固定契約（内部CIのみ）

元の fixtures/cbdk_parameter_experiment.py のSHA256は e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3。対象は CBDKParameterExperimentSettings.sphere_radius の FloatProperty default の数値トークン1箇所だけ、0.75→1.15。bevel_width default=0.08は不変。既存7 variantは不変、既存 sphere_radius_changed.glb を固定参照にする。既知の実験値であり修正の最適値・一般原因・実ユーザー推奨ではない。元ファイルを編集せず、毎回新規の隔離作業ディレクトリ内に固定名のコピーだけを生成する。candidateの逆差分で元バイト列に完全一致する復元を確認。任意ソース/パス/パッチ/設定値/コードを受け付ける公開CLIを作らない。固定元SHAかつ唯一の旧トークン、許可されたAST差分、他バイト不変を検査。候補を実行する前に実際に読んだバイト列が固定元から導いた許可候補と完全一致することを検査し、検査済みバイト列のみを実行する。未検証コピーのimport、外部コード・任意exec・実ユーザー入力なし。SHAは整合性で真正性や権利を証明しない。

case_id=parameter_source_r27、run_id=親発行32 lowercase hex、blender_version=4.4.3/4.5.15/5.2.1、source_sha256/candidate_sha256=64 lowercase hex、property=sphere_radius。Bは固定候補の before/after 数値・旧新トークン・byte offset・単一差分・元/候補/逆変換SHAを報告（自由文・外部パス不要）。Cは original/candidate/restored の3段階それぞれ、actual_source_sha256、実RNA sphere_radius/bevel_width 読値、登録/解除、生成/再importの既存固定2部品の頂点/面数・座標SHA・寸法、GLB SHA、元ソース/参照SHA不変、実際の逆変換復元、失敗時cleanupを報告。Aが既存R26同一jobのbaseline/changed参照と結び、元/復元は同じ固定計測、候補は既知参照と同じ固定計測、非対象は全段階で不変を検査。GLBのバイト同一性を形状一致の必要条件にしない。座標SHA/寸法は固定モデル内の限定観測で一般形状等価ではない。

## B — 固定候補の生成と逆差分

branch work/v021-glb-r27、専門PR1件。既存AST解析と固定R26 helperを再利用。新規内部 cbdk/parameter_source_candidate_r27.py、B専用tests/docsのみ。固定元を読み、正確なクラス・宣言・default数値トークンの位置を検査し、唯一のバイト差分で候補を組み立てる。候補ASTを比較して許可された1値以外の変更を拒否し、逆変換で元SHA/バイト一致。純Pythonの固定契約・重複/別クラス/不正SHA/複数編集/未知値・復元不一致の負例。候補bytesと固定構造化観測をAへ渡せる内部関数にする。候補実行や書込は担当しない。既存watched tests/test_glb_property_map.pyの関連回帰追加可、5CI/Blender3版の既存回帰。C/D/共有CI変更なし。

## C — 隔離コピーの実RNA・再生成・復元

branch work/v021-ui-r27、専門PR1件。新規 scripts/blender_parameter_source_r27_smoke.py、C専用helper/tests/docs、既存 scripts/blender_parameter_experiment_smoke.py の末尾に限定した呼出しのみ担当。既存7 variant/report/marker・R26観測を保持。専門単独では固定元SHAと独立の厳密な許可トークン置換から候補を構成し、A統合時はB候補との完全一致を親が検査できる契約にする。新規一時作業領域の固定名コピーに候補を作る。元・候補・逆変換で復元したコピーをそれぞれ新規登録状態で実行し、値を明示代入せず実RNA既定値を読み、既存operatorからGLB生成/再import、固定2部品計測を採る。各段階で登録解除/Scene pointer/class消失、コピー内容SHAを検査。失敗はfinallyで隔離コピー復元/解除を試み、失敗時に成功を出さない。検査済み固定バイト列以外を実行しない。元fixture・R26 GLBを変更しない。専門nativeログに3段階と復元/cleanupの観測を出す。5CI/3版実測。B/D/共有CI変更なし。

## D — 変更範囲と復元・測定証拠の厳格検査

branch work/v021-quality-r27、専門PR1件。新規内部 cbdk/parameter_source_evidence_r27.py、D専用tests/docsのみ。R26 reducer/R25 stage契約のfail-closedを再利用。独立親identity、固定property、候補・元SHA、単一差分と復元SHA、段階original/candidate/restored各1回、実値、測定元/GLB SHA/非対象不変、解除/元不変を照合。欠落/重複/型混同/異なるrun/版/SHA/余分な変更/復元不一致/不明な測定/偽成功・承認を拒否またはincomplete。任意のコード実行/適用なし。実測成功はAの信頼済み親が実際のファイル/測定から確認する。固定負例と既存watched tests/test_glb_experiment_triage.py関連回帰可。5CI/3版の既存回帰。B/C/共有CI変更なし。

## A — 固定差分・実コピー・測定の縦断統合

Aが新規親run ID・元SHA・matrix versionを発行し、Bの候補bytes/差分を独立期待で照合、Cの実行したコピーと復元・段階実測、既存R26 baseline/changed GLBと測定を同一jobに結び、D厳格検査を呼ぶ。既存R26の全7 variant、旧検証を保持。元/候補/復元の実際のコピーSHA/GLB/報告を再計算し、候補と既知参照の固定寸法/座標等、復元と元の固定測定、非対象不変を確認。独立親期待を報告から逆算しない。Cの専門単独候補とA統合の結果を二重計上しない。各担当5CI＋A5CI＋dev独立7CI、全3版実測ログで限定受入。失敗経路のPython制御負例と実機での通常復元を区別。複数候補の採否・一般的な原因/最適化・自動適用・実ユーザーソース・配布は範囲外。F021-03は別ラウンド判断。
