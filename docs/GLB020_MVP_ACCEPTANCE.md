# GLB-020 MVP 総合受け入れテスト・スコープ凍結

開発ブランチ: \`feature/v0.18-shape-diagnostics\` / ドラフトPR #25。
正式リリースは \`v0.17.0\` のまま。これは \`GLB-020\` **レビュー用MVPの品質ゲート**であり、完全な幾何検査機能の完成宣言ではない。

## 目的

色分け・匿名部品別レビュー・同期視点・表面距離・境界線を統合し、**ユーザーの実制作に近い形状変更を安全に見分けられるか**を確認する。新しい解析アルゴリズムを積み増す工程ではない。

## テストデータ

\`scripts/blender_make_glb_joint_mvp_fixtures.py\` がCBDK自身で生成する小さな3部品モデルのみ使用する。

- **ソケット**：12分割の中空円筒リング。上端・下端のリップ、内壁、外壁から構成。
- **ボール**：8三角形の低ポリゴン球。軸とは別オブジェクト。
- **軸**：上下端面を閉じた12分割円筒。正常ケースではすべての部品が観測上の開放境界なし。

モデルは実製品の製造精度や物理的な可動性を再現するものではない。ファイルはCI内で生成し、**私有の実GLB/アドオンは一切投入しない**。

## MVP合格条件

| テスト | 期待する観測 | 合否の確認点 |
| --- | --- | --- |
| 正常・同一形状 | 全三角面の誤差色が\`low\` | 無変更で\`medium/high\`の誤検出がない |
| ソケット開口を狭める | ソケット部品に\`medium/high\`検出 | ボール・軸は不必要に異常扱いしない |
| ボール位置を変更する | ボール部品に\`medium/high\`検出 | ソケット・軸は不必要に異常扱いしない |
| ソケットのリップから面を1組削除 | ソケットの境界エッジが0→4 | 面数が2枚減り、ボール・軸は不必要に異常扱いしない |
| プライバシー・安全 | 集計JSONに元メッシュ名/パス/頂点を含まない | HTML・色付きGLBは派生形状を含むためローカルに限定 |
| 不変性 | 合成入力GLBのSHA-256が検証前後で一致 | コマンド実行がソースを上書きしていない |
| 互換性 | Blender 4.4.3 / 4.5.15 / 5.2.1 | 同じ判定を各バージョンの実GLB書き出し/読み込みで検証 |

合成モデルの比較に使うコマンド：

\`\`\`bash
python -m cbdk glb-diff-visualize inputs/reference.glb inputs/identical.glb --blender "$BLENDER_PATH" --output review_identical
python -m cbdk glb-diff-visualize inputs/reference.glb inputs/narrow.glb --blender "$BLENDER_PATH" --output review_narrow
python -m cbdk glb-diff-visualize inputs/reference.glb inputs/shifted.glb --blender "$BLENDER_PATH" --output review_shifted
python -m cbdk glb-diff-visualize inputs/reference.glb inputs/uncapped.glb --blender "$BLENDER_PATH" --output review_uncapped
python scripts/verify_glb_joint_mvp.py .
\`\`\`

CIでは\`.github/workflows/blender-smoke.yml\`内で実行する。テストに失敗した場合は**成功したと報告せず**、原因を区別して修正し再実行する。

## 不合格になった場合の対応

正常モデルに境界が出た場合、**解析器の誤判定**か**テスト形状自体に本当に境界があるか**を最初に切り分ける。特定の異常部品以外にも色が付く場合は、サンプリングの距離、座標系、GLBのメッシュ順序、他部品との干渉を確認する。

MVPの範囲をすり替えて単に閾値を緩めたり、失敗する正例を削除して「成功」に変えたりしない。

## 合格後の開発スコープ

ここに定めた合成モデルのMVPゲートを満たしたら、**GLB-020の細かな機能追加はいったん凍結し、GLB-021の「改善候補を人がレビューする」機能を次優先**にする。

残る\`GLB-020\`の本格精度向上（複雑な内部空洞、小穴の網羅、T字接続、正確な遮蔽/深度バッファ、512三角形超、任意ユーザーGLB、完全な部品一致）は**後日別タスクとして維持**する。合成CI成功をこれらの達成・実ユーザーファイルの合格と混同しない。

\`GLB-021\` と \`GLB-022\` はこの時点では未実装。設定の原因特定、元アドオンの無断実行/変更、自動パラメータ適用も行わない。
