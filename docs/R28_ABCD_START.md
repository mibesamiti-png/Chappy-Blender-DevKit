# CBDK R28 — F021-03 固定合成ソース候補の比較・副作用拒否・停止

2026-11-26 JST。**本割当とfuture JSONのdev統合・独立7CI成功・Issue #125 revision 24 active化までは専門実装禁止。** R29/v0.22自動開始なし。GL/DIL独立、正式v0.17.0/main/last_verified/44要件/24 NEXT不変。

## 既存資産・限定目標

R27節目#189 dev 0e62d85f0c657f909ea3336d81378cf24ae2c42f、独立7CI（Python45771553334、Windows45771553321、Blender45771553369、Chromium45771553315、Handoff45771553377、Kit45771553314、Skill45771553459）成功、Notion同期確認、#125 rev23 paused。F021-01/02限定受入。GLB-022は固定/適応候補、厳格改善・他部品悪化拒否・予算・停止・失敗/不完全履歴を実装済み。再実装・一般化せず判定原則を再利用する。R26は固定7 variantの実RNA/生成/再import/計測、R27は固定ソース差分・隔離コピー・逆変換・親証拠を実証済み。R28で追加するのは同じ固定ソースからの複数候補と、実測による選別・拒否・停止を結ぶ限定縦断。

## 固定契約（内部CIのみ）

元 fixtures/cbdk_parameter_experiment.py SHA256 e645723ff89a99530841e1ccd37ea8d059952eec0f980ac1782d8228e46588e3。元の既定値 sphere_radius=0.75, bevel_width=0.08。対象 CBDK_Param_Sphere、保護 CBDK_Param_BevelCube。基準は同一jobのR26 baseline、目標は sphere_radius_changed（1.15, 0.08）。R26全7 variant・R27の固定0.75→1.15実験・既存marker/回帰は維持。

| 試行順 | 固定ID | sphere_radius | bevel_width | 同一job R26参照（sphere / cube） | 期待判定 |
| --- | --- | ---: | ---: | --- | --- |
| 1 | wrong_direction | 0.55 | 0.08 | sphere_probe_down / sphere_probe_down | target_regression |
| 2 | cross_part | 1.15 | 0.20 | sphere_radius_changed / bevel_probe_up | protected_part_regression |
| 3 | intermediate | 0.95 | 0.08 | sphere_probe_up / sphere_probe_up | observed_improvement |
| 4 | target | 1.15 | 0.08 | sphere_radius_changed / sphere_radius_changed | observed_target_reached |

cross_part は副作用を実測するためだけの唯一の固定2トークン負例。許可変更は上記固定クラスのFloatProperty default数値のみ。任意の複数編集、自由値、外部パス、任意コード、公開CLIは禁止。各候補は直前候補ではなく固定元から独立生成。実行するのは許可された全バイト列と完全一致する検査済みbytesのみ。独立のAST比較・唯一の許可トークン位置・元/候補SHA・逆変換・復元完全一致を確認。各試行は新規隔離領域の固定名コピーを original/candidate/restored の3段階で実行し、明示値代入なしで実RNA既定値、実GLB生成/再import、cleanup、元/参照不変を検査。失敗時はfinallyで復元/解除を試み、成功としない。cross_part の参照は二つの既存variantから部品ごとに取り出した測定であり、既存の混合GLBがあるとは主張しない。元/復元は同じR26 baseline測定。候補後に物理ソースを採用状態へ書換えない。

## 判定契約（B/D/A共通）

case_id=parameter_source_r28、親発行run_id=32 lowercase hex、blender_version=4.4.3/4.5.15/5.2.1、source_sha256=固定元SHA、reference_run_id=同一jobのR26親ID（R28とは別）、trial_id=上記4値、candidate_sha256=実際の許可候補bytesのSHA。各段階のactual_source_sha256、実RNA before/after、登録/解除、GLB SHA、generated_mesh/imported_glb_mesh（R27と同じ固定2部品・頂点/面数・座標SHA・world_dimensions）を使う。親が実ファイル/測定から独立確認。GLB byte同一性を形状一致の必要条件にしない。

評価指標は固定球体の目標world_dimensionsとの差の3軸最大絶対値を、generated/imported別々に測る（座標単位、許容差1e-5、有限値・正の寸法・固定部品/版、既存R26/R27の丸め計測）。これは部品限定寸法スコアであり任意形状等価/表面距離/最適値ではない。保護cubeは両段階で固定baselineの全測定と一致必須。採否はまず証拠妥当性、次に保護部品の不変、次に現在の仮想bestと両段階のスコア比較。両方がmargin超で悪化→target_regression、両方がmargin超で改善→observed_improvement。片側だけ改善/悪化、同点/差不足はuncertain_no_strict_improvementとしてbestを更新しない。観測目標達成は両段階のscore<=marginかつ球の全固定測定が目標と一致、保護部品も不変、すべての証拠成立時のみ。寸法だけ一致したが全固定測定不一致ならuncertainとして採用しない。保護部品悪化は目標スコア0でも優先棄却。欠落/不正/別run/別版/復元失敗はincomplete/rejected、正常完了や採用扱い禁止。

