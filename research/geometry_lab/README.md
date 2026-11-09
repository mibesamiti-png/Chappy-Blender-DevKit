# CBDK Geometry Research Lab 0.1.0

曲面接合・自己交差の検出/回避を人工データで比較する独立研究環境。CBDK本体へ自動登録しない。レビュー用、製品採用未承認。

## 起点と所有範囲

- ユーザー依頼に基づく独立研究。Task `RESEARCH-GEOM-001`。
- 起点: `feature/v0.18-shape-diagnostics` @ `8665a3c136ae81efbd28a820e7de50ef6ee59332`。
- 枝: `research/geometry-lab-20261110`、Draft PR baseは同開発ブランチ。
- 変更は `research/geometry_lab/**` のみ。共有STATE/HANDOFF/PROGRESS、既存CI、catalog、cbdk、parts、他チームの枝を編集しない。ユーザー指定を優先し、このREADME/結果を研究の引き継ぎに使う。
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

出力は新規ファイルのみ。既存結果がある場合は別名を使う。rotated probeは `runs/rotated.json` 固定なので再試験は既存結果を保管してから行う。共有CIは変更していないため、これらの研究テストは既存CIで自動実行されない。研究専用CI配線は統合担当への次の変更依頼。

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
