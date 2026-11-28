# CBDK v0.18 — Blender設定値の実測GLB実験（GLB-012）

## 実験の目的

GLB-007〜011の静的解析は「設定宣言→参照→形状生成APIに流れる構文」を推測できるが、実際に3D形状が変化したことの証明ではない。GLB-012では**CBDK自身が用意した合成Blenderアドオン**だけをBlenderで起動し、設定値の変更前後で生成GLBが変わるかを測定する。

ユーザーの自作アドオンや私有GLBは実行・変更・GitHubへ送信しない。

## 実行と成果物

ソース:
- `fixtures/cbdk_parameter_experiment.py`: CBDK作成のPropertyGroupと生成Operatorを登録・解除。球の半径`sphere_radius`と立方体Bevel幅`bevel_width`を持つ。
- `scripts/blender_parameter_experiment_smoke.py`: 3つの設定値でOperatorを呼び出し、メッシュを生成、GLBを書き出し、Blenderで読み戻して頂点位置を測定する。
- `tests/test_glb_parameter_experiment.py`: 設定宣言と`bpy.ops.mesh`/モディファイア風代入への静的経路を純PythonのASTで6件チェック。

ローカルで信頼済みのBlenderを指定する場合:

```bash
blender --background --factory-startup --python-exit-code 7 \
  --python scripts/blender_parameter_experiment_smoke.py \
  -- reports/ci/parameter_experiment
```

生成される `reports/ci/parameter_experiment/` の中身:
- `baseline.glb`：球半径0.75、Bevel幅0.08
- `sphere_radius_changed.glb`：球半径1.15、Bevel幅0.08
- `bevel_width_changed.glb`：球半径0.75、Bevel幅0.35
- `parameter_experiment.json`：各部品の頂点座標SHA-256、頂点/ポリゴン数、ワールド寸法、GLBの再読み込み前後の測定と独立コントロール

ベースラインと各変更版について、半径変更時だけ球が変わること、Bevel幅変更時だけ立方体が変わること、Bevelにより外寸が変わらないことを確認する。GLBの再インポート前後でワールド寸法が一致することも確認する。

Blender 4.5.15のCIでは追加で`glb-regression`を使い、ベースラインと半径変更版について**実GLBの寸法差→診断→確認プラン**まで実行する。差分を検出してexit 1を返すのはこのケースでは期待される正常結果。

## 実測した対象と限界

GitHub Actionsで次を実際に成功確認した（実装コミット `5923adda697841695cd28bc391e30e7761b06767`）。

- Python 3.11 / 3.12 / 3.13：run 42217215361
- Windows PowerShell 3.11 / 3.13：run 42217215479
- Blender 4.4.3 / 4.5.15 / 5.2.1：run 42217215423
- Windowsキット：run 42217215296
- GitHub引き継ぎ：run 42217215376

**証明できたこと:** この合成アドオンで、プロパティ設定を一つずつ変えると対応するメッシュ形状が変更され、GLBで書き出し/再読み込み後も違いを測定できた。

**まだ証明できないこと:** 他の自作アドオンに同じ静的経路があれば必ず形状が変わること、Boolean穴などの細部が32×32のシルエットだけで判定できること、参考GLBの形状を完全自動再現できること。実ユーザーアドオンの実行は安全上、自動化しない。

PR #25はドラフト。正式な`last_verified`リリースはv0.17.0のままとする。
