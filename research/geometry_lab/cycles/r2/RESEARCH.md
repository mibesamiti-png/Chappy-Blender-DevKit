# R2 — 交差判定の独立検証と共有境界の厳密分類

開始/調査日: 2026-11-10 JST。親研究コミット159e89f、PR #114、既存研究を保持して追記。

## 再評価・テーマ選定

Git fetch後、研究HEADは159e89fac6110a87511c5e6b664480b01ebc38e9、devは8665a3cのまま。README/RESEARCH/RESULTS、実装、テスト、PR、並行ルールを再読。既存14テストを再実行して成功。旧PRのPython/Chromium/Handoffの3CIはすべてsuccessとAPI確認。ただし研究テストは未配線で、これらは旧SATの信頼性の証拠ではない。

| 優先 | 候補 | 価値・依存・見送り理由 |
|---|---|---|
| 1 / 今回 | 交差検出の独立oracle + 共有simplex分類 | 接合の成功/失敗を決める基盤で、現在の偽判定は全後続研究に波及する。小さな解析例で原因を切り分けられる |
| 2 | 一般の接続meshへのCCD | AI編集の安定性に重要だが、静的な正しさと接触の意味を先に定める必要 |
| 3 | 境界ループbridge・曲率連続 | 制作品質の改善。交差の評価基盤と対応点の仕様が必要 |
| 4 | 操作記録・模倣学習 | 長期有望。今は幾何の誤った報酬/評価を学習へ伝播しないことを優先 |

## 原因仮説と実証

旧SATは面を重心方向へ1e-7縮めて共有境界を除外するため、細い本物の交差も削る。さらにglobal bbox由来のepsが正の隙間を接触とみなす。これは単なる数値丸めだけでなく、判定対象の形状/意味を変える設計である。既存結果のhitは「確定交差」ではなかったため、旧結果を消さず再分類する。

改善案は、元の三角形の交差集合Iを求め、実際の共通頂点IDが表すsimplex SにIが含まれる場合だけ正常な共有境界とする。座標一致だけで頂点をweldしない。異なるID同士の点接触もhitという契約を維持。

## 技術資料と候補の比較

- [Shewchuk, 1997 / 著者の解説・実装](https://www.cs.cmu.edu/~quake/robust.html): 行列式の符号が丸めで反転する問題と、誤差評価に応じ精度を上げる手法。今回の実装はそのexpansion arithmeticの移植ではない。
- [CGAL intersectionの定義](https://doc.cgal.org/latest/Kernel_23/group__intersection__linear__grp.html): 面内部も集合に含め、結果の点/線分/面を区別する根拠。
- [CGAL EPECK](https://doc.cgal.org/latest/Kernel_23/classCGAL_1_1Exact__predicates__exact__constructions__kernel.html): predicateとconstructionの両方を厳密にする選択肢。
- [Python Fraction](https://docs.python.org/3/library/fractions.html): floatからの変換は入力binary64値を正確に保持し、人が意図した10進数への復元ではない。
- [CGAL SWIGのkernel定義](https://github.com/CGAL/cgal-swig-bindings/blob/main/SWIG_CGAL/Kernel/typedefs.h): 配布bindingはEPICK系で、EPECKそのものを導入できたと主張しない。今回使用するのはkernel do_intersectとPMP self_intersectionsで、交点constructionをoracleとして比較しない。

| 方式 | 原理・前提 | 精度/効率/保守性 | 今回の判断 |
|---|---|---|---|
| 旧SAT + inset | 分離軸、許容差、共有面縮小 | 速めだが入力形状を変える。微小隙間・共有頂点付近に誤判定 | 変更せず比較baselineとして保存 |
| rational clipping | 辺–面の交点/共面線分を三角形の3半平面でclip。両面の辺から交差集合の極点を集め、共有simplex包含を判定 | binary64に対し丸めなし。純Python標準FractionでBlender同梱Pythonから利用可。ただし遅く大規模には不向き | 小規模参照実装として追加 |
| rational clipping + 厳密AABB除外 | min/max比較のみで非重複を除外。残りは同一rational処理 | 判定を変えず不要clipを省く。mesh版はbroad phase全走査も予算へ算入 | 既定候補。filtered/unfiltered一致も検査 |
| adaptive predicates/native CGAL | 近接時に精度を上げる、native spatial acceleration | 高速だがC++/wheel/ライセンス・Blender ABI依存 | 独立oracleとしてのみ採用。製品依存にはしない |

Rational clippingの前提: 非退化三角形、有限binary64座標、絶対値1e100以下。退化は明示拒否。intersectionの極点は両三角形の境界上にあるので、6辺と対向面のclipで包含・共面も扱える。convexな共有simplexへの全極点包含を用いる。ソフトウェアの形式証明ではなく、certified=falseを維持。

## 実験・停止条件

- 解析15条件×3スケール×向き2 = 90ケース。微小隙間、共有辺/共有点のsliver、正常共有境界、重複面を含む。
- 3方式は同一入力、1warmup+3回。seed=20261110の128ランダムペアをCGALと比較。degenerateは記録して拒否、勝手な再抽選なし。
- 任意依存が欠けたときbenchmarkは失敗。外部oracle無しを成功とはしない。
- 3つの旧Blender fixtureを同じ4.3.2で再生成し、全ペア集合をCGALと照合。3回計測・warmupなし。新方式1呼出し90秒/200万broad phase走査/2048面まで。未完了はpairs=null。
- 研究プロセスtimeout300秒、benchmark内部240秒。CI10分。異なるCPUの時間を速度保証に使わない。
- パラメータ探索なし。精度不一致が1つでもあれば昇格停止、同一集合を検証してから記録。CGALが正しい形状を保証するという主張でもない。

## 依存と失敗記録

CGAL Python binding `6.0.1.post202410241521`、NumPy2.3.5を研究用venvへ導入。wheel METADATAのGPLv3+分類とLICENSE.GPLを確認。bindingはGPL-3.0-or-later / commercial、CGAL本体にはLGPL/GPLの区分がある（[公式](https://www.cgal.org/license.html)）。CGALコード/バイナリはリポジトリや製品配布物に含めない。oracle専用adapterはテストコードであり、正式な商用/製品採用・再配布許諾は別途必要。

初回oracle adapterでSWIG Facet_pairをPython tupleとしてunpackすると例外。bindingの__getitem__がindex modulo 2で、範囲外IndexErrorを返さない実装だったためfirst/second propertyを明示利用して修正。初回計測は不成立とし、完成結果は再実行したものだけを保存。

## 次の判断

R2は静的判定の改善であり、任意meshの安全編集を完成させない。優先候補は(1) exact対象を安全に絞るpredicate filter/BVHの速度改善、(2)退化面の由来とnative Boolean出力の接触分類、(3)対象Blender3版で同一fixture検証。その後CCDへ進む。外部ライブラリの単なる速さを理由に製品へ自動採用しない。
