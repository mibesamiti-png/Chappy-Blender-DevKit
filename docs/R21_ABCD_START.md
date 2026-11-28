# CBDK R21 — v0.19 / F019-02 部品対応の限定実用化（Bのみ）

2026-11-25 JST。ユーザー継続指示に基づく正式割当候補。**本書のdev統合・統合HEAD独立7CI成功・#125 revision更新まで専門実装禁止。** C/D待機、GL/DIL独立。R22自動発行なし。

## 基点
#152 R20実装受入dev 7e8bd21994a3b12dc1282fedc3ceceb4230e6860 独立7CI。#153節目同期dev `26eeeb02ac3ee75d6f1dbbbbcb5892e00f3e32e4` 独立7CI成功: Python45568640215、Windows45568640035、Blender45568640113、Chromium45568640092、Handoff45568640031、Kit45568640146、Skill45568640071。実Blender jobs139049558804/139049559240/139049559177 各69 lifecycle・R19縦断/R20 CLI 2048測定・既定/密集停止・SHA成功。#125 rev9 paused、v0.19 active。44要件/24 NEXTの状態・正式v0.17.0/main/last_verified不変。

## B / F019-02 — 匿名部品候補と局所表面比較をつなぐ
専用枝 `work/v019-glb-r21`。R20の2048面/scene表面比較は全体計測のみで匿名上位32面数一覧、弱い面数候補まで。既存glb_part_match.pyは512面/64部品、world AABB midpoint（真の重心ではない）/外寸/面数の重み0.58/0.32/0.10、双方向最良・margin・境界形状/連結性guard、最大2候補。glb_boundary_audit.py の近似weld/256境界辺guard、glb_diff_visualize.py のv1親検証とローカルviewerは既存。**これらを作り直さず、R20の集計専用経路に明示選択の部品候補比較を接続する。** 旧512のmatcher/viewerとR20既定/拡張レポートは無断変更しない。

- 既存候補選定の再利用・必要な有限上限拡張を小さく実装。目標各2048面・各64部品以下（上限値の実証ができなければ測定値と理由を報告）。既存境界256辺guardを維持し、未知/多すぎる部品・空メッシュ・不正layout・退化・予算超過を明示する。全64×64の精密表面比較は禁止。既存位置/外寸/面数から短い候補リスト、候補毎の局所scale・双方向sample距離等で形状差を追加観測。R20のBVH/予算を再利用し、全候補を合計した有限のpair/sample/node/eval/境界比較仕事量・構築数・出力・親timeoutをコード所有上限で制約。全体表面比較と部品評価の予算を混同せず、両者の合計上限を記載。個々の候補に毎回無制限の新予算を与えない。
- **失敗例から実装判断**: 同じAABB/面数/境界情報だが異なる閉じた表面、同じ位置に複数の競合部品、近接した小部品と遠い大部品、分割変更・部品順序入替・移動・欠落/追加・分割/結合。既存判定で何が起こるかを先に再現。明確な独立期待を設け、誤suggestionを減らすことを優先。局所表面差は不確かな候補を保守的に降格する証拠とし、単独で一意identityやexact equalityを主張しない。候補の昇格・再順位付けを行うなら既存双方向競合/境界guardと矛盾しない独立根拠必須。判定不能/未計測は曖昧のまま、競合やsplit/mergeは強制1対1化しない。適用/パラメータ変更なし。固定/適応距離の観測範囲と残差、理由・未計測状態を明示。真の重心を追加する場合は面積加重で定義、AABB中心とは区別。効果が再現できない追加特徴は不採用。
- 既存 `glb-surface-review` の内部API/runnerへ、既定OFFの追加部品レビューとして接続。既存schema1/2出力は非選択時完全互換、必要なら明示選択の新schema/profileをAに提案し、親が匿名ID/順序・候補数・双方の重複/未対応・理由・有限指標/カウンタ/状態・上限・no-auto/identity flagsを検証。GLB読み込みで得た実オブジェクト別面数と対応を照合（ソート済み上位32面数一覧を部品ID順序と混同しない）。座標・名前・パスやgeometry signatureをJSON/ログに出さない。全体比較がskip/timeoutでも部品評価を測定済みとしない。部品だけskipする場合は全体結果とは別状態。旧viewer/overlay/回帰CLIは今回対象外。共有CLI hookはAが担当。
- 人工fixtureで旧512回帰、匿名IDの並べ替え、同形別分割/既知移動/差のある同AABB、曖昧・不足・追加、各2048/64境界の有効例と2049/65超過、256/257境界辺、強制小予算、偽報告の拒否を検証。既存のR2〜R20試験は再利用。新規 nativeは既存inventory smokeに統合し、3 Blender版で実GLB export/import→親検証、独立期待、元SHA不変、予算停止、代表ケースのwarmup+3中央値と仕事量、旧結果の誤suggestion/改善/残る曖昧を数える。全例に正解があると仮定しない。native memory/任意実モデルの保証はしない。
- B所有: cbdk/glb_part_match.py, glb_boundary_audit.py, glb_surface_distance.py, glb_multires_surface.py, glb_surface_pipeline.py, scripts/blender_glb_surface_review.py, scripts/blender_surface_inventory_smoke.py と関連B tests/docs。既存モジュールの最小差分に限定。共有CLI/CI/STATE/HANDOFF・viewer変更はA経由。GL研究の無断採用や新依存、別研究なし。専門PR1件・exact HEAD 5CIと実native marker。目標が成立しない場合は再現証拠で止めA判断。細分化や根拠のない閾値調整を続けない。

## A/C/D
Aは必要なCLI hook・統合5CI/独立7CIと台帳を担当。C/Dは新規PR/CI不要。F019-03の穴/薄壁/接合/内部・GL exact-static適用候補は別判断。viewerの2048拡張も必要性と実測で判断し、F019-02内で無理に行わない。私有データ、main/正式配布、未承認コード採用は別承認。R21はv0.19内の割当でありv0.21ではない。
