# 研究サイクルの継続手順

1. 最新の研究branch・PR #114・CIをfetchし、各cycleのSTATUSと実行ソースhashを確認する。
2. 未解決問題を複数列挙し、後続評価への影響・検証可能性・計算コストから1テーマを選ぶ。
3. 変更前に、解析的正解または独立実装、固定fixture、試行数・秒数・メモリの観測範囲、停止条件を記録する。
4. 小さい変更単位で実験し、失敗/例外/timeout/未確定を除去せず記録する。速度測定とmemory測定を分離する。
5. source hash・依存版・Blender版・試行値を保存し、旧結果を上書きしない。異なる版/形状/計測条件の結果を混ぜない。
6. 維持/不採用/次方式へ移る判断と理由を記録し、algorithms.jsonのメタデータを更新する。自動実行/採用フラグは付けない。
7. 研究PRを更新し、最終HEADに対応するCIを確認。通常開発・mainへのマージは行わない。

R1: ルートRESULTS.mdとresults/（親commit159e89f）。
R2: r2/STATUS.json、RESEARCH.md、RESULTS.md。新規アルゴリズムの横展開より評価器の信頼性を優先。

これは再開可能な研究プロトコルであり、チャット終了後の常駐実験・自動学習を起動するものではない。

R3: r3/STATUS.json。R2と同じ厳密判定の高速化、球以外のshape追加、R1全候補の独立再評価。

R4: r4/STATUS.json。境界ループ接続3方式と標準Blenderを比較。標準置換不採用。2版で一致、6未使用ケースの失敗を形状保存研究へ引き継ぐ。

R5: r5/RESEARCH.md、RESULTS.md、STATUS.json。既知R4の10ケースを開発用に移し、新規5ケースのholdoutでradial 4/5・phase 3/5。研究ゲート達成だがBlender GUI標準未比較で本体未承認。以後このholdoutでモデル調整しない。


R6: r6/RESEARCH.md、RESULTS.md、STATUS.json。Blender GUI相当のnative operator cuts=0/3と3補間方式を公式4.4.3で実測・CGAL検証。新規人工holdout5形状でR5 5/5、最良単一native3-cuts 3/5。研究ゲート達成、非平面・実作品・UI未検証。採用はA司令塔審査まで保留。次サイクルを自動的に始めない。

R7: r7/RESEARCH.md、RESULTS.md、STATUS.json。軽度非平面Z境界に対し独立アルゴリズムとBlender4.4.3標準を10人工形状で比較。新規holdout R7 5/6 vs native3 4/6、スリム形状でR7も品質不合格。CGAL交差0、境界保持。実モデル/一般姿勢/UV未検証、正式承認なし。R8自動開始しない。

R8: r8/RESEARCH.md、RESULTS.md、STATUS.json。R7固定内部密度を上下の頂点数に沿って段階変更し、R7既知10件で10/10、fresh人工holdout6件で5/6（R7とBlender3-cut各3/6）。CGAL交差0、入力境界保持。失敗スレンダーケースを隠さず記録。処理時間・形状RMSがやや悪化、製品未承認、R9を自動開始しない。

R9: r9/RESEARCH.md、RESULTS.md、STATUS.json。元の入力境界頂点/面数不変で内部対角線を条件付きで反転。Blender4.4.3・CGAL独立66ケース検証。既知16/16、新holdout5/6（R8 4/6、Blender3cut 2/6）、自己交差0。未知reverse_narrow 0.08078で不合格、R8より処理時間約12.5倍。研究のみ成功、製品未承認、R10自動開始なし。

R10: r10/RESEARCH.md、RESULTS.md、STATUS.json。品質0.1以上のR8はそのまま返し、未満だけR9反転。Blender4.4.3、CGALで30人工形状×4方式=120を独立検証。新規8ケースR10 8/8、R9 8/8、R8 6/8、Blender 4/8。fast6、repair2、平均時間R9の50.2%、CGAL交差0。既知不合格r9_reverse_narrowは未解決。品質/速度の研究は成功、製品は未承認・R11自動開始なし。

R11: r11/RESEARCH.md、RESULTS.md、STATUS.json。Blender4.4.3 Edit Mode BMeshで人工カラー元面へのR10接続を検証。既知UV8+新UV6=14の属性保持監査に合格、悪いUV/材質の対照も14/14検出。接続後全体メッシュのCGAL交差0。元面は完全保持される一方、分割UV島の継ぎ目0.25と最大法線差約56.35°（新規）は残る。実アセット/Undo/任意UVに未対応、本体未承認、R12自動開始なし。

R12: r12/RESEARCH.md、RESULTS.md、STATUS.json。Blender4.4.3で元BMesh UVを境界拘束として読み取り、新面に1面1チャートのUV平行移動量を伝播。新規8/8、既知4/4、24全体メッシュCGAL交差0。元UV保持かつ境界誤差は最大6e-8、ただし内部シーム最大126/304辺・41.4%、最小シーム/UVパッキング/法線/実アセットは未検証。研究のみ成功、本体未統合、R13自動開始なし。
