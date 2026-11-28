# R5 — 元境界を固定した放射方向ロフト

## 開始時に固定した判断（R4の後）

1. **問題**: R4では低ポリゴンと大きな横ずれにおいてBlender標準の直接Bridgeも失敗。形状を保持した曲面接続を検証する。
2. **現行限界**: R4の独自DPは交差0でもRMS/最大誤差が悪化し、標準より52〜86倍遅い。標準のBMesh直接Bridgeは中間輪郭なし。BlenderのGUI Edge Loop Bridgeには`number_cuts`と補間方法が既にあるため、R4の標準結果に勝ってもGUI標準の全機能に勝ったことにはならない。
3. **比較**: 旧R4の同一6ケースに記録されたBlender 4.4.3 BMesh直接Bridge（4/6）、phase（2/6）、DP（3/6）。新しいholdout5ケースではphaseを同時生成して比較するがBlender-native未測定。
4. **今回の候補は1方式**: 頂点順をXY平面の重心まわりの角度へ正規化。両境界のポリゴンへ放射線を交差させて同一角度の点を取り、3本の中間輪郭を線形補間。両端は元の境界頂点・境界辺を動かさずangular zipperで接続。三角形帯を別meshで返し、編集sceneなし。`approved=false`。今回の3カットは固定し、holdoutを見て調整しない。
5. **予算と合格**: R4で観察済み10ケースは開発用へ全移行。新しい5ケースを未使用holdoutに固定（同一研究者の人工データでblind実作品ではない）。各候補3反復。ループ各3〜48点、タイムアウト10秒。各ケースCGAL自己交差0、厳密な元境界エッジ保存、manifold、Euler=0、最小三角品質>=0.1、R4と同一の重心サンプルRMS<=0.08、最大<=0.2。R4旧6件の5件以上と新holdout4件以上を満たせば**追加検証に進む価値がある**（正式採用とは異なる）。速度はnativeとの同ホスト比較がないため採用の証拠にしない。
6. **終了**: 新holdout一次実測とCGAL検査を完了した時点で一区切り。達成・未達を記録して1サイクル終了し、再調整しない。CGAL障害なら環境未解決で停止。実作品、非平面、穴分岐、法線/UV/材質、GUI standard`number_cuts`比較が残れば正式採用を保留。

## 実装上の限定

- XYに平行な2つの平面上の単純なstar-shaped輪郭、上面のZが下面より大きい入力のみ。
- 頂点/辺の接続順が放射方向に単調で、中心からの各rayが境界を一度だけ横切る場合に限定。非平面・凹で非star-shaped・ねじれた3D部品接合は拒否。
- 内部頂点の追加は許可するが元の境界頂点や境界辺は維持する。API返り値は独立meshであり既存オブジェクトへのpatch適用ではない。
- 補間されたポリゴン同士の直線loftなので曲率・接線連続性・一般三角形最適解は保証しない。
- 検出器改善ではなく実際の生成meshを独立CGALと解析輪郭で評価する。
- CGALは研究専用の検証依存でありCBDK本体へ組み込まない。

## 根拠

- Blender [BMesh bridge](https://docs.blender.org/api/current/bmesh.ops.html#bmesh.ops.bridge_loops) と [GUI mesh bridge operator](https://docs.blender.org/api/dev/bpy.ops.mesh.html#bpy.ops.mesh.bridge_edge_loops)。後者の中間cut/surface補間は未比較。
- Klein, Schilling, Straßer (2000), *Reconstruction and Simplification of Surfaces from Contours*, Graphical Models 62(6), doi:10.1006/gmod.2000.0530。輪郭間の対応と中間輪郭が本質的問題であることを参考とした。論文実装を再現したとの主張はしない。
- R4 [RESULTS](../r4/RESULTS.md)、[FROZEN](../r4/FROZEN.json)。R4の実験・評価は改変しない。

## 再現コマンド

```bash
cd research/geometry_lab
python -m pip install -r requirements-oracle.txt
python -m unittest discover -s tests -v
python -m cycles.r5.run --output runs/r5-first-evaluation.json
```

研究専用CIはR2〜R4を保持し、R5新評価を追加。Blender本体はR5 CIでは動作しない。入力はsyntheticのみで非公開3Dモデルや画像は読み込まない。
