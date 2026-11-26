# CBDK R26 — F021-01 診断・静的宣言・実登録・実測効果の限定照合

2026-11-26 JST。既承認のv0.19→0.22移行方針に従う。**本割当とfuture JSONのdev統合・独立7CI成功・Issue #125 revision 20 active化までは専門実装禁止。** R27/F021-02自動開始なし。GL/DIL独立、main/正式v0.17.0/last_verified/44要件/24 NEXT不変。

## 基点と既存資産
R25節目#176 dev 972736be66515f558c2ba9ef07ba6c5947047118 独立7CI成功（Python45725920249、Windows45725920191、Blender45725920198、Chromium45725920203、Handoff45725920193、Kit45725920338、Skill45725920526）、Notion既存ページ同期済み、#125 rev19 paused。v0.20限定3/3受入。旧GLB-012のCBDK自作 fixtures/cbdk_parameter_experiment.py は sphere_radius / bevel_width のFloatPropertyを登録し、scripts/blender_parameter_experiment_smoke.py は7固定GLBを生成/再import、両方向の変位と非対象部品不変を既に測る。tests/test_glb_parameter_experiment.py は同じfixtureのAST宣言・同一クラス参照・構文フローを確認済み。GLB-021は弱い仮説・AST名照合・初期測定SHAの連携、GLB-022は固定/適応候補・他部品悪化拒否・打切り・checkpointを既に持つ。これらを作り直さない。v0.21の最初の焦点は、同一固定fixtureについて静的観測と実際の登録、読値、形状効果、診断の対応を区別してつなぐこと。

## 共通固定契約（試験内部のみ）
主対象は既存2プロパティと既存7 variantの順序・値を変更しない。対象/非対象は sphere_radius→CBDK_Param_Sphere / CBDK_Param_BevelCube、bevel_width→CBDK_Param_BevelCube / CBDK_Param_Sphere。case IDは parameter_fixture_r26、run_idは信頼済みA親が発行する32 lowercase hex、source_sha256は実際に読み/実行した既存固定fixtureの64 lowercase hex、Blenderは4.4.3/4.5.15/5.2.1。固定試験の型/識別子以外の自由文やパスは集約しない。静的情報は property, declaration_count, same_class_self_count, geometry_path_count, expected_api_observed の固定観測、実機は property, registered_on_expected_instance, value_readback_verified, target_changed_generated, target_changed_imported, unrelated_unchanged_generated, unrelated_unchanged_imported の固定観測、run共通 cleanup_verified と source_unchanged。B/Cはそれぞれ内部helperを返し、Dは固定case/version/run/source SHAとproperty集合（各1回）を検査する。Aの親は期待値を入力観測から逆算しない。boolと整数の混同、欠損/重複/異なるsource/run/version/prop/偽承認は拒否またはincomplete。実測変位と既存比較の元記録を照合し、単なるマーカーの成功を段階証明にしない。SHAは整合性で真正性/権限を証明しない。

## B — 静的設定候補・診断照合
branch work/v021-glb-r26、専門PR1件。既存 glb_property_map / glb_property_usage / glb_geometry_flow / glb_diagnose / glb_repair_plan を利用し、固定fixtureだけの明示的な内部観測helper、B専用tests/docsを担当。既存公開API/一般的な仮説強度や形状判定を変更しない。sphere_radiusのprimitive_uv_sphere_add、bevel_widthのmodifier.widthの構文観測を同一クラス宣言と照合。重複宣言・別receiver・同名別クラス・経路無しを合成AST負例で区別し、未登録・未実行・因果未確認を静的証拠だけで成功扱いしない。既存診断カテゴリと固定fixtureの候補対応は明示的な試験用対応で、実アドオンに一般化しない。Blender既存7 variantの実機回帰を5CI/3版確認し、静的helperの実測結合はAへ渡す。既存 watched tests/test_glb_property_map.py に関連する回帰を追加可能。C/D/共有CLI/CIは編集しない。

## C — 実プロパティ登録・読値・実形状の観測
branch work/v021-ui-r26、専門PR1件。既存 scripts/blender_parameter_experiment_smoke.py、C専用helper/tests/docsのみ担当。既存fixture source、7 variant、旧marker/reportと測定を維持し、新規報告を付加する。実際の登録済みPropertyGroupのRNA型、Scene pointerの実インスタンス/宣言クラス、実値設定と読戻しを各variantで観測。既存生成/再importの変位・非対象不変を再利用（sphere/bevelを取り違えない）。解除後に所有pointer/class消失を確認、元fixture SHA不変。静的同名が未登録でも実登録を証明しない負例はテスト専用の独立観測で確認可能。B/DのhelperやAの共有CI/CLIは変更しない。内部でA親からrun_idを受け取れる形とし、専門単独では独立runを明記。5CI/Blender3版の実測で停止。

## D — 証拠の厳格照合・不足判定
branch work/v021-quality-r26、専門PR1件。新規の小さな内部 evidence reducer/validator、D専用tests/docsのみ担当。R25のfail-closed原則を再利用、静的とnativeの共通case/version/run/source SHA・固定property各1回・型・正負の観測・cleanup/source不変を照合。別実行/別fixture/別property/欠落/矛盾/未知値はverifiedにしない。静的候補のみ、登録のみ、対象効果未観測、非対象変化、cleanup未確認を区別、測定値の原因・最適値・権限・自動採用はfalse。固定の理由コードのみ。Python制御負例と既存native 7 variant回帰を5CI/3版で確認。Aの観測元を偽造して成功扱いしない。既存 watched tests/test_glb_experiment_triage.py に異なる測定元・過大主張拒否の関連回帰を追加可能。B/C/共有CLI/CIは編集しない。

## A — 同一実行の縦断統合・限定受入
Aは共有CI、信頼済み親runnerと固定集約helperの接続を担当。親からfresh run ID・fixture SHA・正確なmatrix versionを固定し、BのAST観測、Cの実機登録/読値/効果/解除、Dの厳格集約を同一固定source/runで結ぶ。既存7 variantの比較値・GLBのSHA・結果を実観測に紐付ける。既存4.5.15のradius_regression（差異exit1は期待正常）を保持し、同じ固定球の実GLB診断と対応候補の縦断を残り2版でも必要最小限に確認する。bevelは外寸不変でも頂点効果が観測される対照で、診断が検出していないカテゴリや原因を捏造しない。F021-01の限定受入は各担当5CI＋A結合5CI＋dev独立7CIと全3版の構造化記録照合後のみ。現段階ではコード修正候補生成・自動適用・探索拡張・実ユーザー実行は行わない。F021-02/03は後続の限定判断。
