# R3実測結果

2026-11-10 JST。環境はenvironment.json、ソースhashと各試行はresults.json。予備計測はpilot_results.jsonとして残し、以下は自前の他実験が終了してから再計測したもの。共有ホストの外部負荷は制御していない。

## 精度・汎用性・速度

研究26テスト成功（CGAL検査も実行）。解析90条件は両variantとも期待値と一致。7つのmeshではR2 / cached / shortcutの全ペア集合が独立CGALと全試行で一致。

| 入力 | 面数 | hit数 | R2秒 | cacheのみ秒 | shortcut秒 | R2/shortcut |
|---|---:|---:|---:|---:|---:|---:|
| torus | 256 | 0 | 2.40198 | 2.08803 | 0.44302 | 5.42× |
| saddle | 242 | 0 | 1.90224 | 1.58125 | 0.56864 | 3.35× |
| folded | 242 | 53 | 2.82623 | 2.25806 | 1.32467 | 2.13× |
| sparse | 64 | 0 | 0.00304 | 0.00713 | 0.00773 | 0.39× |
| voxel_overlap | 1268 | 0 | 9.31471 | 7.19723 | 1.13541 | 8.20× |
| exact_thin_neck | 1076 | 3 | 7.78774 | 6.28126 | 0.64815 | 12.02× |
| exact_rotated | 1078 | 4 | 8.40905 | 6.57897 | 0.79748 | 10.54× |

全体191.8秒。各方式3回、warmupなし、方式順を回転。面準備・bbox・判定を含むend-to-end時間。native/Python peak memoryは今回未計測。

トーラス・鞍型開曲面・自己交差する折り返し面でも一致。折り返し面の53組を保持した。疎な64面では事前変換の負担で約2.5倍遅くなった。したがって全入力向けの既定API置換は不採用。比較可能なreview-only APIとして追加する。

予備計測でBlender再生成と重なり大きなばらつきが出たため、最終速度には使わない。再計測は1回に限定。上記の速度倍率はこの入力・環境での観測値で、CGAL nativeより高速という意味ではない。

## R1全14候補の再評価

CGALを合否判定に使い、生成・体積誤差8%・成分数・境界辺・非多様体辺の条件を維持。新しい自作検出器で自分を合格判定していない。

**旧: 合格2 / 品質不合格8 / 退化出力拒否1 / 接線保留3 → 新: 合格7 / 不合格3 / 拒否1 / 保留3。**

| 条件 | 方式 / voxel | 旧判定 | CGAL再評価 | CGAL hit |
|---|---|---|---|---:|
| overlap | exact / None | error | rejected | — |
| overlap | voxel / 0.2 | failed | passed | 0 |
| overlap | voxel / 0.1 | failed | passed | 0 |
| thin_neck | exact / None | failed | failed | 3 |
| thin_neck | voxel / 0.2 | failed | passed | 0 |
| thin_neck | voxel / 0.1 | failed | passed | 0 |
| tangent | exact / None | ambiguous_contact | ambiguous_contact | 0 |
| tangent | voxel / 0.2 | ambiguous_contact | ambiguous_contact | 0 |
| tangent | voxel / 0.1 | ambiguous_contact | ambiguous_contact | 0 |
| gap | exact / None | passed | passed | 0 |
| gap | voxel / 0.2 | failed | failed | 0 |
| gap | voxel / 0.1 | failed | passed | 0 |
| rotated_overlap | exact / None | failed | failed | 4 |
| rotated_overlap | voxel / 0.15 | passed | passed | 0 |

5件の不合格→合格は旧検出器の偽陽性を訂正したもの。モデルを改善・修復した成果ではない。極細三角形の低い品質値は残る。今回の成功条件を通過しても制作向けの良い面流れや物理的適合は保証しない。

薄い首と非対称Exact Booleanの接触、粗いVoxelによる隙間消失、対称Booleanの退化出力は未解決。接線の3件はCGAL hitが0でも保留を維持する。生成前の理想的な球の接触と、丸められた出力meshの点接触を混同しない。

再生成はBlender4.3.2のみ。旧R1の生成式・パラメータを再使用した比較で、旧実行時の全頂点snapshotを同一hashで証明した比較ではない（R1はsnapshot未保存）。高速化benchmarkの3入力はR2保存snapshotのhashと照合している。

## 未検証・次の研究

対象Blender4.4.3/4.5.15/5.2.1、Windows/GUI、実データ、native memory、完全CCDは未検証。次は対象版で同一fixtureを検証し、退化面/接触の版差を調べる。次点は疎なmesh向け遅延キャッシュ。新方式は正式採用せず、旧APIと旧結果を保持する。

研究専用CIはR2とR3 benchmark、26 unittestを実行する。Blender全14候補の再生成はローカル実測でありCIには含めていない。厳密な最終HEADのCIリンクはPR #114に記録する。
