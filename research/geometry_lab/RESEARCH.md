# 曲面接合・自己交差：研究ノート

調査日: 2026-11-10 JST。独自実装と標準Blender API呼出しのみ。論文/OSSコードの転載なし。

## 調査と比較

| 手法 | 長所 / 前提 | 弱点・研究での扱い | 出典 |
|---|---|---|---|
| 三角形交差 + 空間枝刈り | 面単位の局所診断。AABBは候補を保守的に減らせる | 浮動小数点、共面・隣接判定に注意。本試作はSATでありMöllerのコード再実装ではない | [Möller 1997, A Fast Triangle–Triangle Intersection Test](https://web.stanford.edu/class/cs277/resources/papers/Moller1997b.pdf) |
| Exact Boolean / corefinement | 交線で分割し体積を合成。既存形状を比較的保つ | 微小三角形、接線接触、入力不正、丸め誤差。接合しても滑らかなG1/G2面にはならない | [Blender Boolean](https://docs.blender.org/manual/en/4.4/modeling/modifiers/generate/booleans.html)、[CGAL 6.1.2 PMP](https://doc.cgal.org/6.1.2/Polygon_mesh_processing/index.html) |
| Voxel / implicit union | 複雑な重なりを体積として統合。スカルプトに適する | グリッド未満の細部・薄い接続・隙間が失われる。分解能で時間/形状誤差が変わる | [Blender Voxel Remesh](https://docs.blender.org/manual/en/2.90/sculpt_paint/sculpting/tool_settings/remesh.html)、[公式2.81開発ノート](https://developer.blender.org/docs/release_notes/2.81/sculpt/) |
| Hermite Dual Contouring | 位置と法線を用い特徴を保つ暗黙面抽出の候補 | グリッド、符号、QEFとトポロジー処理が必要。本試作のVoxel Remeshと同一アルゴリズムとは扱わない | [Ju et al. 2002, Dual Contouring of Hermite Data](https://people.eecs.berkeley.edu/~jrs/meshpapers/JuLosassoSchaeferWarren.pdf) |
| IPC + CCD | 交差のない初期状態から接触制約と連続衝突判定で変形を進める | 非線形最適化・距離微分・CCDが必要。既に交差したモデルの万能修復ではない。本研究は導入前調査 | [Li et al. 2020, Incremental Potential Contact](https://ipc-sim.github.io/)、[ipc-toolkit](https://github.com/ipc-sim/ipc-toolkit) |
| 境界ループ接続 + fairing / retopology | 対応する開境界から制御しやすい接合。面流れを設計できる | 境界対応、異なる頂点数、曲率連続、局所交差を別途解く必要 | [CGAL fairing](https://doc.cgal.org/6.1.2/Polygon_mesh_processing/index.html)、[Blender Studio Modeling](https://studio.blender.org/tools/artist-guide/asset-creation/modeling)、[制作記事: Retopology Modifiers – Pinning & Relaxing](https://studio.blender.org/blog/retopology-modifiers-pinning-relaxing/) |

制作記事からの設計上の示唆: Boolean/Remeshの形状合成と、アニメーション・テクスチャ向けの面流れの良さは別の評価軸とする。人間の境界ループ配置を将来の学習対象にする余地がある。

## OSS導入候補とライセンス境界

- [CGAL self_intersections.h](https://github.com/CGAL/cgal/blob/main/Polygon_mesh_processing/include/CGAL/Polygon_mesh_processing/self_intersections.h): 自己交差の独立参照判定候補。PMPのGPL/商用条件を採用前に確認。exact predicatesだけでなくconstructionの精度も必要。
- [libigl Boolean tutorial](https://libigl.github.io/tutorial/#boolean-operations-on-meshes): Boolean・self-intersection解消とCSGの比較候補。コアMPL-2.0とCGAL/copyleft依存を区別。今回はリンクのみ。
- [IPC toolkit](https://github.com/ipc-sim/ipc-toolkit): MITの接触/CCD関数群。実際の導入時は固定コミット・依存のライセンス・コンパイラを記録する。今回ビルド/実行していない。
- Blender標準Boolean/Remeshをインストール済みBlender 4.3.2から利用。Blenderのソースを同梱していない。CBDK側の権利状態も変更しない。
- 将来の依存採用では特定版のLICENSE/SPDXと依存関係を再確認する。本ノートは法的な採用許可を与えない。

閲覧範囲: IPCプロジェクト本文、CGAL 6.1.2マニュアル、libiglチュートリアル、IPC GitHubを閲覧。Möller/Ju論文は検索索引の題名・要旨と公開PDFの所在確認が中心で、全導出の検証ではない。Blender Manual/Studioは検索索引で確認できたが本文取得はweb側402・実行環境403のため、読めた要約を超える詳細な記述を根拠にしていない。APIは実際のBlender試験で確認した。

## 採用した実験

1. SAT narrow phaseを共通にして全ペアとAABB sweepを比較する。既知正解の6条件×3スケール×2方式とseed固定soup。共通SATの一致だけでは数学的正しさを証明しないので、解析的正解を別に持つ。
2. 非隣接triangle soupの線形移動をswept AABBでガード。終点だけの検査が通る突き抜け例を用いる。保守的な偽拒否を許容。IPCや完全CCDではない。
3. 閉じたUV球2個のExact BooleanとVoxel Remeshを比較。体積真値は解析球のunionで、入力多面体自体の離散化誤差も含む。重なり・薄い首・接線接触・隙間を分ける。対称性を崩した追加実験も独立保存。

## 品質と成功の定義

- 検出: 正解ラベルとの一致、FP/FN、ペア数、検査数、時間。境界接触は非隣接面ではhit。
- 接合: 境界辺0、3面以上共有辺0、期待する連結成分数、解析球union体積との相対誤差8%未満、検出完了かつhit候補0。接線接触は常にambiguous。
- 三角形品質: `4√3 A / Σ辺長²`、正三角形1、退化に近いほど0。最小値を報告するが今回成功閾値には入れない。
- 時間: 1回warmup後3回の実測と中央値。接合APIには一時mesh作成・評価・cleanupを含み、検出時間は別。共有クラウドCPU・他テストとの競合があり、速度保証や厳密な専用機比較ではない。
- 頂点配列のコピー、入力不変、Blender一時データの解放、選択/active object保全も検査。

## 未解決と次の候補

P0: 隣接面のinset近似をexact intersection/shared-simplex分類に置き換え、CGAL等との独立比較で微小接触の偽陽性・偽陰性を分類する。今の`certified=false`を維持。

P0: 対称Boolean出力の退化面について、面を黙って削除せず、交線と面の由来を保存して原因を分離する。Blender 4.4.3/4.5.15/5.2.1で同一fixtureを検証する。

P1: IPC-toolkit/Tight InclusionのCCDを導入し、共有頂点のある変形と辺–辺/頂点–面接触に拡張。三角形の途中の退化・反転も別に検査する。

P1: 境界ループ対応 + Hermite bridge + fairingと、SDF smooth unionを追加し、法線角・曲率・局所表面距離・薄肉保持を測る。Boolean接合だけでは曲率連続性を達成しない。

P2: 接合後のretopology、材料/UV/属性保全、native heapと大規模BVHの評価。開境界・非多様体・大きな絶対座標は追加コーパスが必要。

## 模倣学習との将来インターフェース（今回未実装）

将来はローカルopt-in記録器が、操作ID、Blender版、モード、選択条件、パラメータ、前後の形状ハッシュ、成功/取消、時間、幾何品質を渡す。`Mesh → proposal → guarded validation → review`の層で本ライブラリを評価器として使う。操作提案を自動実行・学習許可と同一視しない。生の.blend/スクリーンショット/頂点/ユーザー識別子は公開しない。公開学習用は人工fixtureから別途生成する。記録器・学習器・収集・モデル送信は今回行っていない。
