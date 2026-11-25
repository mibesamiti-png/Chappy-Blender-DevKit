# CBDK R20 — v0.19 / F019-01 大規模表面比較の限定実用化（Bのみ）

2026-11-25 JST。ユーザー継続指示と既承認v0.19の有効化に基づく新規正式割当候補。R20はラウンド番号でありv0.20ではない。**本書のdev統合・そのHEAD独立7CI成功・Issue #125 revision更新まで専門実装禁止。** C/D待機。GL/DIL独立。研究採用や実ユーザーデータ実行は未承認。

## 基点と重複回避
#149統合dev `1b32541dd425e1d1555f9612d766fbbdad3b6b25` 独立7CI成功: Python45562210245、Windows45562210336、Blender45562210294、Chromium45562210242、Handoff45562210236、Kit45562210386、Skill45562210251。Blender3版 jobs139028371497/139028371868/139028371767 各69 lifecycle、R19同一ZIP縦断・SHA検証成功。future JSON active=true、v0.19のみin_progress。#125 revision7 paused。正式v0.17.0/main/last_verified/44要件/24 NEXTの状態不変。

CBDK既存: glb_surface_distance の512面/scene・24点/面・median AABB BVH、glb_multires_surface の粗8/精48と特徴優先、glb_surface_pipeline の親プロセス検証・180秒既定timeout、glb_part_match の位置/重心/外寸/境界候補、GLB-020の3D viewer。既存部品対応には別の512面/64部品/256境界辺制限あり。現ラウンドでこれらを一括解除しない。GL #114 HEAD 3944d205ddcee54dbcae6fb26d594399179eef33 の exact-static/exact-cached-topology は共有境界以外の交差/接触判定（最大2048面、review_only、approved=false）であり、表面距離の代替ではない。CGAL照合研究は後のF019-03候補。生成/UV/編集トポロジー研究を本体へ無断コピーしない。

## B / F019-01 — 一つの既存GLB比較経路で上限を実測拡張
専用枝 `work/v019-glb-r20`。既存の `glb-surface-review` 経路の上に限定の明示選択プロファイルを設計する。既定512面の出力/安全境界・旧schema reader・既存テストを維持。目標は両入力各2048三角面（512の4倍）までの自作合成GLBを実際に比較すること。測定上この値が成立しなければ上限を捏造せず、達成値と原因を記録。無制限解除、暗黙の間引き、全部分一致の主張は禁止。

- 既存BVH・多解像度アルゴリズムを再利用し、固定/適応の両方向で同一targetのBVH再利用が可能か測定。必要な場合だけ実装。入力上限に加え、サンプル数、BVHノード訪問/精密距離評価、累積仕事量を有限なコード所有予算で制限し、構築/収集/親process timeoutも含め安全境界を明示。予算値は同一人工fixtureの実測根拠で決め、過大な予算をユーザー任意入力で認めない。予算超過・時間切れ・不正報告は計測不能/部分計測として明示し、未測定を0や合格に変換しない。旧schemaと拡張schemaを混同せず、親は報告の上限/カウンタ/状態/有限性/安全フラグを再検証。私有座標・パスのJSON出力なし。24MiB/10万参照の既存入力preflightは維持。
- 同一条件で512面以下の旧結果・新経路を比較。2048面以下の新経路で平面の別三角分割、既知Z移動、局所開口を人工GLBで実測。既存方式での測定値をそのまま真値とせず、独立な解析的期待値/小規模総当たりを照合。密なBVH重複、上限+1、強制小予算、偽カウンタ/非有限/旧schemaの拒否・互換を確認。固定サンプルと適応サンプルの精度差は別表示。予算超過を全体の一致/完了としない。
- 512/1024/2048の代表ケースで実時間中央値（warmup後3回、同条件）、距離評価数/ノード訪問、必要ならPython allocation peakを別測定。未計測のnative memoryや速度改善を主張しない。速度閾値を保証のない値で固定せず、性能/精度が悪化した場合は既存方式を保持。対象3 Blender版で実GLB生成→再読込→既存の親検証を通した新経路の成功/超過結果を確認。既存CI entrypointを再利用し、専用native markerと測定値をAへ。小規模旧経路の回帰・元GLB SHA不変・review_only/auto_apply=falseを保持。
- Bの所有: cbdk/glb_surface_distance.py, glb_multires_surface.py, glb_surface_pipeline.py, 必要な既存surface helper, scripts/blender_glb_surface_review.py, scripts/blender_surface_distance_smoke.py, scripts/blender_surface_inventory_smoke.py, Bの関連tests/docs。共有CLI cbdk/__main__.py、共有CI、他チーム、STATE/HANDOFF、viewer、matcher/境界上限の変更はA経由。Bは必要なCLI hookを最小差分としてAへ提案。既存native smokeで不足する場合もAへ。正式公開/任意入力の実行/新依存/GL研究採用なし。
- **終了条件**: 既存経路と新プロファイルの小規模互換、実際の512超GLB（目標2048/scene）で有効な結果、上限/仕事量超過の拒否、測定根拠、独立期待値、3版実行ログ、専門1PR exact HEAD 5CI成功。達成不能なら再現証拠で停止・A判断。細分化PRや追加研究を自動発行しない。Aは必要なCLI/CI接続と統合5CI/独立7CIを担当。

## C/D/GL/DIL・次の判断
C/Dは新規PR/CIなし。Bが完了した後にAがF019-02（既存部品対応の実用化）とF019-03（GL交差技術候補・難例）を残差から一括判断。必要時のみDの独立監査、Cの既存viewer接続を正式割当する。R21自動発行なし。GLの研究は独立継続、必要になった候補だけ採用前に比較/権利/対象条件を確認。DIL新研究不要。main/正式配布/私有入力/直接GitHub installの別承認を維持。
