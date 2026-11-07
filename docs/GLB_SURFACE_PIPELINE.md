# GLB-019: ローカル2GLBの3D表面比較を既存CBDKへつなぐ（v0.18 開発中）

## 使い方

参考モデルと、アドオンから生成したモデルを**ローカル**に用意した場合、次のコマンドを明示的に実行する（Blenderの実行ファイルは自分の環境のパスに置き換える）。

```powershell
python -m cbdk glb-surface-review reference.glb generated.glb --blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --output reports/latest/glb_surface_review.json
```

従来の7方向プレビュー・外寸・シルエット・診断・修正候補レポートとまとめて使う場合は`glb-regression`に`--surface-review`を追加する。

```powershell
python -m cbdk glb-regression reference.glb generated.glb --blender "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --output reports/latest/glb_regression --surface-review
```

すると従来の`comparison.json`・`diagnosis.json`・`repair_plan.json`に加え、`surface_review.json`を別ファイルで作成する。**従来の`passed`はメタデータの許容差チェックで、3D形状の同一性を保証しない**。表面の比較結果は`surface_status` / `surface_observation`を別表示し、自動修正を開始しない。

## 実装の範囲

1. 標準ライブラリ製の`glb_inspector`でローカルファイル2つのコンテナ構造を事前確認。外部URIの参照禁止、入力24MiB/個以下、概算頂点参照10万以下に限定。
2. 利用者指定のBlender実行ファイルを`--background --factory-startup --disable-autoexec`で起動し、CBDKに付属する固定スクリプト`scripts/blender_glb_surface_review.py`だけを実行。**ユーザーのアドオンPythonは実行しない**。
3. 各GLBから全メッシュの三角形を**共通のワールド座標系**へ変換して取得。両方とも512面以内なら既存の表面距離（固定24サンプル/面・BVH）と特徴優先型多解像度（粗8点→選んだ面48点）を実行。**オブジェクトごとの対応づけはまだ行わない**。
4. 三角形が512を超えた場合は無理に間引かず`status: skipped`/`reason: triangle_limit`と記録する。スキップを一致・合格・解析完了として扱わない。
5. `status: review_only`の集計JSONへ、対象三角面数・スコア・選択特徴の集計・安全フラグのみ保存。三角頂点のXYZ配列・元GLBの絶対パス・テクスチャは書き込まない。

`surface_observation: sampled_difference_detected`は**調べたサンプル点で違いを観測した**ことを示す。`no_difference_observed_at_samples`は**調べた点では違いを見つけられなかった**だけで、同じ立体だと証明したわけではない。

## 安全上の境界と今後の問題

このコマンドは**明示してローカル実行したときにだけ**2つのGLBをBlenderで開く。外部URIなどは事前拒否するが、未知のファイルをBlenderにインポートするリスクを完全にゼロにはできない。非公開GLBを公開GitHubやCIへアップロードしない。公開CIにはリポジトリ内で生成した自作の合成GLBだけを入力する。

現在の表面比較は512三角形/GLBまでという研究用制限があり、大きなモデル・細かい内部空洞・トポロジ違反・ボールジョイントの正確な嵌合などを十分に判定できない。参照GLBと候補GLBを比較するときは配置・スケール・軸が揃っていることが必要。異なるメッシュ名や部品対応の推測は含まない。

今後は、安全な大規模モデルの分割評価、GLBのオブジェクトごとの対応、差分箇所の可視化、承認済み設定の改善実験へ段階的に進める。

## CIでの実測

Python回帰テストで外部URI・サイズ・頂点参照・失敗ランナー・偽報告・最大面数超過の扱いを確認する。Blender 4.4.3/4.5.15/5.2.1では、CBDKが生成した**同じ外寸の穴あり/穴なしGLB**と**同じ形状の別三角分割GLB**を、この新CLIに入力して確認する。既存`glb-regression --surface-review`の実行にもopt-in段階を加え、従来レポートが残ることを確かめる。

検証成功が実際に観測されるまではGLB-019は`partial/not_tested`の扱いとする。

## 2026-11-07: Blenderレポートの入力検証強化

Blenderから返る集計レポートも無条件には信頼せず、面数が非負整数であること、主要な表面距離が非負かつ有限の数値であること、測定・スキップの状態と記録が矛盾しないことを検査する。NaN、Infinity、負の距離、真偽値の面数、スキップなのに測定値が入っているレポートは拒否する。対応する回帰テストを追加した。

この変更のコードコミットは `6ad969d6`、テストコミットは `abfccff5`。CIは当該コードHEADの実測結果を確認するまで未検証として扱い、既存の正式リリース `v0.17.0` の検証記録は変えない。検査対象はメトリクスと状態の一貫性であり、任意のGLBの幾何学的な同一性の保証にはならない。

## 2026-11-07: 観測結果と表面距離の矛盾を拒否

表面比較ランナーのレポート検証を追加。`sampled_difference_detected` と、固定/適応型サンプルの最大距離（しきい値 `1e-6`）が整合することを要求し、ゼロ距離を差分ありとする結果や、明らかな差分を差分なしとする結果を拒否する。また、`review_only` の実測三角形数が各GLBで512を超えた場合は、制限超過を誤って解析完了と扱わない。これらはレポートの整合性検証であって、表面の完全一致の証明ではない。回帰テストを追加し、最新コードのCI結果を確認するまでは新規変更を未検証とする。
