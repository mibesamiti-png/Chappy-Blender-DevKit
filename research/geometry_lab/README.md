# CBDK Geometry Research Lab — R11

曲面接合・自己交差の検出/回避を人工データで比較する独立研究環境。CBDK本体へ自動登録しない。レビュー用、製品採用未承認。

## 起点と所有範囲

- ユーザー依頼に基づく独立研究。Task `RESEARCH-GEOM-001`。
- 起点: `feature/v0.18-shape-diagnostics` @ `8665a3c136ae81efbd28a820e7de50ef6ee59332`。
- 枝: `research/geometry-lab-20261110`、Draft PR baseは同開発ブランチ。
- R1の変更は `research/geometry_lab/**` のみ。R2ではユーザーの研究専用CI指示に基づき、独立した `.github/workflows/geometry-lab.yml` のみ追加。既存共有workflowは無変更。共有STATE/HANDOFF/PROGRESS、既存CI、catalog、cbdk、parts、他チームの枝を編集しない。ユーザー指定を優先し、このREADME/結果を研究の引き継ぎに使う。
- main確認時 `c5b63ba`、正式版0.17.0。mainにはv0.18シルエット回帰まで。devはR13統合済み/R14割当済み。7部品・5機能・6レシピ、GLBの形状/表面/仮説レビューが既存。本体に汎用接合/CCDは見つからなかった。
- 確認した進行中PR: B #107、C #108、D #106、A速度改善 #109、私有mesh準備 #112、知識収集 #113。内容を取り込まず独立。
- 並行ルール: docs/PARALLEL_DEVELOPMENT.md、PARALLEL_ROLLING_QUEUE.mdのR14末尾、AGENTS.md、PROJECT_SPEC、STATE/HANDOFF、catalog/partsを確認。mainマージや正式公開は今回の作業に含めない。

## 再現

Python 3.11+、NumPyが必要。ホストで動作確認した版はresults参照。仮想環境に `pip install -r requirements.txt`（Python 3.11+）で研究依存を隔離。Blender内は同梱NumPyを使用する。

```bash
cd research/geometry_lab
python -m unittest discover -s tests -v
python benchmark.py --output runs/new-python.json
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python blender_benchmark.py -- --output runs/new-blender.json
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python probe_rotated.py
```

出力は新規ファイルのみ。既存結果がある場合は別名を使う。rotated probeは `runs/rotated.json` 固定なので再試験は既存結果を保管してから行う。既存共有CIは無変更。R2追加の専用CIはPython3.12・CGAL oracle・研究unittestとpair benchmarkを実行する。Blender benchmarkは専用CIには未配線。

## API

- `Mesh(vertices, faces)`: detached三角形mesh。NaN/Inf、退化、index不正、2万面/6万頂点超過を拒否。
- `detect(mesh, method='sweep'|'brute')`: status、pairs、tested、adjacent_tests、certified=false。予算超過のpairsはNone（交差なしとは異なる）。
- `guarded_step(mesh, displacement)`: 最大512面の独立triangle soupのみ。accepted/blocked/initial_collision、採用alpha、新meshを返す。元を変更しない。一般の接続meshは明示拒否。
- `quality(mesh)`: 辺次数、連結成分、volume、最小三角形品質。閉じた一貫方向meshでのみvolumeを物理量として利用する。辺次数だけではvertex manifoldや向きを保証しない。
- `cbdk_geometry.blender_backend.join(a,b, method, voxel_size)`: Blender依存を遅延import。Exact union / voxelを一時データで評価しコピーを返す。mesh/material/UVの保全機能ではない。

`RESEARCH.md`に出典と比較、`RESULTS.md`に実測、`results/*.json`に人工データの集計と実行ソースhashを保存する。私有モデルを読むCLIは設けていない。

## 明示的限界

