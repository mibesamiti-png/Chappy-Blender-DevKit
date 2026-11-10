# R9 — 内部エッジ反転による局所三角形品質改善（2026-11-11 JST）

## 結論

**事前登録した研究ゲートは達成。ただしCBDK本体への採用は保留（`approved=false`）。**

R8で残った逆向き細長形状 `r8_slender_opposite` について、R8の生成済みメッシュの**内部エッジを最大3パスで反転**させた。入力境界頂点の座標も、元境界の辺も、頂点数・三角形数も変更しない。旧R8失敗の最小三角形品質 **0.078598 → 0.127179** に改善し、独立CGAL判定・解析的形状誤差・境界・トポロジー基準も合格した。

### 評価方法・実行環境

- 事前登録: [R9 RESEARCH.md](RESEARCH.md)。研究候補は `cbdk_geometry.flip_loft.conservative_flip_loft` **1つ**。対象はXY投影がstar-shapedかつZ包絡が分離した上下非平面輪郭のみ。R8の `tapered_radial_loft` は変更していない。
- Blender公式アーカイブ **4.4.3**、SHA256照合 `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946`。比較3方式: 固定R9・固定R8・Blender標準Bridge（3 cuts / LINEAR）。
- 既知16人工ケース（R7/R8の旧データ）と新規固定holdout 6人工ケース、合計**22形状×3方式=66出力**、各方式1ウォームアップ+3計測（計198回の時間計測）。新6ケースは検証開始前に確定し、検証後のアルゴリズム・fixture調整は**0回**。実際のモデルや私有アセットは使用せず、第三者blind corpusでもない。
- Blender生成から独立したPython3.12+CGAL6.0.1 oracleで66出力すべて評価。自己交差 **0**、oracle_unavailable **0**、元境界頂点/辺とトポロジー保存を検証。基準：三角形最小品質≥0.1、解析3D loft RMS≤0.12、max≤0.28、連結成分1、Euler=0、非多様体0、CGAL交差0。
- 局所辺反転は、共有面の向き、隣接三角形法線、新旧対角線の重複、局所最小品質の改善を条件に採用する。ただし内部条件だけでは大域的な交差ゼロを保証しないためCGALの独立確認を必須とする。

## 事前基準と実測

| 指標 | R9 | 凍結R8 | Blender 3-cut LINEAR |
|---|---:|---:|---:|
| **既知16形状・合格** | **16/16** | 15/16 | 11/16 |
| **新規未使用6形状・合格** | **5/6** | 4/6 | 2/6 |
| 新規6形状・平均最小三角形品質 | **0.30988** | 0.26164 | 0.11950 |
| 新規6形状・平均三角形数 | **195.5** | **195.5** | 341.8 |
| 新規6形状・生成時間のケース中央値（ms） | **90.93** | **7.26** | 2.82 |
| 新規6形状・平均RMS | **0.02122** | 0.02134 | 0.04556 |

**時間の注意:** R8とR9は同系統のPython detached-mesh生成で比較でき、R9はR8の約12.5倍遅い。Blender nativeは編集モード・メッシュ生成・三角分割などの経路が異なり、速度の直接倍率比較はしない。R9は品質改善を時間で買う方式であって常用前提ではない。

| 新規holdout | R9最小品質 | R8最小品質 | Blender最小品質 | R9合否 |
|---|---:|---:|---:|---|
| `r9_reverse_narrow` | 0.080778 | 0.048220 | 0.023815 | **不合格** |
| `r9_forward_narrow` | 0.261271 | 0.158824 | 0.069014 | 合格 |
| `r9_reverse_skew` | 0.155966 | 0.096875 | 0.044226 | **合格（R8不合格から改善）** |
| `r9_lobed_offset` | 0.312030 | 0.216669 | 0.129324 | 合格 |
| `r9_sparse_ridge` | 0.550364 | 0.550364 | 0.201628 | 合格 |
| `r9_opposed_waves` | 0.498885 | 0.498885 | 0.248995 | 合格 |

