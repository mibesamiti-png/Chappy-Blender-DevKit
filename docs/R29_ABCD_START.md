# CBDK R29 — F022-01 固定関節の統合操作パネル（割当候補）

2026-11-27 JST。基点 9969c848f48b0c1be99a5c8c19bc032cf77a97f5。**本割当のdev統合・独立7CI成功・Issue #125 revision 26 active化までは専門実装禁止。** 既承認v0.22の最初の限定縦断。現在は候補のみ、F022-01/02/03完了としない。GL/DIL独立、正式版v0.17.0/main/last_verified/44要件/24 NEXT維持。

## 基準・今回の範囲

PR #196 dev 9969c848f48b0c1be99a5c8c19bc032cf77a97f5、独立7CI（Python45983042573、Windows45983042767、Blender45983042567、Chromium45983042677、Handoff45983042614、Kit45983042541、Skill45983042508）。4環境provider各18、Linux 4.5.15 GUI 5/5、Windows kit研究provider除外。#198は検証専用でclosed/unmerged。既承認F022-01の限定割当候補を作成。固定人工回転関節の読取ビュー・既存操作・証拠/状態境界を一つの開発UIに接続し、R28/GLB-022/CJM/GLの既存処理を再実装しない。#125 rev25 paused、割当統合・独立7CI・rev26 active前は専門実装禁止。v0.22全体完了・任意モデル・Windows GUI・正式配布は未承認/未検証。main/正式版/last_verified/44要件/24 NEXT不変。

対象は既存 parts/blender/joint_preview.py の固定人工回転関節のみ。元外径5、目標4、軸径2、隙間0.4、Z軸、原点、Object mode、unit scale=1。FREEを肯定実測に使う。他の既存補正方針は回帰を維持。CJM ZIP SHAとGL frozen manifestは既存configureで照合。候補生成は既存のbaseline、negative、midpoint、targetの固定列をそのまま利用し、測定/採否/中断/寸法採用/復元を再実装しない。新しい機構/任意レシピ/任意モデル/コード実行/外部パス自動取得/自動採用/mesh commitなし。新規パネルは明示登録の固定開発プレビューで既存パネル・registry・catalog・releaseを変更しない。

## 共通契約

固定表示ID joint_rotary_fixture_v1、表示用part IDs rotary_outer / rotary_axle（役割表示のみ、既存catalog IDとしない）、固定recipe label、現在の検証状態、候補の外径と既存判定・score、reasonを表示。Bの純Python projectionはCの描画用にread-only dictを返す。入力は既存status、reason、result_jsonと現行RUNSからA/Cのadapterが抽出した固定候補の要約、現行入力一致の明示bool。任意JSONの実行なし、有限値・既知enum・最大3候補、欠落/矛盾は unavailable、候補採用可否は現行operatorが最終判断する。RUNNING時は中断のみ許可、BLOCKEDではすべての変更操作を拒否、READYかつ現行候補に限り寸法採用ボタン表示、失敗/中断は明示再試行、復元は既存安全guardに従う。UIの有効/無効は権限付与ではない。B/C/Dは共通契約のfixtureを独立に使い、相互専門ブランチを取得して実装しない。Aが統合時に接続する。

## B — 表示用データ・候補の読取projection

branch work/v022-glb-r29、専門PR1件。新規 cbdk/joint_panel_view_r29.py、B専用tests/docs。固定ID、既存の候補判定/有限数値/状態・reason codeを読取整形。候補最大3、重複/欠落/非有限/古い入力/未知状態は採用不可表示、BLOCKEDとRUNNING優先。判定の再計算や最適化、bpy、provider load、ファイル書込なし。既存 watched GLBテストに関連回帰を追加する場合は最小。5系統CI・3版既存回帰。C/D/共有CI変更なし。

## C — Blender統合パネルの固定縦断

branch work/v022-ui-r29、専門PR1件。新規 parts/blender/joint_panel_r29.py、scripts/blender_joint_panel_r29_smoke.py、C専用tests/docs。projectionの受取境界は固定契約のテストstubで検証しAが実Bを接続。部品/レシピ・候補・状態/エラーを表示し、既存 joint_start/joint_action/joint_dimension にのみ委譲、追加実行経路や別のundo pushなし。UI状態制御・明示登録/解除・重複登録拒否・他クラス/既存パネル保全。3版でPanel.drawと実operator委譲（直接呼出と実GUI区別）、生成/候補/採用/拒否/中断/再試行/復元を既存固定実測に接続する入口を提供。新規実測はA統合時に固定providerで実行し、専門単独は既存native回帰＋実panel登録/解除・描画の固定stub検証。5CI/3版。必要な発火は既存 scripts/blender_joint_integration_smoke.py の末尾に限定hookを1箇所許可（A調整可）。B/D/共有CI変更なし。

## D — 独立安全・証拠検査

branch work/v022-quality-r29、専門PR1件。新規 cbdk/joint_panel_evidence_r29.py、D専用tests/docs。固定表示/操作/状態遷移・候補の鮮度・明示採用のみ・中断/失敗/blockedで自動採用なし・元scene保全を独立検証。B/C実装への直接依存なし。親run ID、Blender版、固定fixture ID、実測かstubか、欠落/重複/順序/未知判定/不正数値/不一致を拒否。GUI入力・native呼出・callback simulationを区別し、Windows GUI成功を推定しない。パッケージprovider除外は既存チェックを再利用。5CI/3版既存回帰。B/C/共有CI変更なし。

## A — 実測接続と限定受入

AがB projectionとC panelを接続、Dの独立検査を通す。固定providerの実測と既存72/72、Linux GUI 5/5の回帰を維持。新規panelの表示・委譲・失敗/中断/復元・登録解除を3版の実Blenderで検証する。UIテスト用のstubだけを実機縦断成功としない。実GUIの生産パネルクリックが未実測なら未検証と記録。専門5CI＋A結合5CI＋dev独立7CIと実測ログを受入条件。今回の合格はF022-01の固定fixture限定縦断のみ。Windows実GUI、任意モデル、一般的な部品/レシピ生成、F022-02/03、正式配布は別ゲート。R30自動開始なし。
