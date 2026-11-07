# GLB-021 第5段階：合成モデル変更履歴の記録と比較

## 目的と開発範囲

GLB-020の形状差分とGLB-021のAST候補レビューを受けて、CBDK **自作の合成ボールジョイント風モデルだけ**を使い、固定された複数の変更結果を比較する。**一般のアドオンを実行・自動変更したり、最適なパラメータを探す仕組みではない。** GLB-022の反復変更エンジンとは区別する。

今回の純Pythonモジュールは `cbdk/glb_synthetic_trial_history.py`。新しいBlender演算を開発するのではなく、すでに生成した安全な集計 `review.json` を読み込む。

### 固定の試験（変更値は実験専用）

| ID | 自作合成ソケット口直径 | 自作ボールの位置 | 判定対象 |
|---|---:|---|---|
| `narrow` | `0.78` | 元の位置 | 不具合を模した基準 |
| `narrow_placebo` | `0.78` | 移動する | **関係ない変更でも直る**と誤認しない対照 |
| `identical` | `1.70` | 元の位置 | 既知の元設定に戻して再生成した対照 |

`0.78` と `1.70` は**CBDK自作のテストモデルにだけ許可した数値**であり、ユーザー製の実ジョイントに推奨する径ではない。元の設定へ戻す処理も合成形状の独立した再生成であって、外部のアドオンコードを編集するわけではない。

## 出力（ローカル専用）

- `reports/ci/joint_mvp/synthetic_trial_history.json`：合成の匿名部品 `part_001`（ボール）、`part_002`（軸）、`part_003`（ソケット）ごとの黄面数・赤面数・合計・境界辺数、固定試験条件と比較結果。
- `reports/ci/joint_mvp/synthetic_trial_history.md`：**日本語の比較表**。試験条件、ソケット・ボールの観測異常面数、無関係な変更では問題が残ること、実アドオンへの非適用を明記。
- 個別のGLB頂点・ソース名・パス・元アドオンの設定値やPython本文は出力しない。結果をGitHubやNotionへ自動アップロードしない。ユーザーの私有モデルに対する汎用レポート出力APIではない。

生成したファイルの存在と安全性を確認し、すでに同名のファイルがある場合は**上書きを拒否**。未知の試験ID・未許可の数値・偽の因果断定・不整合な件数・危険なサンプリング結果は拒否する。最大512面と64匿名部品の既存GLB-020入力制限も継承する。

## 品質ゲートと成功条件

`tests/test_glb_synthetic_trial_history.py` で次を検証：

- 合成ソケットの不具合時に観測面数が正、`identical`では0、ボールだけの無関係な変更ではソケットの観測差分が解消しない。
- JSONの匿名部品別集計とMarkdown表が同一内容で、新規ローカルファイルにだけ保存される。
- 不正な入力・件数・偽の証明フラグ・勝手な試験名を拒否し、元のGLBや元ソースを実行・改変しない。

Blender CIはバージョン **4.4.3 / 4.5.15 / 5.2.1** ごとに合成GLBを実際に書き出し、`scripts/verify_glb021_synthetic_counterfactual.py`が結果と履歴を検証する。元合成GLBのSHA-256が変わらないことはCIの別工程で確認する。

**確認済みのコードSHA：`ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f`**

- [Python 42299997255](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997255)
- [Windows 42299997246](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997246)
- [Blender 3バージョン 42299997251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997251)
- [Windows Kit 42299997311](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997311)
- [引き継ぎ 42299997254](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997254)
- [Chromium 42299997355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997355)

**全6系統成功**。これは**合成モデルの限定試験**を確認したもので、実ユーザーモデルの内部空洞・精密な幾何全域・本当のコード因果・設定値の最適性は証明していない。

## 次の工程

GLB-021は引き続き一部実装。実アドオンとの因果関係を裏付けるには、人の明示的な確認と、隔離された許可済みの実行テストが別途必要。GLB-022の「生成→比較→改善」を自動反復させる汎用機構は**まだ未実装**。今後は、明示許可されたCBDK自作モデルに限る反復実験を、今回の履歴形式に接続するのが次の候補。

正式版v0.17.0は維持し、v0.18はドラフトPR #25を継続する。
