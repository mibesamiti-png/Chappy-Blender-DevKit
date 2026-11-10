# CBDK通常開発 R15 — ABCD正式割当（ゲート通過後に有効）

2026-11-11 JST。**本書を含むA節目同期PRがv0.18開発ブランチに統合され、その新HEADの独立7系統CIが成功するまで、R15実装ブランチ/PR作成は禁止。** それまでは読み取り専用設計のみ。次期v0.19への移行ではない。

## R14受入の証拠

- B [#107](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/107) `a58e070c`、C [#108](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/108) `f6300b28`、D [#106](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/106) `f8aea0d3`：それぞれ最終HEADの5系統CI成功。担当パス重複0。
- A [#117](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/117) の結合HEAD `fba160753bbbb4d20d55b27dcbf61f6190331710` は6CI成功。専門11パスと正式長期ビジョン5パスを結合。Cのnative R14 7項目とR13 5項目をBlender3版ログで確認。
- dev squash `db25585342e19e629fc32e2cc94ceae5d2e3d7b4` の**独立7系統**：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905403010)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402793)、[Blender3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402730)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402841)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402989)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402745)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42905402775)は全てsuccess。旧PRは二重マージしない。
- 正式v0.17.0/44要件/24 NEXT/last_verified/次期計画active=falseは維持。長期ビジョンは文書・DEC-075のみ、Geometry Lab #114/DIL #115研究コードを採用していない。

## R15の担当と条件

|担当|専用ブランチ（ゲート後）|目的・編集可能パス|受入条件と禁止事項|
|---|---|---|---|
|**B** GLB NEXT-008/GLB-021|`work/v018-glb-analysis-r15`|R14匿名triageの異なるreportが**同じ実験/測定基点か**の保守的照合。 `cbdk/glb_*`とB専用tests/docs|合成一致・別試行混入・古いrevision・根拠欠落を分離。疑義はunknown/レビュー専用。私有path・元座標を出さずhash一致を真正性や編集許可にしない。既存R2/R3/R8/R13不変|
|**C** UI-001/BUILD-001|`work/v018-ui-builder-r15`|信頼済み自作5機能/6レシピで**UI表示の操作可否と実Blender operator結果**が一致するか、旧module復旧を維持して精査。`templates/modular_preview/`、C専用tests/docs|OBJECT/EDIT_MESH、selection、mode切替、foreign Scene、disable/reenableの3版実機検証。実際の不一致がある時だけ最小修正。問題なしならtests/docsで終了し、汎用UIや任意コードを拡大しない|
|**D** EXT-001|`work/v018-extension-quality-r15`|R14のhandle試験の続きとして同一inode・同サイズ・時刻偽装を伴う合成書換えの**検出限界**を評価。`cbdk/extension_*`、D専用tests/docs|独立に信頼できる事前digestの有無を分け、断定不能はunknown。POSIX根拠をWindows junction/reparse保証と呼ばない。ZIP上限16MiB/2MiB/64件と7正常プレビュー維持。権利/公開を承認しない|

**A並行タスク:** [開発速度改善#109](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/109) のwarm-cache・基点差・整合性と実ジョブログを比較。時間短縮が安全に実証されるまで本体へ統合しない。B/C/D通常開発を止めず、独立研究は継続。

## ゲートと安全

1. このR15節目PRがCI greenでdev統合され、**その新HEADで別に発火した7系統CIが全成功**した後に初めてR15着手可。Aが開始HEADを再取得する。
2. B/C/Dは最新devから担当ブランチとDraft PRを各1件作る。A専有STATE/Handoff/PROGRESS/共通CI/Notion、他担当領域、main、旧R14 PRのHEADは変更しない。
3. 専門HEADの5系統CI→Aの新結合HEAD 5系統CI→dev一回統合→統合SHA独立7系統CIを区別。速度/品質/失敗の実測根拠がない変更は無理に採用しない。
4. 私有GLBや元addonの無断実行/公開、権利不明の採用、Windows GUI未検証を成功扱いすること、正式Extensions配布、v0.19 active化、保留中の直接GitHubインストール、mainマージは禁止。
