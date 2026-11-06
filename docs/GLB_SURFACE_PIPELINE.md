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
