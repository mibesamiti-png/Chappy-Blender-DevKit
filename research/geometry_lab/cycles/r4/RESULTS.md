# R4 実測と判断

## 結果

2版とも40出力の頂点/面配列が完全一致。各方式の3反復も一致。CGAL独立検証、境界頂点保存、辺次数/連結成分/Euler特性、解析輪郭への誤差を評価。全30研究unittest成功（R3まで26 + R4の4）。

|方式|開発合格/4|未使用合格/6|未使用6件の中央値 ms: 4.3.2|同: 4.4.3|未使用平均RMS|
|---|---:|---:|---:|---:|---:|
|index|0|0|1.240|0.951|0.3474|
|phase|4|2|15.913|21.292|0.0251|
|dp|4|3|62.077|70.271|0.0859|
|Blender標準|4|4|1.193|0.816|0.0651|

時間は各形状3反復の中央値を取り、その6件の中央値。全失敗ケースも含む。形状生成+Mesh構築を含みCGAL検証時間を含まない。4.4.3起動時に4.3.2の独立評価が約0.9秒重なったため、細かな版間速度差には意味を持たせない。単一ホスト、warmupなし、小標本である。

**結論: DPは単純接続より3/6件改善、phaseより1件改善。しかし標準より合格1件少なく、中央値比約52倍/86倍遅い。標準の置き換えに採用しない。** 研究APIとして比較用に保存し、`approved=false`を維持。検出能力から生成能力への評価軸は追加できたが、既存Blenderを超える制作能力向上は実証できていない。

## 合否基準と独立性

事前固定: 頂点座標multiset完全保存、境界辺数n+m、非多様体辺0、連結成分1、Euler=0、CGAL交差0、最小三角形品質>=0.1、誤差RMS<=0.08・最大<=0.2。開発テストでは境界辺そのものの集合も一致確認。集計評価器のboundary_preservedは座標multiset検査であり、任意meshの境界辺対応の証明ではない。

誤差は各三角形重心において、その高さの理想的な連続輪郭loftを2048点でサンプリングし、最近XY距離を計測したもの。単位はfixture座標系（高さ1）。面全体のHausdorff距離、曲率、G1連続性、法線、体積誤差ではない。粗い輪郭の離散化誤差も含む。解析目標は固定した対応であり唯一の正しい美的形状という意味ではない。

自己交差は自作検出器でなくCGAL。解析的目標とBlender標準を併用したが、fixtureと評価実装は同じ研究者であり、完全な第三者検証とは区別する。CGAL例外0。2版一致はこの入力集合の互換性であり、一般のBlender対応宣言ではない。

## 失敗を残す

- index: holdout全6件不合格。5件で交差（43/45/16/37/53ペア）、superellipseは交差0でも形状誤差/品質不合格。
- phase: offset/slender/far_offsetは細長い三角形。平均RMSは最良でも品質基準で落ちる。単一指標の順位では判断できない。
- dp: offsetの最大誤差0.2098、lowpoly RMS0.0849、far_offset RMS0.3036・最大0.6168。**交差0でも意図した形状から逸脱**。辺長目的関数だけでは形状保存に不十分。
- Blender標準: lowpoly RMS0.0849、far_offset RMS0.2005・最大0.5503で不合格。低解像度や大きい横ずれは標準でも未解決。
- 初回Blender実行は組込みCyclesモジュールと研究の`cycles` namespace衝突でimport失敗。生成前にrunnerのfixture読込のみ明示パスへ修正し再実行。凍結モデル・評価器・fixtureは無変更。
- 非平面/交差境界、穴分岐、既存面への法線整合、UV、材質、非常に高密度、手作業時間、実作品は未検証。Blender4.5.15/5.2.1を含む本体の他対象版は未検証。

## 次の判断

形状保存制約付きの対応付け・中間輪郭追加を優先。辺長目的の改善だけでなく「目標loftからの逸脱上限」と「三角形品質」の両立を検証する。今回の6holdoutは今後開発回帰として扱い、新しい非平面/凹形状・密度差・第三者公開データを別holdoutにする。既存meshの局所修復と比較し、境界の移動を必要とする方式は別契約に分ける。人間操作記録・模倣学習は将来候補のまま。

## 再現

`research/geometry_lab`で、各出力に未使用名を指定:

```bash
python -m pip install -r requirements-oracle.txt
python -m unittest discover -s tests -v
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python cycles/r4/blender_run.py -- --output runs/new-r4-raw.json
python -m cycles.r4.evaluate --input runs/new-r4-raw.json --output runs/new-r4-eval.json
python -m cycles.r4.python_run --output runs/new-r4-python.json
```

Blender executableを4.3.2/4.4.3へ置き換えて別々に実行。Python集計はBlenderなし、CGALを隔離環境で使用。`results/blender432.json`と`blender443.json`には全成功/失敗・反復時間・品質・実行source hashを保存。生の人工頂点/面はignored runsのみ。専用CIはPython3.12・CGALの再検証を追加し、Blender2版はローカル実測と明確に区別する。R1〜R3の実装・結果は無変更。
