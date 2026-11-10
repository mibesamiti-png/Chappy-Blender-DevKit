# CBDK 通常開発R14 — ABCD正式割当（R13マイルストーン同期後に有効）

> 本ファイルはA司令塔の正式割当文書。ただし **本ファイルを含むAのマイルストーン同期PRがCI greenでv0.18開発ブランチへmergeされ、さらに統合SHAの独立7系統CIが成功した後にだけ** R14新ブランチを作る。未成立中は読み取り専用の設計のみ。これはv0.19への移行許可ではない。

## 検証済みR13基点

- B #100 `f3e83449bb41512771a25010a02002bddf37ec20`、C #102 `233738e8294fd7658d378611ba55ab73f5c923f5`、D #103 `fa97caaee002b9c9959f5eb8cc75fbb93a9e6ec9`。各担当5系統CI green。
- A一度だけ統合 #104 候補 `7d7933de1d5f59a074bd227457c98358c6e1c35b` で5CI green、dev squash `0a306a85d6f84ef434eb6b54f12cb4ce93251a6c` で別7CI green。結合9ファイル・専門PRを個別マージしていない。
- 正式リリースv0.17.0・main・44要件の状態は維持。実GLB/Windows GUI/第三者addon/権利/正式Extension公開は未検証。

## R14割当

| 担当 | 予定ブランチ | 許可された変更領域 | 重要な受入条件 |
| --- | --- | --- | --- |
| **B P1** | `work/v018-glb-analysis-r14` | `cbdk/glb_*`、GLB専用tests/docs | GLB比較の複数根拠（差分・IoU・boundary・表面距離・静的prop候補）を匿名・review-onlyのtriage結果に整理。合成4条件（変位・開口・欠損・同一）で既存reportとの整合、未知領域の明示、誤った自動適用拒否。既存R2/R3/R8/R13不変、上限保持。新CLI/共通UIが要るならAへ依頼。 |
| **C P1** | `work/v018-ui-builder-r14` | `templates/modular_preview/`、UI専用tests/docs | R13の元module参照回復を複数（2〜3）失敗世代に拡張し、登録class/Scene ledgerのidentity、foreign所有権、explicit cleanup成功/拒否/unknownを正確に判別。Blender 4.4.3/4.5.15/5.2.1 native CI、5機能/6レシピ・過去markers不変。新importの空ledgerを復旧成功と誤認しない。 |
| **D P1** | `work/v018-extension-quality-r14` | `cbdk/extension_*`、Extensions専用tests/docs | R13の固定basis/読取時変更/Windows aliasesを引き継ぎ、precheck→open間のreparse/junction入替などTOCTOU負例と安全上限を測定。権限/ライセンス/真正性未確認を安定した値なし理由コードで報告する方向を検討。POSIX/Windowsハンドル保証の証拠がない限り任意ソースの製品用自動読取には昇格しない。7正常ZIP・合成公式validator・16MiB/2MiB/64件維持。 |

## ABCDの作業ゲート

1. 開始直前に最新 `feature/v0.18-shape-diagnostics` のSHAと `docs/project/STATE.json`、`docs/PARALLEL_DEVELOPMENT.md`、`docs/PROJECT_HANDOFF.md`、各PR/CIを再読する。本ファイルを含む同期PRの最新dev統合+独立7CIを確認する。
2. B/C/Dは最新dev SHAから担当専用ブランチを作成し各1ドラフトPR。自分の領域のみ編集、AのSTATE/Handoff/PROGRESS/scripts/CI/Notion/mainには触れない。
3. 実用的な新規機能または明確に再現した安全欠陥への修正を優先。欠陥がなく本体変更の利得が測れないときは保守的tests/docsで止め、品質を理由に無意味な機能を追加しない。
4. 各担当の正確な最終HEADでPython3版/Windows2版/Blender3版/Chromium/Handoff **5ワークフロー**と対象markerを実測。CIレポート・最終HEAD・未検証項目をAへ提出する。
5. Aが最新devから統合候補を作成して9+ファイルの所有境界/既存API/依存を確認。結合HEADの5CI→dev一度だけ統合→統合SHAの独立7CI→STATE/Handoff/PROGRESS/キュー同期とNotion節目ミラーの順。自動起動CIの確認前にdispatchしない。

## 不変の安全境界

私有GLB・元addon・派生形状を公開GitHub/CI/Notionへアップロードしない。未承認コードを実行・採用・自動修正しない。source hashは作者同意、ライセンス、正式公開の許可ではない。Windows GUI/Ctrl+Z・実ユーザーモデル・第三者との共存は別検証。GitHubからBlenderへの直接インストール保留。main/正式v0.17.0/Extensions配布・Pages/v0.19を勝手に変えない。
