# GLB-022 第1段階：許可済み合成モデルの生成→比較→採否判定ループ

## 目的

GLB-021で確認した「候補設定名の静的レビュー」と「固定の合成モデル変更履歴」を踏まえ、**実際にBlenderで合成GLBを毎回再生成し、GLB-020比較器を実行して、改善しない試行を棄却し、停止理由を保存する**小さな反復実験を実装する。

**安全境界**：この段階はCBDKがソース管理している`scripts/blender_make_glb_joint_mvp_fixtures.py`だけを実行し、`reference`、`narrow`、`narrow_placebo`、`identical`の4条件に限定する。任意のPythonアドオン、非公開GLB、第三者コードは実行・アップロード・書換しない。一般的な自動最適化・コード修正・実際の設定値推奨は対象外。

## 初期テストケース（固定2試行）

| 順序 | 合成条件 | ソケット開口径 | ボール | 判定条件 |
| --- | --- | ---: | --- | --- |
| 基準 | `narrow` | 0.78 | 元の位置 | 変更前の観測差分 |
| 試行1 | `narrow_placebo` | 0.78 | 移動 | ソケットの差分が減らず、他部品の差分が増えるため**不採用** |
| 試行2 | `identical` | 1.70 | 元の位置 | ソケットの観測差分が減り、他部品の新たな悪化もない場合に**採用** |
| 停止 | 採用済みの合成状態 | — | — | ソケット・他部品とも観測差分0、または試行上限2件 |

これらは**合成専用の固定数値**であり、実際のボールジョイントに推奨する寸法ではない。改善の指標はGLB-020の三角面別・疎サンプリングでの`medium/high`**面の件数**のみで、完全な幾何学的一致・3Dプリント適性・可動クリアランスなどを証明しない。

## 実装

- `scripts/blender_make_glb_joint_mvp_fixtures.py`に単一許可済み合成条件`--single <variant>`の新規GLB出力を追加。**任意のPythonファイル・スクリプトパス・新しいパラメータ値は受け付けない**。既存出力の上書きを拒否し、`--factory-startup --disable-autoexec`でBlenderを起動。
- `scripts/run_glb022_synthetic_iteration.py`が、まず`reference`と`narrow`を実際にBlenderで生成し比較。各試行時も別々にGLBを**再生成**してから`run_glb_diff_visualize`で差分を測定。評価対象は候補と採用済みの匿名部品集計のみ。
- `cbdk/glb_synthetic_iteration.py`が状態遷移を決める。**ソケットの観測異常面数が厳密に減少**し、**他部品の観測異常面数が増えない**ときのみ候補を受け入れる。候補が不適なら既存採用状態を保持し、次試行へ。上限2回、観測差分が0になれば終了する。
- 出力はローカルの新規`reports/ci/glb022_iteration/synthetic_iteration_history.json`と日本語`synthetic_iteration_history.md`。各試行の条件、変更前/後の部品別集計、採否、理由、残存する観測差分、停止理由、合成テスト限定の安全フラグを記録。候補やソースの生ジオメトリ・ユーザーアドオン本文は記録しない。
- 既存ソースのSHA-256を実行前/後で比較し、生成された各合成入力GLBのSHA-256が比較前/後に変わらないことを検証。
- 出力フォルダは**存在しない`reports/ci`直下の新規フォルダ**に限定。元GLBや既存成果物の上書きは拒否。

## 品質と未解決事項

`tests/test_glb_synthetic_iteration.py`は、不採用→採用→停止、誤採用を防ぐ負例、偽造した安全フラグや試験名・件数の拒否、出力の非上書きをテストする。

Blender 4.4.3/4.5.15/5.2.1の実CIでは、固定合成GLBを**試行ごとに作成**し、その都度GLB-020比較器を起動する。これは**キャッシュ済みレポートを単に再集計するGLB-021履歴とは別**の工程である。成功の証拠はテスト対象コードSHAとGitHub Actions runを確認してから追記する。

**この第1段階の未保証事項**：任意のユーザーアドオンの生成/実行/設定変更、動的なパラメータ探索、メッシュ全領域の差分、内部空洞の完全一致、候補が本当に問題を修正する因果、最適な値の発見、物理的ジョイントの安全性。正式リリースはv0.17.0のまま、v0.18のPR #25はドラフトを維持。

## 第1段階のCI確認結果（2026-11-07）

テスト対象コード SHA `9f1bb66e826d6568e923eb3d21c4d28692f74d5d`：[Python 42302517951](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517951)・[Windows 42302518051](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302518051)・[Blender 4.4.3/4.5.15/5.2.1 42302517870](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517870)・[Windows Kit 42302517757](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517757)・[引き継ぎ 42302517807](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517807)・[Chromium 42302517853](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42302517853) **全6系統success**。

CBDK自作のソケットとボール/軸から、基準`narrow`のGLBを実生成し、`narrow_placebo`（無関係なボール移動）と`identical`（既知の正常ソケットへ復帰）を**その都度Blenderで新規書き出し→GLB-020で比較**した。無関係な変更は採用されず、正常復帰だけ採用、観測上の対象・他部品の異常面数0で停止。各試行・採否・停止理由をローカル`synthetic_iteration_history.json`と`.md`に記録。比較用の生成済み合成GLBとソース管理の合成ジェネレーターのSHA-256が変わっていないことをコードで検証。

`tests/test_glb_synthetic_iteration.py`は不正レポート、故意の誤採用、偽の因果宣言、未許可の試験ID、既存ファイルの上書きを拒否することを検証した。**注意**：GLB-022のこの実装は固定2試行の合成用MVPであり、ユーザーアドオン一般でのパラメータ最適化やコード変更、連続探索はまだ実装していない。GLB-022全体の状態は`partial`とする。
