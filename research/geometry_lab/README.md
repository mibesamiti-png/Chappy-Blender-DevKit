# CBDK Geometry Research Lab — R5

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
