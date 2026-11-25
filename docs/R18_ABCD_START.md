# CBDK R18 — v0.18完成直結の生成経路（C/D限定）

2026-11-25 JST。R17受入完了後、ユーザーの継続指示を受けAが既存残条件の2件を選定。新しい研究ラウンドではない。**本書のdev統合・統合HEAD独立7CI成功・Issue #125 revision更新をAが確認するまで実装禁止。** Bは待機。GL/DILは独立。

## 基点証拠

#137節目同期 dev 922ad354a437d577ad42b57278b6c7fea57dca69 独立7CI成功。#138キャッシュ改善 dev 91d8cdcbf3950203b945afdbc84ede3beffd7c7a 独立7CI成功（Python45536736016、Windows45536736021、Blender45536736023、Chromium45536736070、Handoff45536736000、Kit45536736099、Skill45536736067）。Blender3版すべてCACHE_HIT/SHA256_PASS/native成功、公式取得0、再実行0。公式ミラー未使用、容量・速度は未測定。PR #25 draft、正式v0.17.0、次期active=false。

## C / UI-001・BUILD-001 — 6番目の自作機能を通して固定5機能から脱する

専用枝 `work/v018-ui-builder-r18`。現行の安全なレシピ、feature_catalog、registration_audit、ui_layout、modular_builder、templates/modular_previewを確認。機能固有の固定分岐が追加を困難にしている箇所を、**コード所有の明示的なfeature descriptor/登録契約**へ整理する。JSONは既知IDのみ選択し、コードやimport先、任意RNA型/operatorを与えられない。既存5機能/6レシピの動作と安全境界を維持。

- 新規の小さなCBDK自作読取専用機能を1件（例：既存bounds helperを使ったメッシュ中心座標表示。実装前に既存機能との重複を確認し、同等に小さく有用な機能へ調整可）。新規形状生成や汎用任意コード実行は今回不要。
- 既存featureだけのレシピと新機能を含むレシピを、同一の計画→生成→登録→Panel.draw→operator→解除経路で確認。新機能の表示値を非対称な自作メッシュで独立計算と照合し、選択外機能・未許可IDを拒否。旧レシピの既存機能セット/ZIP内挙動を保持。既存のglobal catalog、inline layout両方で適切に扱う。
- 追加の型付き汎用設定は、この新機能と既存契約に必要な範囲のみ。任意operator、任意Python、外部ソース、自動採用、GUI保証、複数preview同時インストールは対象外。
- C編集許可: `cbdk/ui_layout.py`, `cbdk/modular_builder.py`, `cbdk/feature_catalog.py`, `cbdk/registration_audit.py`, `templates/modular_preview/`, `catalog/addon_features.json`, `catalog/ui_layouts.json`、専用test/fixture/docs。共有CLI/CI/parts/STATEはAへ変更要求。既存native lifecycleスクリプト内に追加の実マーカーを置く。旧5機能の既存テスト期待値を理由なく6へ置換しない。既存全5CI・Blender3版で新機能マーカーを確認して停止。

## D / EXT-001 — 実際のExtensions ZIP生成・公式検証経路

専用枝 `work/v018-extension-quality-r18`。既存manifest field review、TOML parser、preview archive検査の制約を再利用。まず**明示メタデータから安全にTOMLを生成し、CBDK自作の合成fixtureをExtensions形式のZIPへ組み立て、Blender公式CLIで実物を検証**する経路を作る。実部品の正式配布許可とは別。

- 既知のrequired fieldsとR17で対応済みoptional max/permissionsだけを最初の出力範囲とする。メタデータは明示入力、TOMLエスケープ/再parse/既存review照合、同じ入力の決定的ZIP、固定上限/安全なmember path/重複拒否/上書き拒否。未知optionalは未対応として明示し、全項目実装を今の必須にしない。
- 公式CLIの生成物検証は3版の既存manifest smokeへ接続。既知の合成テスト専用最小アドオン（固定init、配布不可、実データなし）と明示したテストメタデータを使用。公式が受理するZIP構造・manifest・内容の実測、無効入力時ZIPなし、既存preview ZIPの承認フラグを書換えないこと。公式CLI validate/buildの仕様差を調べ実行結果を記録。実部品のライセンスは決めず、未承認実ソースを正式Extensionへ変換する入口は作らない。
- D編集許可: `cbdk/extension_*.py`、専用test/fixture/docs、`scripts/verify_extension_manifest.py` の合成fixture/CLI観測追加のみ。Cのbuilder/catalog/templateは読取専用。AのCLI接続が必要なら小さなAPI契約とテストを提示し変更要求。共有CI設定はA。既存6 strict＋R17 7 optional例、7 preview検査と上限、値/パスの漏洩防止を維持。5CI/3版の実ZIP検証まで一括し停止。

## B / GLB — 待機

R17で自動化可能な限定triageは受入済み。NEXT-007/008/009の実GLB/実プロパティ登録/因果は別途明示許可と実環境が必要。今回の新規PR・CI・追加の合成負例は不要。Aの正式割当までは従来範囲を越えない。

## A / 統合と終了

C/Dは独立した1PRずつ、対象最終HEAD各5CI、結合5CI、dev独立7CI・Blender3版。必要な共有CLI hookだけAが追加。Bの空PRを要求しない。実装中に判明した本質的な未対応は既存完成ゲートへ記録、細かな追加負例ラウンドを自動生成しない。合成Extension合格を正式配布可能とはみなさない。R18受入時に現行自動化残条件を再判定し、私有データ/GUI/権利/正式公開/実Extensionの別承認を維持。main/正式v0.17.0/last_verified/44要件/24 NEXT/次期active=false、研究#114/#115は変更しない。Notionは節目実測後に別同期。