新規ケースでR8より**最小品質が≥0.02改善したのは4/6件**（reverse_narrow、forward_narrow、reverse_skew、lobed_offset）。2件は反転なしで品質不変。新6ケースのR9はすべて元のR8と**頂点座標配列・頂点数・三角形数が完全一致**（面インデックスのみ変化）。新6ケースの自己交差は0。

### 研究ゲート（事前固定）の確認

- R8で失敗した既知reverse slenderが品質≥0.1を含む全条件で合格 → **達成**（0.127179）。
- 過去のR8合格15/15をすべて維持 → **達成**。R9既知16/16。
- 新規holdout R9≥4/6、かつR8より劣らない → **達成**（R9 5/6、R8 4/6）。
- 新規holdoutのうち≥2件で最小品質差≥0.02 → **達成**（4件）。
- CGAL交差0、元境界保存、トポロジー有効、R8と同じ頂点座標・面数 → **達成**、全66件においてoracle欠落なし。
- 新holdoutに合わせたソース改良0件 → **達成**。

## 未解決・不採用・悪化

**不合格 `r9_reverse_narrow`:** R9 q=0.080778で閾値0.1に届かない。R8の0.048220より改善したが、まだ採用成功に数えない。解析RMS=0.03001、CGAL交差0でも品質は不合格。結果を見てR9を再調整していない。

**処理コスト:** ケース中央値約90.9msはR8約7.26msに対して大幅増。最大3パスで各三角形の局所品質・法線・辺マップを複数回計算するため。三角形の接続を変えるため、局所では良くても視覚曲率・材質・UV・法線連続性を損なう可能性がある。今回の人工解析誤差はわずかに改善しているが、実作品の見た目向上は未証明。

**対象外:** star-shapedでないXY輪郭、Z包絡重なり、任意方向に傾いた3D境界、枝分かれ、既存実作品のUV/Normal/材料/Undo/操作時間、Blender4.4.3以外、第三者blind品質評価、極端なスケールや大きなメッシュ。CGALの無交差結果もこの66人工条件に限る。

## 証拠 / 再現

- [初回実測 R9専用 CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42911818095)（`r9-conservative-interior-edge-flips` SUCCESS）。生成と評価を異なるPythonランタイムで実行。GitHub Actions artifact `geometry-lab-r9-*` の `ci-r9-raw.json`（全66メッシュ・生タイム）と `ci-r9-eval.json`（全ケース品質・CGAL判定・ハッシュ）、保持14日。
- 生成時の実ソースSHA256:
  - `cbdk_geometry/flip_loft.py`: `1321fa5ee5ca6935f6cce29b39c3b5bca363649f152558e9a14b75a29f3d2aa1`
  - `cycles/r9/fixtures.py`: `a3f837bf5e4b28e4eb7d1617173f17acf576d1778a374852a9f5f7996bd1ec65`
  - `cycles/r9/blender_run.py`: `f7e30e756a93214e797d3aafb0645872205111499908eba3f3e13d0d708e43b1`
  - `cycles/r9/evaluate.py`: `0f0bc1e77afbd3fc9812dbf848807a0828092d9d32f8855067dca3c2d86b20bf`
- `research/geometry_lab` で検証済みBlender4.4.3、`requirements-oracle.txt`を用意して再現:

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python cycles/r9/blender_run.py -- --output runs/local-r9-raw.json
python -m cycles.r9.evaluate --input runs/local-r9-raw.json --output runs/local-r9-eval.json
```

## 終了判定

**R9は一サイクル終了。研究候補として維持、製品への自動採用はしない。** PR #114はDraftで未マージ、A司令塔の統合判断待ち。R1〜R8のソース・研究記録・凍結fixtureは未変更。ABCD・Development Intelligence Lab・main/STATE/Handoffは未変更。R10は自動開始しない。

次サイクルが必要なら、実際の3D作業モデルでのUV/法線と視覚品質、または今回の未知データに依存しない品質改善アルゴリズムの独立研究を優先する。今回の新規R9 holdoutをR10では「既知」として扱う。