SATは浮動小数点近似。隣接面は1e-7 insetで共有境界を除外するため微小重複の見逃しがあり得る。hitも接触/丸め由来候補で、実交差確定ではない。FP/FN=0という記録は限定した解析fixtureについてのみ。sweepとbruteは同じnarrow phaseであり独立oracleではない。

swept-AABBは保守的で、初期から箱が重なる非交差meshを拒否し得る。線形軌跡の異なる面の衝突をガードする実験で、連結meshや三角形内部の反転防止、IPC/完全CCDの保証ではない。

ローカルBlender 4.3.2は既存CI対象4.4.3/4.5.15/5.2.1の代替証拠ではない。GUI・Undo・実ユーザーモデル・ライセンス許諾・製品統合は未検証。

## 現在の進捗 — R2

[研究選定・根拠](cycles/r2/RESEARCH.md) / [比較結果](cycles/r2/RESULTS.md) / [状態](cycles/r2/STATUS.json) / [APIメタデータ](algorithms.json) / [次サイクル手順](cycles/README.md)。旧R1の結果は履歴として保持し、R2で偽判定を確認した部分は新結果を優先する。

新API `from cbdk_geometry.exact import classify_pair, detect_exact` はbinary64値の有理数clippingで共有simplex外を判定する。最大2048面、全ペア走査数と時間の予算がある。上限時はpairs=null。旧SAT既定API・motion guard・接合APIは変更していない。

```bash
# 研究ディレクトリ内、任意の専用venvへ
python -m pip install -r requirements-oracle.txt
python -m unittest discover -s tests -v
# Linux/macOSのtimeout相当で各プロセス300秒まで
python -m cycles.r2.benchmark --output runs/new-r2.json
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python cycles/r2/export_blender.py
python -m cycles.r2.recheck_blender
```

Blender exporterはruns/r2_meshes.json、再評価はruns/r2_blender.jsonを新規作成する。再実行時は既存のruns出力を別の場所へ保管してから実行する。人工mesh snapshotはruns内にだけ置き、コミットする結果は数値・ペアID・hashのみ。CGALはGPL系の検証専用依存で、ライブラリruntime requirementsには入れない。Blender PythonへCGAL wheelを直接importしない。

## R3: 高速化とR1全候補の再評価

[選定・停止条件](cycles/r3/RESEARCH.md)、[結果](cycles/r3/RESULTS.md)、[状態](cycles/r3/STATUS.json)。新APIは `cbdk_geometry.accelerated.detect_accelerated(mesh, shortcuts=True)`。`shortcuts=False`でcacheだけの比較ができる。R2/R1 APIは変更しない。独立研究CIはR2とR3を両方実行する。

```bash
python -m cycles.r3.benchmark --output runs/new-r3.json
# R2人工snapshotがある場合だけ --include-blender を追加（保存hash一致必須）
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python cycles/r3/export_joins.py
python -m cycles.r3.reevaluate
```

再評価のsnapshot/結果はruns/r3_join_meshes.json、runs/r3_reevaluation.jsonへ新規作成。再実行前は旧runsを別名で保管する。公開結果は集計だけ。CGALの判定でR1を再評価するので、新検出器が自分の出力を合格にする構造ではない。


## R4: 検出から形状生成の評価へ

[研究選定・出典](cycles/r4/RESEARCH.md) / [実測・失敗・再現](cycles/r4/RESULTS.md)。
境界ループ接続API `cbdk_geometry.bridge.bridge_loops(a,b,method="dp",seconds=10)` を追加。
順序付きNx3/Mx3配列（各3..48頂点）から入力を変更せずdetached三角形帯を返す。
戻り値はmesh/objective/shift/reverse/trials/approved=false。`method`はindex/phase/dp。
無効入力・非退化候補なしはValueError、予算はTimeoutError。自動採用/scene編集なし。

未使用6ケースの合格はindex0、phase2、DP3、Blender標準4。
DPは標準より遅く、置換不採用。4.3.2/4.4.3で全40出力一致、他版・実作品は未検証。
R1〜R3の検出改善を制作能力改善とは混同しない。次候補は形状保存制約付き接続。


