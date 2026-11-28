# R1実測結果 — 2026-11-10 JST

**履歴記録（159e89f）。交差判定は[R2の独立再評価](cycles/r2/RESULTS.md)で一部訂正・補足。以下の旧成功率を一般的な精度として使わない。**

Python 3.12.14 / NumPy 2.3.5 / Linux、ローカルBlender 4.3.2。人工fixtureのみ。研究ソースのSHA-256は各JSONに保存し、記載された全ファイルの現行hash一致を確認。後から追加した別実験のスクリプトは以前の記録のmanifestには含まれない。

## 自動検証

- 研究unittest: **14件成功**（解析的正解、共面、接触、隣接折り返し、共有頂点、退化拒否、sweep一致、移動途中の突き抜け、保守的拒否）。
- 既存CBDK: `python -m unittest discover -s tests` → **1101件実行、6件skip、失敗0**、106.445秒。新研究テストはこの1101件に含まれない。
- `python scripts/project_handoff.py --check` → current。書き込みオプション未使用。
- 研究検出: **36/36条件一致、FP=0/FN=0**。これは6種類×3スケール×2実装の限定fixtureで、一般精度ではない。
- 移動: 終点hit=0・中点hit=1の突き抜け提案をalpha=0.25へ制限。中央値0.326ms。共有頂点meshは未対応として拒否。
- Blender main実験は退化出力の拒否1件を含みexit=1。結果JSONは保存済み。これは成功実行扱いしない。追加failure probeで同拒否を3回再現しcleanupも確認、probe自身はexit=0。
- 追加rotated実験exit=0、全成功を意味しない（2候補中1候補のみ品質ゲート合格）。

## 検出時間（ms、warmup後3回中央値）

| 分布 | 面数 | 全ペア | sweep | narrow phase検査数（全ペア→sweep） |
|---|---:|---:|---:|---:|
| sparse | 32 | 140.055 | 0.099 | 496 → 0 |
| sparse | 128 | 2401.728 | 1.247 | 8128 → 0 |
| sparse | 256 | 13705.428 | 8.406 | 32640 → 0 |
| dense | 32 | 100.984 | 96.025 | 496 → 489 |
| dense | 64 | 373.978 | 390.217 | 2016 → 2002 |

全条件でペア集合一致。sparseはAABB候補0の最良寄り条件で、一般的な高速化率として扱わない。dense64ではsweepが約4.3%遅い。broad phaseは最悪二乗、pair_budgetはnarrow phaseの上限であり厳密なCPU時間上限ではない。

## Blender接合（14候補）

**合格2、品質ゲート不合格8、退化出力の拒否1、接線接触で保留3**。hitは浮動小数点/隣接近似の接触候補も含むため、不合格をすべて確定自己交差と解釈しない。

| 条件 | 手法 / voxel | 状態 | 接合ms | 体積誤差% | 成分数 | hit候補 | 最小三角形品質 |
|---|---|---|---:|---:|---:|---:|---:|
| overlap | exact | 退化出力拒否 | 別probe 181.25 | — | — | — | — |
| overlap | voxel / 0.2 | failed | 49.65 | 5.50 | 1 | 8 | 5.16e-06 |
| overlap | voxel / 0.1 | failed | 66.81 | 3.29 | 1 | 8 | 1.03e-05 |
| thin_neck | exact / None | failed | 327.46 | 2.79 | 1 | 5 | 3.88e-07 |
| thin_neck | voxel / 0.2 | failed | 65.82 | 5.65 | 1 | 4 | 5.76e-06 |
| thin_neck | voxel / 0.1 | failed | 116.44 | 3.24 | 1 | 4 | 1.07e-05 |
| tangent | exact / None | ambiguous_contact | 139.05 | 2.82 | 2 | 36 | 0.405 |
| tangent | voxel / 0.2 | ambiguous_contact | 24.62 | 6.32 | 1 | 8 | 5.16e-06 |
| tangent | voxel / 0.1 | ambiguous_contact | 54.64 | 3.57 | 1 | 8 | 1.03e-05 |
| gap | exact / None | passed | 139.76 | 2.82 | 2 | 0 | 0.405 |
| gap | voxel / 0.2 | failed | 21.38 | 5.32 | 1 | 8 | 5.16e-06 |
| gap | voxel / 0.1 | failed | 47.46 | 3.87 | 2 | 8 | 1.03e-05 |
| rotated_overlap | exact / None | failed | 415.25 | 2.45 | 1 | 3 | 2.66e-07 |
| rotated_overlap | voxel / 0.15 | passed | 70.29 | 4.23 | 1 | 0 | 0.132 |

出力が得られた13候補は境界辺0・3面以上共有辺0。これだけでは微小接触やvertex manifoldを判定できない。gapのvoxel=0.2は本来2成分を1成分にするため不合格。rotated voxel=0.15は1成分・hit0・体積誤差4.23%で合格した。Booleanは曲率連続化処理ではなく、細い三角形が残る。

接合時間に交差検出は含めない。検出時間はblender.jsonに別記し、最大数十秒。追加rotatedでは検出時間は未計測。退化拒否の時間は失敗probe3回中央値（warmupなし）で、通常成功時間と計測条件が異なる。

## 既存CIと今回の証拠の区別

起点8665a3cの7workflowがcompleted/successであることをGitHub APIで確認。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42440811503)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42440811589)。これは研究コードのCI結果ではない。

研究専用CIは未配線。Blender対象3版、Windows、GUI、実ユーザーmesh、G1/G2連続、材料/UV、完全CCD、厳密交差oracleは未検証。4.3.2のローカル結果を対象3版の成功に流用しない。次の研究はRESEARCH.md参照。

## R3追補

[R3再評価](cycles/r3/RESULTS.md)でR1全14候補をCGAL判定に置き換えて再検査。旧集計は履歴として保持し、新判定と区別する。