初期best=baseline。棄却時best不変、intermediateで仮想best更新、targetで仮想best更新・停止。期待score（設計値、実測で確かめる） baseline 0.8、wrong_direction 1.2、cross_part 0、intermediate 0.4、target 0（generated/imported各）。最大4候補、順序固定、target前に終了ならbudget_exhausted/incompleteで目標達成を出さない。予算1/2/3の検証は実測済みprefixのPython replayでよいが、実機で別々に途中停止を試験したとは記録しない。失敗/不確実/偽成功の負例はPython制御と実機観測を区別。bestはレビュー上のIDのみ。実ソースや作業コピーへ採用変更を残さず、auto_apply/auto_adopt/auto_approve=false。

## B — 固定候補の形状評価・履歴

branch work/v021-glb-r28、専門PR1件。新規 cbdk/parameter_candidate_review_r28.py、B専用tests/docs、既存 watched tests/test_glb_property_map.py の関連回帰のみ可。R26/R27の固定計測とGLB-022の厳格改善/保護/予算原則を再利用し、固定測定の純Python評価・best遷移・停止/不確実判定を実装。内部関数は上記固定trial ID順と同一job基準/目標測定、候補のgenerated/imported測定、budget=1..4を受け、順序付き判定/各スコア/仮想best/停止理由を返す。外部パス/任意設定/コード実行なし。Bは実測入力の評価であり証拠真正性を主張しない。両段階改善・悪化、保護優先拒否、同点・片側改善、寸法一致だが座標不一致、欠落/型混同/順序/予算/偽bestの負例。5CI/3版の既存回帰。C/D/共有CI変更なし。

## C — 4固定ソース候補の実測・隔離復元

branch work/v021-ui-r28、専門PR1件。新規 scripts/blender_parameter_source_r28_smoke.py、scripts/parameter_source_r28_copy.py、C専用tests/docs。専門CIを起動するため既存 scripts/blender_parameter_r27_parent.py の __main__ 内の run() 後にR28専用入口を呼ぶ最小hookだけ許可（run()本体、R27既存モジュール・共通CIは不変）。R27の固定SHA、readback/cleanup/検査済みbytes実行/GLB snapshotパターンを再利用。4候補をそれぞれ元から独立に派生、隔離コピーの original/candidate/restored で実RNA・生成/再import・SHA・復元を採る。2トークン負例以外の複数編集は禁止。固定trialごとに新規作業ディレクトリを使用し、実コピーを読み検査したbytesのみcompileする。元/全7参照/R27成果物は変更しない。実行前後/各stageの計測時点でAが実コピー・実GLB・mesh/RNAを観測できる内部callbackまたは観測hook契約を文書化し、独立計測を可能にする。専門単独は独自run ID、A統合時は親指定run ID/版/元SHAを受ける。native.json/details.json等は固定出力、実測stageごとの観測と参照run IDを含める。判定はB/Aに委ね、成功markerは全stage/cleanup/復元成功のみ。5CI/Blender3版の新規実測。B/D/共有CI変更なし。

## D — 厳格な候補・判定・履歴の独立照合

branch work/v021-quality-r28、専門PR1件。新規 cbdk/parameter_candidate_evidence_r28.py、D専用tests/docs、既存 watched tests/test_glb_experiment_triage.py の関連回帰可。R27 reducer/R26親identity・GLB-022の履歴replay/fail-closed原則を再利用。親が独立に渡す許可候補bytes由来のSHA/差分/逆変換、同一job参照・actual source/GLB/RNA/mesh、元/参照/復元不変、4試行×3段階、Bの決定履歴を照合。Bモジュールへの直接依存なしで上記ルールを再計算、予算1/2/3のprefixと4完走、棄却でbest不変、target前の成功拒否、保護部品悪化優先、未知ID/重複/順序/型/非有限/別run/版/SHA/復元不一致/偽採用を拒否。欠落はincomplete。固定reason codeのみ、任意コード実行/適用なし。Dの合成負例は実測成功でない。5CI/3版の既存回帰。B/C/共有CI変更なし。

## A — 実測縦断と正式受入

AがR28親identityと固定許可候補を独立に導出・AST/byte/逆変換検査。R27親 run() をそのまま呼ぶ新規A統合入口で旧R26/R27を維持し、C専門hookとは二重起動しない。実コピー・GLB SHA・R26参照・実RNA/meshの親観測とC記録を結び、B評価とD独立replayを照合。既存R26全7・R27全stageを保全。4試行×3stageの実測を3版で確認し、期待判定/停止・保護不変・復元を実際の証拠から確認。prefix budget/失敗制御はPythonテストと明記。各担当5CI＋A5CI＋dev独立7CI、3版nativeログを受入条件。専門とAの同じ成果を二重計上しない。F021-03限定受入まで、v0.22/R29移行は別判断。main/正式版/権利/任意ユーザーソース/自動適用は範囲外。
