# R5 実測・失敗・結論（2026-11-11 JST）

## 決定

**R5の事前設定した研究ゲートは達成。研究用の形状生成方式として残すが、CBDK本体への採用は保留（approved=false）。**
今回の候補は`cbdk_geometry.radial_loft.radial_loft(a,b,cuts=3)`の1つのみ。CGALを独立oracleとし、形状誤差・元境界・トポロジー・三角形品質を検証した。R4の既存ソース・データは一切変更していない。未使用holdoutの結果を受けてアルゴリズム調整0回。

## 集計と比較

|データ|Radial Loft R5|比較対象|比較対象合格|
|---|---:|---|---:|
|R4から開発用へ移行した既知6件|**5/6**|R4 Blender4.4.3直接BMesh Bridge（保存済み）|4/6|
|R4の元開発4件|4/4|—|—|
|**新規固定holdout5件**|**4/5**|同一入力のphase|3/5|

R4の6件はR5の新規holdoutではない。Blender標準4/6はR4で実測・保存した値で、R5でBlenderを再実行したわけではない。新しいholdoutではBlender-nativeを測定しておらず、BlenderのGUI`number_cuts`・補間設定との比較も未実施。**R5がBlender標準全般に勝ったと主張しない。**

### 新規holdout（今回初回実測、各生成3反復）

|人工ケース|R5/phase|R5最小品質|phase最小品質|R5 RMS|phase RMS|R5中央値ms|phase中央値ms|
|---|---|---:|---:|---:|---:|---:|---:|
|r5_lobed_asymmetric|合格/合格|0.4536|0.1374|0.0151|0.0106|3.051|23.618|
|r5_ellipse_offset|**不合格/不合格**|0.0634|0.0722|0.0203|0.0157|2.746|15.835|
|r5_superellipse_skew|合格/合格|0.1914|0.1625|0.0279|0.0164|2.148|9.213|
|r5_slender_offset|**合格/不合格**|0.1022|0.0483|0.0086|0.0054|3.327|6.495|
|r5_lobed_wide|合格/合格|0.1833|0.2143|0.0448|0.0360|3.086|18.048|

すべての新規holdout出力10個で、CGAL交差0・元の境界エッジ集合完全保持。R5の5出力は非多様体辺0・Euler=0・連結成分1。成功と失敗は当初設定の基準（最小三角形品質≥0.1、重心評価RMS≤0.08、最大誤差≤0.2）で判定した。phaseは全5ケースでR5よりRMSが小さい一方、細長い横ずれ形状の最小品質が0.0483で不合格。**複数の品質軸で一方が全面的に優れているわけではない。**

### 旧R4の6件（R5では既知開発データ）

|ケース|R5|R5最小品質|R5 RMS|R5最大誤差|
|---|---|---:|---:|---:|
|holdout_lobed|合格|0.5627|0.0304|0.0642|
|holdout_superellipse|合格|0.1704|0.0110|0.0220|
|holdout_offset|合格|0.1224|0.0146|0.0472|
|holdout_lowpoly|**不合格**|0.2117|**0.1039**|0.1780|
|holdout_slender|合格|0.1609|0.0101|0.0370|
|holdout_far_offset|合格|0.1600|0.0261|0.0565|

R4のfar_offsetでBlender直接BridgeのRMSは0.2005・最大0.5503だった（R4保存結果）。R5は0.0261・最大0.0565。radial対応が有利な人工入力では形状を保ちやすい。ただし、三角形数が増え、実モデルの見た目・曲率の改善を証明しない。R4のlowpolyではRMS 0.1039で形状誤差が残り、**失敗を採用成功として数えない**。

## 実測環境・再現性

- CI実測: [Geometry Lab CI #42898272486](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42898272486)、Python3.12.16 / NumPy2.3.5 / CGAL6.0.1.post202410241521。研究33 unittest成功、R2/R3/R4/R5検証・artifact成功。
- ソースSHA-256:
  - `cbdk_geometry/radial_loft.py`: `0b404cc2f5b8b6440b7ab44035a608a41942c8efb329c2a3028df014d175c7ac`
  - `cycles/r5/fixtures.py`: `3ee0c363b5f60e7e8d7955748c2423cfd53ca3808af4ccb5d44b8302bacfd972`
  - `cycles/r5/run.py`: `ba7f823307c369d873d46f45148f5e1e868a3a7df45c63c7821445233e8e45f0`
  - `cycles/r4/results/blender443.json`: `0ed047bf4a7246e19d90085c7ae7cc0aec9ef36d7bcb24a99f0c449f98a10d44`
- `python -m cycles.r5.run --output runs/NEW_R5.json`で再現。生の全ケース・反復時間・source SHAを含むJSONは上記CI artifactの`ci-r5.json`（GitHub Actions保持期間14日）。新しい名前を指定し既存出力を上書きしない。
- 同じCI runnerでのphase比較ではR5 2.15〜3.33ms、phase 6.49〜23.62ms（生成+Mesh構築、oracle時間なし）。小標本・warmupなし。R4のBlenderネイティブ測定は別環境であり**速度倍率を出さない**。BlenderはR5で`not_run`。
- R4の4+6形状は合計10開発ケース。新規5形状は同一研究者が別パラメータで作った人工ケースで、第三者のblind datasetでも実際の制作物でもない。

## 不採用・限界・次の研究

- **不採用として残すもの**: 低ポリゴンの形状保存改善（まだRMS不合格）、横ずれ楕円の三角形品質（R5=0.0634）、R5がphaseより常に誤差を減らすという仮説（偽）。
- **改善したもの**: 既知R4のfar_offsetと新規slender_offsetの合否、元境界エッジ集合を保った追加断面生成。研究用APIの実測可能性。
- **悪化したもの**: phaseより出力頂点/面数が増加、人工R5新5形状すべてでphaseよりRMSが大きい。Blender nativeとの速度未比較。
- **未検証**: GUI標準Bridgeのcuts/interpolation、Blender4.4.3/4.5.15/5.2.1でのR5生成、非平面/非star-shaped境界、既存meshへの縫合・法線・UV・材質、第三者モデル、人手作業の削減、面積加重/Hausdorff/視覚品質、peak memory。
- **次の一サイクル候補**: Blender GUI標準Bridge（cuts/interpolation含む）を同じ人工メッシュに対して測り、R5の追加頂点コストに見合う実用差があるか確認。今回自動着手しない。

A司令塔承認までCBDK本体に統合しない。通常ABCD/Development Intelligence Labは変更しない。実モデル・画像を公開しない。
