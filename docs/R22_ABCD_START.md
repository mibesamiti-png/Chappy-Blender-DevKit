# CBDK R22 — v0.19 / F019-03 詳細形状診断の検出限界（Bのみ）

2026-11-25 JST。ユーザーの継続指示による正式割当候補。**本書のdev統合・統合HEAD独立7CI成功・#125 revision更新まで専門実装禁止。** C/D待機、GL/DIL独立。R23自動発行なし。

## 基点と重複回避
#157 R21節目同期dev `3d916d7585297c731e9f515eab82b07e871cbd41` 独立7CI成功（Python45627337180、Windows45627337341、Blender45627337202、Chromium45627337195、Handoff45627337163、Kit45627337178、Skill45627337387）。実Blender jobs139250928120/139250927393/139250928086でR21 native/CLI marker、2048面/64部品、旧誤suggestion降格、65部品skip/exit2、SHA不変を確認。#125 rev11 paused。F019-01/02限定受入、F019-03未着手。44要件/24 NEXT状態、正式v0.17.0/main/last_verified不変。
既存 glb_boundary_audit.py は近似weldの辺次数と局所境界、glb_feature_priority.py は内側境界/鋭角/小面等のヒント、glb_sampling_audit.py は追加Halton probeの感度、R20/21 は有限BVH距離と匿名候補を提供する。これらをまず比較基準とし、再実装しない。
GL #114 の研究HEAD 6ddda0c84d3fce1ed4a538c148e8e773cb7fd94f では研究R2/R3 exact rational static intersectionが独立oracle照合済みだが approved=false、対象Blender版・native memory・CCD未検証、疎な入力では高速化不利。研究成果は読取評価の参考のみ。製品コードへの移植/import・新依存・研究PRマージは今回許可しない。接合生成、UV最適化も今回対象外。

## B / F019-03 — 検出限界を先に測る、必要最小限の診断補強
専用枝 `work/v019-glb-r22`、専門PR1件。まず既存実装の失敗/未測定を再現する。固定の合成fixtureと独立の解析期待を設計し、穴、薄壁、接合、内部空洞について、既存の表面観測と境界ヒントが何を検出し何を見逃すかを定量化する。検出の主張は入力GLBに実際に含まれる面に限り、閉じた内部に面が存在しないケースは情報欠落として区別する。
- 4系統各2以上の非ゼロ差の寸法・無変更または再三角分割対照。穴は既知幅の貫通開口と単なる境界/外縁、薄壁は既知面間隔と単面/退化、接合は既知隙間/接触/交差と同じ部品の重複候補、内部は同一外殻+明示内面の有無と面のない内部の判定不能を区別。寸法、scale、期待、sampling budgetを事前固定し、実測後に閾値を合わせない。局所診断を別々に扱い、表面差・境界辺・接触候補を物理的な穴/厚み/連結/空洞の証明としない。
- 既存 R20/R21 の明示profile、2048三角面/64部品、既定512、旧schema/CLI/viewerを保持。未測定/予算停止/退化/曖昧を clean としない。候補領域の選定は既存 feature hints と R21 局所証拠を優先。効果が独立に再現した場合のみ小さな読取専用補強をB所有モジュールへ追加。根拠がなければ tests/docs の測定結果だけで止める。新しい製品profile/schema/CLIの必要性はAへ提案し、今回無断接続しない。
- 各観測の有限上限・共通総予算・タイムアウト・出力上限をコード所有の値で制約。R21の既存予算に無制限の追加走査を重ねない。精密全組合せ禁止。候補数/サンプル/面評価/経過時間を報告し、ネイティブメモリ未測定は明記する。静的GL exactの比較は公開済み研究結果と解析fixtureの読取照合までとし、実装採用は別判断。真の連続衝突・最小肉厚・閉じた実体の内外判定は保証しない。
- 人工GLB export/importの3版nativeを既存 `scripts/blender_surface_inventory_smoke.py` に統合。4系統の代表対照、既存profile互換、上限/予算停止、元SHA不変、誤警告/見逃し/未測定を別集計。明示面のある空洞と観測不能の対照を含める。測定できない例は理由を残す。独立した期待値と観測値を分ける。既存5CIと実native marker、代表ケースwarmup+3中央値。合格件数は研究限定で、実ユーザーGLBの一般精度・実運用完成は主張しない。
- B所有: cbdk/glb_boundary_audit.py、glb_feature_priority.py、glb_sampling_audit.py、glb_surface_distance.py、glb_multires_surface.py、glb_part_match.py、glb_surface_pipeline.py、scripts/blender_glb_surface_review.py、scripts/blender_surface_inventory_smoke.py および関連B tests/docs。必要な最小差分のみ。A所有CLI/共有CI/STATE/HANDOFF・旧viewerは変更しない。私有データ、研究コード採用、自動修正、別研究、新依存なし。失敗・未確定を報告して終了し、未達成を成功に見せない。

## A/C/D
Aは測定の妥当性と採否、必要な共有CLI/CI接続の判断、統合5CI/独立7CI、台帳を担当。C/Dは新規PR/CI不要。F019-03の限定受入範囲と残る課題は実測後に判断し、v0.19全体完了やv0.20移行を自動宣言しない。GL/DIL独立、正式公開/権利/実データは別承認。
