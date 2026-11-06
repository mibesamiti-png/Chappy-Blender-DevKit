# GLB-021 合成モデルだけの設定変更実験（第4段階・開発中）

対象: [GLB-021](GLB021_VISUAL_PROPERTY_REVIEW.md)、[GLB-020 MVP](GLB020_MVP_ACCEPTANCE.md)。ブランチは `feature/v0.18-shape-diagnostics`、PR #25 はドラフト。**ユーザーアドオン・実GLBの自動実行や編集は一切しない。**

## 仮説と反証例

設定の宣言名をASTで見つけただけでは、実際の形状を変えると証明できない。そこで **CBDKが内部に固定した合成ジェネレーター**でだけ、ある数値を変えると結果が変わることを確認する。

| 条件 | 合成モデルの操作 | 期待する観測 |
|---|---|---|
| 正常（対照） | ソケット開口直径 `1.70` | 参照と同じ形状、黄/赤の観測面なし |
| 不具合を模した状態 | 同じソケット開口直径 `0.78` | ソケット部品に形状差分が観測される |
| 元へ戻す操作 | ソケットを `1.70` に再生成 | 合成ソケットの観測差分が0になる |
| 無関係な操作（反証例） | 開口は `0.78` のまま、ボール位置のみ変更 | ソケットの差分は残り、ボールの差分も増える |

直径は**CBDK合成テストでのみ有効な固定値**であり、ユーザーのボールジョイントに適した設定値ではない。ジェネレーターはこれらの数値だけを受け付け、それ以外のパラメータ・任意のアドオンコードは実行しない。

## 実装と判定方法

- `scripts/blender_make_glb_joint_mvp_fixtures.py` が合成モデル（ソケット・軸・ボール）をGLB出力する。`reference`/`identical` は正常形状、`narrow` はソケット口の縮小、`narrow_placebo` は縮小したソケットのままボールを移動した**無関係な対照**。
- `scripts/verify_glb021_synthetic_counterfactual.py` が実際にGLB-020で生成した集計`review.json`を読み、ソケットの`medium/high`が正常0、縮小時に正、無関係なボール移動後も正であることを検査する。ボールだけの差分は本来ソケットが壊れる原因ではないことを別の対照として確認する。
- 既存GLB-021のレビュー用AST照合は**別プロセス・別種類の根拠**。合成形状が設定値で変化するという確認と、ユーザーの実アドオンのプロパティが本当に形状を制御するという主張を混同しない。
- 実験記録`reports/ci/joint_mvp/synthetic_only_counterfactual_summary.json`は**CBDK自作モデルの集計値のみ**を保持する。ファイル名・未公開ソース・ユーザーGLB・派生3D座標は含めない。入力GLBは既存CIがSHA-256で不変性確認する。
- Blender 4.4.3/4.5.15/5.2.1の各CIで、ソケット改善と無関係操作の両方を検査。**テスト対象SHAと全CIの成否を確認後にのみ成功を報告**する。

## 未解決のこと

これは**合成ジェネレーター内部の限定的な因果実験**であり、実際のユーザー製アドオンの任意プロパティを変更して良くなると断定するものではない。また設定候補の順位、根拠の確信度、機構の物理強度、印刷公差、内部空洞の一致を証明しない。

GLB-021はレビュー用`partial`を維持する。任意の実データ・プライベートコードについては別途ユーザーの許可とローカル検証が必要であり、GLB-022の反復的な自動変更を本実験の成功と取り違えない。

## 合成実験の確認結果（2026-11-07）

テストコードSHA `3b553039968e982e973d10d3427bf0607bbad88d`：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028446)・[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028346)・[Blender 4.4.3/4.5.15/5.2.1](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028811)・[Windows Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028286)・[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028673)・[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42298028338) **全6系統成功**。

Blender3バージョンの合成GLB比較で、ソケット径0.78の差分は検出され、径1.70の参照設定に再生成したモデルは観測差分0。径0.78を維持したままボール位置だけ変更してもソケット差分は残り、ボールの差分も別途観測。入力GLBのSHA-256不変も確認。**ここで検証した因果関係はCBDKが固定値を使って生成する合成モデルのみ**。実際のユーザー製アドオンの設定値や原因を自動判定したわけではない。

## 第5段階：ローカルでの合成変更履歴記録

CBDK自作の合成GLBについて`cbdk/glb_synthetic_trial_history.py`を追加。固定試験`narrow`（狭窄）→`narrow_placebo`（無関係なボール移動）→`identical`（元の合成設定に復帰）を、**匿名部品ごとの観測黄赤面数・境界数**とともにローカルの`synthetic_trial_history.json`・`synthetic_trial_history.md`へ新規保存する。既存ファイルの上書きは拒否。意図しない試験名や嘘の因果保証、矛盾した数値なら出力しない。

テスト対象コード SHA `ece5b0a6c6bc5ec03e1b8f54687bd4bdd4462a4f`：[Python 42299997255](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997255)、[Windows 42299997246](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997246)、[Blender4.4.3/4.5.15/5.2.1 42299997251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997251)、[Windows Kit 42299997311](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997311)、[引き継ぎ 42299997254](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997254)、[Chromium 42299997355](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42299997355) **全6系統成功**。

履歴の「改善」は**測定された面で差分が減った**という意味に限定し、メッシュ全体の正しさ、ユーザーの実際のアドオン設定の因果・適切な径を証明しない。ユーザーの元GLBやアドオンは読み込んだり実行しない。ローカルCIの履歴形式を汎用のGLB-022反復実験エンジンの実装完了と混同しない。詳細：[履歴とプライバシー仕様](GLB021_TRIAL_HISTORY.md)。