## R5: 元境界の保存を優先したRadial Loft

[実験設計](cycles/r5/RESEARCH.md) / [初回実測と失敗](cycles/r5/RESULTS.md) / [状態](cycles/r5/STATUS.json)。
`cbdk_geometry.radial_loft.radial_loft(a,b,cuts=3)`はXY平面上のstar-shaped輪郭専用。入力境界の頂点・辺を変えず、3本の中間輪郭を補間する。独立した三角形meshを返す（approved=false）。Blender sceneは触らない。

R4の既知6ケースで5/6、R5の新規人工holdout5ケースで4/5。後者のphaseは3/5。CGAL交差0。横ずれ楕円では最小三角品質0.0634で不合格、R4 lowpolyでは形状誤差で不合格。Blender GUI版Bridgeの中間cut/補間とは未比較であり、CBDK本体へは未採用。

```bash
python -m pip install -r requirements-oracle.txt
python -m unittest discover -s tests -v
python -m cycles.r5.run --output runs/my-r5-result.json
```

専用CIでR1〜R4の既存回帰とR5を別々に実行し、R5出力JSONのhash・測定値をartifactに保存。実作品・私有モデルは読まない。


## R6 — Blender標準のcuts/interpolationとR5の公平比較

[研究事前設計](cycles/r6/RESEARCH.md) / [R6の全結果・失敗](cycles/r6/RESULTS.md) / [状態](cycles/r6/STATUS.json)。

公式Blender 4.4.3で`bpy.ops.mesh.bridge_edge_loops` の0-cuts PATH、3-cuts LINEAR/PATH/SURFACEと、凍結R5 radial loftを同一人工meshで比較。20形状×5方式=100出力、3反復とCGAL検証。新5ケースは**R5 5/5、native best 3/5**（LINEAR）、旧15ケースはR5 13/15、native best 11/15。速度値はAPI経路が異なるため直接比較しない。低ポリゴンのR5不合格・標準成功もある。非平面・実作品・第三者データ未検証。

研究専用CIがBlender正規アーカイブをSHA256照合して実際のnative operatorを実行。R6完了、研究ゲート達成。ただしA司令塔承認までCBDKへ実装せず、`approved=false`。


## R7: 非平面境界への限定拡張

[事前合格条件](cycles/r7/RESEARCH.md) / [R7比較実測・失敗](cycles/r7/RESULTS.md) / [最新状態](cycles/r7/STATUS.json)。

`cbdk_geometry.warped_loft.warped_radial_loft` を研究用に追加。XY投影がstar-shapedで、上下Z包絡が分離した軽度非平面ループだけをサポート。元境界頂点/辺を保持するが、一般的な3D接合やUV・法線保存を保証しない。

公式Blender4.4.3で10人工形状×3方式=30生成＋CGAL独立評価、新規6ケースで研究R7 5/6、標準3-cuts Linear 4/6、標準no-cuts 4/6。細長い横ずれケースでは全方式不合格、R7 min quality=0.06183で標準より悪い。研究ゲート達成、製品未承認（`approved=false`）。AレビューまでCBDK本体へ反映しない。R8は自動開始しない。


## R8: 中間リング密度を段階変化し、細長い三角形を減らす実験

[事前登録条件](cycles/r8/RESEARCH.md) / [R8実測・不合格・限界](cycles/r8/RESULTS.md) / [最新状態](cycles/r8/STATUS.json)。

従来R7が内部中間輪郭で均一な頂点数`max(n,m,12)`を使っていたのに対して、R8 `cbdk_geometry.tapered_loft.tapered_radial_loft` は中間の頂点数を上下に合わせて変化。入力境界の頂点・エッジは変えず、非平面ながらXY star-shapedでZが分離した輪郭のみに対応。CGALで正式に評価した人工R7既知10ケースでR8 10/10（旧R7 9/10）、新6ケースでR8 **5/6**、R7 **3/6**、Blender標準3-cuts **3/6**。新6ケースのすべてで最小三角形品質が改善。唯一の失敗`r8_slender_opposite`は最小品質0.0786で不合格。

