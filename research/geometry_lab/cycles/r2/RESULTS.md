# R2 実測結果

Python3.12.14 / NumPy2.3.5 / CGAL binding6.0.1.post202410241521 / Linux。Blender生成は4.3.2。入力は人工fixtureだけ。旧記録は上書きせず、同じパラメータで再生成して比較した。

## 解析的正解と独立oracle

| 方式 | 解析90ケースのFP | FN | 正解数 |
|---|---:|---:|---:|
| legacy | 12 | 24 | 54/90 |
| exact | 0 | 0 | 90/90 |
| unfiltered | 0 | 0 | 90/90 |

CGALと直接照合できる解析66ケース＋seed固定ランダム128ペアで、新方式の不一致は0。残りの共有頂点/重複faceケースは解析的正解で照合し、CGALで確認したと数えない。別unittestで64組の非格子ランダム座標と120面の閉球もCGAL比較。

単純な6条件だけでは見えなかった、微小な正の隙間の偽陽性12件、共有境界のsliverの見逃し24件を再現。向き・scale違いを含むため独立した90種類の形状という意味ではない。

| 方式 | ペア処理中央値のケース間中央値 ms |
|---|---:|
| legacy | 0.2350 |
| exact | 0.6511 |
| unfiltered | 0.6212 |

計測は各ケース1warmup+3回。別測定のPython traced peak=30775 bytes（native/Blender/CGAL heapを含まない）。ペアbenchmark全体0.95秒。速度の集計値は入力の混合に依存し、形状全体の高速化を意味しない。

## Blender旧失敗候補の全ペア再評価

| fixture | 面数 | 旧hit | 新hit | CGAL hit | 旧FP / FN | 旧秒 | 新秒 | CGAL秒 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| voxel_overlap | 1268 | 8 | 0 | 0 | 8 / 0 | 2.864 | 9.546 | 0.0075 |
| exact_thin_neck | 1076 | 5 | 3 | 3 | 3 / 1 | 2.618 | 8.370 | 0.0053 |
| exact_rotated | 1078 | 3 | 4 | 4 | 0 / 1 | 2.782 | 8.574 | 0.0060 |

3回・warmupなしの中央値、同一snapshotに対する全ペア集合の比較。新方式は3fixtureすべてCGALと一致。旧方式は合計FP11組/FN2組。CGAL時間にはPolyhedron作成も含む。新方式は約3.1〜3.3倍遅いので、小規模参照検出器として追加し既存既定APIを置き換えない。

voxel_overlapの旧8hitは独立判定では偽陽性だった。一方、薄い首と非対称Booleanには実際に共有simplex外の接触が残り、旧方式は一部を見逃した。接触に幾何学的な重なりの面積があるか、表面を横断するかまでは今回分類していない。

R1の14候補全部を再実行したわけではないため、R1全体の成功率を新しい数字に置き換えない。Voxelの隙間消失、退化出力、曲率連続性の不足は依然別問題。

## 実行確認と限界

- 研究unittest: **21件成功**、CGAL optional検査もこの環境ではskipなし。CGALがない通常Pythonでは2件skipであることを明示する。
- 初回oracle adapter失敗はRESEARCH.mdに記録。修正後pair benchmark / Blender再評価ともexit0。
- 新しい専用workflowは研究PRの対象pathsだけ、Python3.12の1job、10分、独立concurrency、contents:read。既存workflowは無変更。新HEADのCI成功は実際のrun確認後にPRで記録する。
- 4.4.3/4.5.15/5.2.1、Windows、GUI、実データ、完全CCD、形式証明、native heapは未検証。
- 厳密さは渡されたbinary64座標の算術についてで、入力前に失われた精度・意図したCAD曲面は復元しない。
- 一般非多様体のCGAL oracle入力は未対応。手書きexact側も有限fixtureでの一致であり万能な証明ではない。
