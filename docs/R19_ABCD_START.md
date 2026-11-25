# CBDK R19 — v0.18の残る生成経路を一括で接続（C/D限定）

2026-11-25 JST。R18受入と節目同期を完了し、ユーザーの継続指示に基づきAが既存完成条件の残る2点を選定。**本書のdev統合・統合HEAD独立7CI成功・Issue #125 revision更新までは実装禁止。** B待機。これは新しい研究ラウンドでもv0.19開始でもない。

## 基点証拠

#142 dev 36d4090402f66f49d5644fbef91f1c03d95a6b34 独立7CI、3版各67 lifecycle・R18両center・合成ZIP公式build/validate・HIT/SHA成功。#143節目同期dev `2696a9b8e171a218b67865ba5caf47f1786164bf` 独立7CI全成功：Python45549944865、Windows45549944815、Blender45549944774、Chromium45549944754、Handoff45549944856、Kit45549944839、Skill45549944762。Issue #125 revision5 paused。正式v0.17.0、44要件/24 NEXT、次期active=false維持。

## C / UI-001・BUILD-001 — 型付き入力の共通化を既存6機能で実証

専用枝 `work/v018-ui-builder-r19`。現在のui_layoutはvertex_nudgeのoffset専用分岐とnudge_offset計画、runtimeはFloatVectorProperty固定。R18のコード所有feature descriptorを使い、**入力契約の検証→計画→RNA登録→描画→operator参照→解除を再利用可能な最小の共通経路へ**。第7機能を増やす必要はない。

- 既存float_vector offset（3要素、有限・非零default、範囲縮小のみ、既存実行時監査）を維持し、もう1種の意味のある小さな入力を既存read-only mesh_centerへ追加する。例：表示小数桁数 int 0..6、既定3桁。新規形状変更なし。別の入力が適切なら同等に限定し理由を記録。コード側で許可したfeature/parameter/type/RNA名/安全上限のみ; JSONは値/許可範囲のみ指定。任意RNA、式、import、operator、型追加、範囲拡大を拒否。
- 旧6レシピ、旧global/inline UI、従来nudge_offsetの計画互換・property/登録・結果、R18 center既定出力を保持。新しい入力の明示設定をglobal/inlineで実測し、変更値が実operatorの独立期待結果へ反映されること、未選択の新規propertyを登録しないこと、無効値/未知キー/type混同/衝突/登録失敗の既存後片付けを維持。既存propertyのライフサイクル契約を無断変更しない。任意新規機能の自動登録はv0.20以降の範囲。
- C許可: cbdk/ui_layout.py, cbdk/feature_catalog.py, cbdk/modular_builder.py, cbdk/registration_audit.py, templates/modular_preview/, catalog/addon_features.json, catalog/ui_layouts.json, C専用tests/docs/既存native lifecycle entrypoint。recipe_matrixは必要な場合だけ理由をAに伝える（旧6レシピ独立期待維持）。共有CLI/CI/parts/STATEおよびDファイルはA経由。専用PR1件、5CIと3版の実行マーカー。完成に必要な2型の実証で停止。網羅的なRNA型/管理システムを増やさない。

## D / EXT-001 — 動作するCBDK自作previewを隔離Extension試験へ

専用枝 `work/v018-extension-quality-r19`。R18の固定sentinel合成ZIPは非インストールであり維持する。**現在の自作modular builderから、固定の内部CI用レシピを実際に生成し、Extension形式のZIPへ組み立て、公式validateと隔離Blenderで登録・operator実行・解除まで検証する**。対象はコード所有の既知read-only mesh_bounds/mesh_center（R18基点で実行可能）、既存の自作helperのみ。実ユーザーソース、任意ZIP変換、実配布、一般インストール機能は今回禁止。

- 既存builderを信頼した固定recipeから同じプロセスの一時領域に生成し、既存preflightで検査、正確なmember inventoryと生成元bytesを照合したうえでroot layoutへ変換。外部ZIPや自己申告hashだけで実行対象を認めない。manifestは明示的なCI用metadataと専用テストID・test-only SPDXサンプル（法的選択ではない）から既存review/roundtripを再利用。実部品の承認フラグは変更しない。必要ならlegacy bl_infoの扱いを公式仕様に照らして限定処理・検証する。出力は一時領域のみ、固定上限、重複/unsafe path/上書き拒否、release_authorized=falseを保持。外部入力・アーティファクト公開/配布なし。
- 公式Blender extension validateで実ZIP成功を確認し、必要な場合official buildも利用。隔離されたfactory-startup/disable-autoexec/一時user config・extension repositoryで、実際のExtension namespace下の登録/enable→既知の非対称mesh center/boundsの期待値照合→disable/unregister/残存登録なしを対象3版で実測。正式インストールの一般機能、GUI、自動採用、ネットワークアクセスなし。CLI installの実行可否と登録の証拠を区別し、単なる通常Python importを公式Extension runtimeと称さない。手法が成立しなければ原因を証拠化しAへ。合成fixtureのR18公式build/validateと旧preflightテストを保持。
- D許可: cbdk/extension_*.py、D専用tests/docs、scripts/verify_extension_manifest.pyと専用の隔離runtime検査スクリプト。C側builder/feature/UIは読取専用。共有CI設定・CLI hookが必要ならAへ明確な最小変更要求。既存3版の検証入口を再利用し、個別PR1件・5CI・3版実物検証で停止。コードの実権利・一般配布・実ユーザーソース変換は別承認。

## B / GLB — 待機

NEXT-007/008/009は個別に許可された実GLB・実プロパティ因果の確認が残る。空PR、追加合成研究、新規CI不要。GL/DIL研究は独立。

## A / 統合と終了

C/Dは並行（Dは基点の6機能の既定設定で実装可能）。Aは必要な共有CLI/CI hookのみ、結合時はCの新しい型付きcenter入力を含む生成→Extension ZIP→公式検証→隔離実行まで同じ実物で検証し、既存の独立テストだけで縦断成功としない。担当最終HEAD各5CI、結合5CI、dev独立7CI、Blender3版の新実マーカー必須。実装が未達なら具体的な未達/権限/実機ブロッカーを記録する。R19の範囲で成立した自動化と、残るv0.20の任意機能/任意UIの将来拡張を区別し、正式タスク数を根拠なく増やさない。次期計画の有効化は既存ゲートに従う。R20の自動発行なし、main/正式リリース/権利/私有入力/直接GitHubインストール保留は不変。
