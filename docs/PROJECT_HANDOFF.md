# CBDK｜新しいチャットの開発引き継ぎ

このファイルが新しいチャットの入口。GitHubの最新mainと実際のCIを優先し、古いチャットや初期READMEの将来予定を現在の状態と混同しない。

## 新チャットで最初に行うこと

1. `mibesamiti-png/Chappy-Blender-DevKit` の `main` を確認する。
2. この文書、`docs/project/STATE.json`、`docs/PROJECT_SPEC.md`、`AGENTS.md` を読む。
3. `pyproject.toml` と部品・機能カタログ、実際のGitHub Actionsを照合する。
4. 優先タスクを新ブランチで開発し、テスト・状態台帳・引き継ぎを更新してPRを作る。

## 現在の開発状況

- バージョン: **v0.15.0**（private_development_preview）
- 最新の節目: Edit Modeでのメッシュ移動に差分監査・異常検出・復元を導入
- 次の予定: **v0.16.0**
- 自作部品: **7件**（BLCTX-001, BLCTX-002, BLGEO-001, BLMOD-001, BME-001, BME-002, BME-003）
- 組み込み可能な機能: **5件**（edit_selection, mesh_bounds, modifier_summary, object_selection, vertex_nudge）
- 正式採用・ライセンス承認は未完了。個人開発用プレビューのみ。

## 仕様・実装状態・未実装項目

| ID | 機能 | 状態 | 備考 |
|---|---|---|---|
| `SRC-001` | PythonアドオンのASTスキャン・関数台帳 | 実装済 | 元コードを実行せず解析 |
| `DUP-001` | AST・構造重複候補と検索 | 実装済 | 同等性は保証しない |
| `REV-001` | 候補の手動選択・来歴記録 | 実装済 | 選択は採用/ライセンス承認ではない |
| `ISO-001` | ソース内/複数ファイルの依存静的検査 | 一部実装 | 条件に合う安全側パターンのみ |
| `AUD-001` | Blender API静的監査・契約 | 実装済 | 実機検査とは分離 |
| `PART-001` | 再利用自作部品の台帳と実機スモーク | 実装済 | 7部品。実行証拠はPR #16のCI。台帳は承認を与えない |
| `PLAN-001` | 機能依存閉包・Blender互換性チェック | 実装済 | 5機能。許可リストにないコードは実行しない |
| `BUILD-001` | レシピからのBlenderアドオン生成 | 一部実装 | レガシー形式・固定の自作プレビューのみ |
| `EDIT-001` | Edit Mode選択頂点の安全な移動 | 実装済 | 単一メッシュ/有限オフセット/Blender UNDOフラグ |
| `EDIT-002` | 編集差分の監査とベストエフォート復元 | 一部実装 | 座標/選択/接続関係の検査、完全なトランザクションではない |
| `TEST-001` | Python/Windows/Blender 3バージョンCI | 実装済 | 4.4.3、4.5.15、5.2.1で最新の確認済み |
| `UI-001` | 汎用アドオンUI組み立て | 未実装 | 任意レイアウトの生成は未対応 |
| `EXT-001` | 正式Blender Extensions形式と公開パッケージ | 未実装 | 法的/ライセンス確認を先に行う |
| `INST-001` | GitHubからBlenderへの直接インストール・更新 | 保留 | ユーザー希望で保留。UI確認段階まで実装しない |
| `PERF-001` | 巨大メッシュ向け監査・効率化 | 未実装 | 監査は現在20万要素で上限制御 |
| `GUI-001` | 実際のGUI Undo・操作感の自動検証 | 未実装 | ヘッドレスではUndoフラグと編集結果まで確認 |

## 既知の問題と制約

| ID | 状態 | 問題と回避策 |
|---|---|---|
| `LIM-001` | open | 監査後のトポロジー破損は座標復元だけでは修復不可。作業ファイルのバックアップとBlender標準Undoを使い、危険な加工は正式採用しない |
| `LIM-002` | open | GUIのCtrl+Zと操作感はヘッドレスCIでは未検証。UIのある開発段階でWindows上で確認する |
| `LIM-003` | open | Blender公式アーカイブ取得で稀にHTTP 403。ダウンロード失敗とコード失敗を区別し、CIの失敗ジョブのみ再実行する |
| `LIM-004` | open | 自作部品の採用・ライセンス/再配布確認は未完了。開発用プレビューのみで、approved=falseを維持する |

## 次にやること

1. **v0.16：大きなメッシュ向け監査負荷軽減と上限時の安全な中断** （NEXT-001, todo）。完了条件: メモリ上限・タイミング・入力拒否をPython/Blenderの両方で測定し、意図しない編集を発生させない
2. **Blender Undo・Redoの実機検証を拡充** （NEXT-002, todo）。完了条件: 自動化可能なUndo/Redoの機械的チェックと、GUI操作未検証部分を切り分けて記録する
3. **機能登録と新レシピ構築の自動化を改善** （NEXT-003, todo）。完了条件: 新規許可部品で台帳・依存・CIの不一致を検出する
4. **GitHubからBlenderへ直接インストール・更新** （NEXT-004, deferred）。完了条件: ユーザーがUI確認の必要性を示すまで作らない

## 最後に確認したテスト

- Python **196件成功** / 3.11, 3.12, 3.13: [CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366371)
- Windows PowerShell / 3.11, 3.13: [CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366384)
- Blender / 4.4.3, 4.5.15, 5.2.1、部品7件、レシピ6構成: [CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366369)
- 開発用Windows ZIP: [CI](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366315)
- [検証したPR](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/16)
- 検証対象の版: v0.15.0。後から変更したコードやGUIでの操作感を保証するものではない。

## 継続すべき判断

- `DEC-001` GitHubが開発状況・仕様・検証の引き継ぎ元：チャット履歴に依存しない。新チャットはGitHubの引き継ぎ文書から開始
- `DEC-002` Blender実機CI優先、Windows GUI確認は必要時のみ：ヘッドレスCIを操作感のテストと偽らない
- `DEC-003` 未確認コードや私有元アドオンは自動実行・公開しない：各部品の正式採用、ライセンス、実機検査を分離
- `DEC-004` GitHubから直接インストールする管理機能は当面保留：UI確認が必要になる段階で検討

## 自動更新と元データ

- 正本は [STATE.json](project/STATE.json)。変更節目ごとに仕様・機能進捗・問題・次の作業・CI結果を更新する。
- `python scripts/project_handoff.py --write` で引き継ぎを再生成し、`--check` で照合する。
- main更新時はGitHub Actionsが再生成し、成功したPythonテストの観測結果を `docs/project/LAST_CI.json` に保存する。
- 元の私有アドオン、個人データ、秘密情報、未承認部品は公開しない。
- GitHubからBlenderへの直接インストールはユーザー希望により保留。

詳細: [現行仕様書](PROJECT_SPEC.md) / [過去履歴](PROGRESS.md) / [開発ルール](../AGENTS.md)
