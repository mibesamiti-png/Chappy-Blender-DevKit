# R4 — 境界ループ接続を実制作能力として評価する

## 再評価・選定

起点 `272769a` / Draft #114。R3の26テスト、CGAL照合、R1再判定は検出の信頼性を改善したが、生成器そのものを改善した証拠ではない。R1の旧判定変更（成功2→7）は評価器の変更であり制作能力向上とは数えない。R4でも旧R1/R2/R3記録は上書きしない。

候補の優先順位:

1. **異なる頂点数・開始点・向きの境界をつなぐ面生成**。チューブ、開口部の遷移、部品間のスリーブに使える。入力境界を動かさず接続できるかを標準Blenderと比較可能。今回選択。
2. 形状保存制約付き接続・局所リメッシュ。細長い三角形と過大な形状変化を両立して減らす。R4の失敗で優先度上昇、次サイクル候補。
3. 既存union/voxelの細部保存・薄肉形状の修復。実用価値は高いが独立した形状誤差の設計が先。
4. 検出器の追加高速化、操作履歴からの模倣学習。今回は出力形状の改善を優先。後者の実ユーザーデータは収集しない。

「できるようになること」は順序付き2ループから独立した三角形帯を返すAPI。これはCBDKへの正式登録、既存meshへの縫合、法線/UV/材質の保持、GUI操作の完成を意味しない。向き・開始点の手動指定を省くが、人間の制作時間短縮は未測定。

## 原理と出典

- Fuchs, Kedem, Uselton (1977), *Optimal Surface Reconstruction from Planar Contours*, CACM 20(10)。[一次論文PDF](https://www.cs.jhu.edu/~misha/Fall13b/Papers/Fuchs77.pdf)。隣接輪郭間の三角形生成を有向トーラスグラフの最小費用閉路へ変換する。本文のelementary tileとgraph reductionを確認した。本試作は着想を利用した独自実装で、論文の完全な最適閉路アルゴリズムの再現ではない。
- [Blender BMesh API](https://docs.blender.org/api/4.3/bmesh.ops.html#bmesh.ops.bridge_loops)、[制作操作としてのBridge Edge Loops](https://docs.blender.org/manual/en/4.3/modeling/meshes/editing/edge/bridge_edge_loops.html)。公式ページの全文取得はアクセス制限で未確認。検索要約だけで互換性を断定せず、実際の4.3.2/4.4.3 BMesh呼び出しを確認した。
- [Blender 4.3.2 OSS実装 bmo_bridge.cc](https://github.com/blender/blender/blob/v4.3.2/source/blender/bmesh/operators/bmo_bridge.cc)。`bm_bridge_best_rotation`は対応点距離和で開始位置を選ぶ。異なるループ長を処理する分岐がある。ライセンスはヘッダでGPL-2.0-or-later確認。ソースのコピー/移植はせずインストール済みBlenderのAPIを呼ぶ。
- [CGAL Polygon Mesh Processing](https://doc.cgal.org/latest/Polygon_mesh_processing/index.html)。自己交差は既存R2のCGAL oracleで検証。トポロジーが正しくても幾何的に正しいとは限らない。CGAL bindingsはGPL-3.0-or-later/commercial、任意検証環境のみ、ランタイム配布に含めない。NumPy BSD-3-Clause、Blender GPL-2.0-or-later。論文図・コード・外部モデルを転載しない。

|方式|原理・計算量（n,mは頂点数）|利点|失敗条件|
|---|---|---|---|
|index|頂点数比に沿い両ループを進む。O(n+m)|安価な基準|開始点/逆順に弱い|
|phase|両方向・全m開始点を探索しindexの辺長二乗和を最小化|単純、境界保持|局所密度差で細長い面|
|dp|同じ探索に帯幅0.45の単調格子DP。O(n m²)、メモリO(nm)|対応と三角形配置を調整|最短辺が目標形状を壊す。非交差/滑らかさ保証なし|
|Blender標準|BMesh bridge + triangulate|既存C++実装、周辺エコシステム|粗い輪郭・大きい横ずれで形状誤差|

独自方式はNumPyのみ、Blender内でも外でも実行可能。DP目的は正規化した三角形の辺長二乗和。面積や曲率を最適化していない。帯制約と退化候補除外があり、全ての可能な曲面での大域最適性は主張しない。

## 凍結・予算・停止

開発4形状を先に検証。`FROZEN.json`にアルゴリズム、fixture、評価器のSHAと閾値を初回holdout実行前に保存。以後これら3ファイルは無変更。holdoutは6 **ケース**、4種類の輪郭（circle/ellipse/lobed/superellipse）。FROZENの「6 families」は不正確であり、6つの独立形状族という意味ではない。未知の実作品・第三者が秘匿したblind datasetではなく、同じ研究者が作った別パラメータ群である。

2版 × 10形状 × 4方式 × 3反復 = 240生成。1ループ3..48頂点、最大96開始点/方向候補、API時間予算10秒（候補境界で確認、厳密な強制停止ではない）、各Blenderプロセス300秒。調整は開発段階のみ、holdout後モデル変更0回。oracle例外は成功扱い禁止。改良停止条件は凍結評価の完了、時間超過、独立oracle障害。失敗を見て同じholdoutへ再調整しない。各プロセスは逐次実行。メモリ最大値・大規模meshは今回は未測定。

4.4.3は公式配布SHA-256を照合:
`8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`。

全入力をfloat32丸め後に各方式へ同一供給。Blender内のobjects/meshes/selection集合の不変を確認。既存ユーザープロジェクトは開かずfactory-startupのみ。標準方式はBMesh直接呼び出し+三角化で、GUI operatorのcuts/smoothness全探索ではない。