平均面数はR8 189 < R7 248 < Blender3-cut 331（新6ケース）、一方でR8の処理時間・解析形状RMSは旧R7より悪化。実モデル/UV/任意方向境界・人手作業は未検証。製品採用承認ではなく`approved=false`、PR Draft維持。R9は自動開始しない。


## R9: 元境界・面数を変えず局所の三角形品質を改善

[実験事前条件](cycles/r9/RESEARCH.md) / [R9全結果・失敗・速度](cycles/r9/RESULTS.md) / [最新状態](cycles/r9/STATUS.json)。

R8の `tapered_radial_loft` を凍結したまま、研究専用 `cbdk_geometry.flip_loft.conservative_flip_loft` を追加。上下の境界頂点・全頂点座標・面数を変えず、内部対角線を条件付きで最大3パス反転する。CGAL独立検証を必須とする（局所の法線検査だけでは交差ゼロを保証しない）。

旧R7/R8既知16件でR9 **16/16**（R8 15/16）。未使用人工holdout6件でR9 **5/6**、R8 **4/6**、Blender標準3-cuts **2/6**。既知逆スレンダー品質0.0786→0.1272で全条件合格。ただし未知reverse_narrow品質0.08078はまだ不合格。R9 median約90.9msはR8約7.26msと高コスト。製品採用を意味せず `approved=false`。Aレビュー待ち・R10自動開始なし。


## R10: 品質が足りないときだけR9の内部エッジ補正を実行

[事前計画](cycles/r10/RESEARCH.md) / [全120出力と速度実測](cycles/r10/RESULTS.md) / [状態](cycles/r10/STATUS.json)。

R8を一度生成して最小三角形品質が0.1以上なら即採用、未満ならR9の凍結内部エッジ反転コアを最大3パス実行する研究用ルーター。**別CGAL検証が必須**。新規人工8ケースでR10 **8/8**、R9常時補正8/8、R8補正なし6/8、Blender標準4/8。6件は補正を省略し、2件を救済。R10新8ケースの平均処理34.6ms、R9の68.9msの**約50.2%**。ただしR8単独6.86msより高コストで、R9の追加品質改善をスキップする場合もある。既知22件でR9と同一合否21/22、未解決 `r9_reverse_narrow` は残る。

研究ゲートと速度ゲートを達成したが、実モデル/UV/法線/Blender一般形状は未検証。本体統合はA司令塔審査が必要。PR #114はDraft/未マージ、`approved=false`。R11は自動開始しない。


## R11: Blender Edit Modeによる元面・UV・材質・法線の実装監査

[事前検証条件](cycles/r11/RESEARCH.md) / [Blender+CGAL全結果](cycles/r11/RESULTS.md) / [研究状態](cycles/r11/STATUS.json)。

公式Blender4.4.3の**編集モードBMesh**上で、元面UV/材質を持つ二つの研究用カラー（人工生成）へR10帯を接続する試作。元面の頂点・UV・材質は**14/14条件で完全保持**。新規人工6形状も6/6属性監査に合格。割当なしの対照は14/14で不正検出。接続後全体を別環境CGALで評価し28出力で交差0。Blender sceneも元に復帰。

**ただしUV島の不連続は残り、意図的な分割UVは新面と最大差0.25。** 新規形状の面法線の接合最大角差約56.35°、既知形状で66.93°。実モデルのUV/法線が自然につながることを保証しない。テスト用カラーはR10の生成境界から作った有利な条件で、実ファイルではない。本体未統合・`approved=false`・A最終判断まで保留。R12は自動開始しない。
