# CBDK R23 — v0.20生成エンジン最初の限定縦断（C/D）

2026-11-26 JST。ユーザー継続指示に基づく既承認F020移行/正式割当候補。**本書とfuture JSONのdev統合・統合HEAD独立7CI成功・Issue #125 revision更新まで専門実装禁止。** B待機、GL/DIL独立。R24自動発行なし。

## 基点・残条件

dev 1540ad4e7d7e41304b81cbdcc8ee65d3ac8b2791 独立7CI（Python45644535642、Windows45644535499、Blender45644535704、Chromium45644535823、Handoff45644535761、Kit45644535523、Skill45644535575）。実Blender jobs139311833554/139311834305/139311834496でR22/R21 marker、16合成ケース固定8/10・適応9/10、情報欠落1、旧profile/SHA保持。#25同HEAD draft、#125 rev13 paused、既存Notion節目同期成功。F019限定3/3は受入済みだが任意実モデル・一般精度・物理診断・native memory・大規模viewerは未完。v0.20は既承認計画の順序に従う。44要件/24 NEXTの状態変更、main/正式版/私有データ/直接GitHubインストールなし。

R19で6コード所有機能/7部品、float_vector/int、固定単一panel内のrow/column・mode・inline UI、登録失敗cleanup、固定2機能の同一生成ZIP Extension runtimeを実証済み。既存の機能/入力/依存/検査は再実装しない。現在のui_layout schema1は単一panel内sectionを選ぶだけ、extension_authored_fixtureは固定recipe/固定inventoryのみ。今回の差はこの2点。新機能の数を増やすだけの作業は禁止。

## C / F020-01 — 明示複数panelの宣言構成

枝 work/v020-ui-builder-r23、専門PR1件。既存schema1と6 legacy recipes、R18/R19の単一panel/2型登録・既存operator ID/実行guardをそのまま保持。別の明示opt-in（例：UI schema2）で、既存コード所有機能を2つの固定panel slotへ分ける最小の生成経路を追加する。panel slot ID/class/RNA/operator/モード/依存/入力型はコード所有、JSONは許可slot選択・ラベル・section・既存入力値の制限付きデータのみ。任意Python、任意class/パス、型/上限の拡大、未知キーは拒否。既存build_modular/plan_modular_recipeの共通検証を再利用し、旧schemaの出力を維持する。

- 既存read-only機能（mesh_bounds/mesh_center）とedit機能（edit_selection/vertex_nudge）を含む2panelの自作recipe、同機能を別の順序/配置にした第2recipeを固定。独立期待でpanel draw/表示・登録数・型付きprecision/offset・実operator結果・対象外選択/モード取消無変更・解除を検証。重複slot/section/feature、未選択/未許可feature、隠れて到達不能なmode、登録衝突/部分登録失敗→原状維持・再登録を負例とする。2panel以内、既存section/recipeサイズ上限を緩めない。第三者addon/実GUI Ctrl+Zは未検証として残す。旧nudge Scene property互換を壊さない。
- C所有：cbdk/ui_layout.py、cbdk/feature_catalog.py、cbdk/modular_builder.py、cbdk/registration_audit.py、templates/modular_preview/、C専用tests/docs、既存C native lifecycle。catalogは既存6機能の契約に必要な場合のみ。共有CLI/CI/parts/STATEはA、D extension系は読取専用。既存の不具合を再現した最小変更、5CI・3版実markerまで。新型/新機能追加は今回なし。

## D / F020-03 一部 — 自作レシピからの非配布Extension準備

枝 work/v020-extension-quality-r23、専門PR1件。R19固定fixtureを維持。現在のschema2 modular recipe（既存schema1 UI含む）を、信頼済みチェックアウトのbuild_modularからその場で生成し、既存preflight/manifest検証と出自byte照合を再利用してローカル試験用Extension root ZIPへ組み立てる最小の再利用経路を追加。Cの新schemaは待たず既存契約で検証できる。外部ZIP/任意root/任意Python/任意メタデータによる実行許可は禁止。固定test-only ID/metadata/SPDX（法的承認でない）、出力fresh/上書き拒否、member閉包/size/重複/パス安全/決定性/元SHA不変、release_authorized/install_authorized/approved=falseを保持。選択機能とhelper閉包は既存コード所有allowlistおよび独立期待で照合し、自己申告hashだけを信頼しない。既存R19 fixture byte/挙動維持。

- 既存の異なる2 recipe（read-only複数機能とeditを含む複数機能）を実生成し、公式extension validate、隔離offline local repoで実ZIP enable→独立期待のbounds/centerまたはvertex_nudge編集結果→disable/残存登録なしを3版で確認。編集対象外不変、無効選択/モードで取消、旧legacy経路回帰。同一IDの変種は逐次隔離、同時install不可。一般公式installer/配布/ライセンス承認は別、公開の実行可能成果物配布なし。失敗時は原因を安全な診断とともに記録。D所有：cbdk/extension_*.py、D専用tests/docs、scripts/verify_authored_extension_runtime.py等既存D検証入口。C builder変更はA経由、共有CLI/CI/STATEはA。5CI・3版実markerで停止。

## A / 統合と終了

C/D独立実装の後、Aが必要な共有CLI（明示preview opt-in・安全な入力/出力・失敗理由、既存CLI互換）/CI接続を最小実装。同一のC新recipe→生成ZIP→D Extension root ZIP→公式validate→隔離runtimeで両panel・typed値・read/edit・cleanupを縦断実測し、別々の成功を同一物の証拠にしない。実入力は自作合成のみ、任意ユーザーコードや権利未確認素材を実行/公開しない。専門各5CI、結合5CI、統合後独立7CI必須。F020-01/03の今回達成範囲を分けて記録し、F020-02（依存/複数機能の一般組み立て）残りは別判断。v0.20全体完成・R24自動発行なし。Bは新規PR/CI不要。
