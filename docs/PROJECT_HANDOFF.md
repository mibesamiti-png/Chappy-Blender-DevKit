# CBDK｜新しいチャットの開発引き継ぎ

このファイルが新しい会話の入口。GitHub main と最新の実際のCIを優先する。古いREADMEやチャットの印象で開発状況を判断しない。

## 新しいチャットで最初にすること

1. リポジトリ mibesamiti-png/Chappy-Blender-DevKit の main を確認する。
2. このファイル、docs/project/STATE.json、docs/PROJECT_SPEC.md、AGENTS.md を読む。
3. pyproject.tomlのバージョンと、部品/機能カタログを照合する。
4. 前回のCI成功が現行コミットのものか確認する。未実施テストを成功とみなさない。
5. 次の優先タスクをブランチで実装し、テストと状態を更新してPRを作る。

## 最新の開発状況

- 現在のバージョン: `0.17.0`
- 開発段階: public_repository_release_candidate
- 最新の節目: PR #18（v0.16監査）、#20（Undo/Redo・登録ワークフロー）、#21（GLB Visual Inspector）を順番にmainへ統合。v0.17.0正式化ブランチで最終CI待ち
- 次の予定リリース: `0.18.0`
- 自作部品: 7件 (BLCTX-001, BLCTX-002, BLGEO-001, BLMOD-001, BME-001, BME-002, BME-003)
- 組み込み機能: 5件 (edit_selection, mesh_bounds, modifier_summary, object_selection, vertex_nudge)
- 部品の正式採用と再配布ライセンス確認は未完了。個人用プレビューのみ。

## 仕様・実装・未実装の一覧

| 要件 | 機能 | 状態 | 検証種別 | 備考 |
|---|---|---|---|---|
| `SRC-001` | PythonアドオンのASTスキャン・関数台帳 | 実装済 | Pythonテスト | 元コードを実行せず解析 |
| `DUP-001` | AST・構造重複候補と検索 | 実装済 | Pythonテスト | 同等性は保証しない |
| `REV-001` | 候補の手動選択・来歴記録 | 実装済 | Pythonテスト | 選択は採用/ライセンス承認ではない |
| `ISO-001` | ソース内/複数ファイルの依存静的検査 | 一部実装 | Pythonテスト | 条件に合う安全側パターンのみ |
| `AUD-001` | Blender API静的監査・契約 | 実装済 | Pythonテスト | 実機検査とは分離 |
| `PART-001` | 再利用自作部品の台帳と実機スモーク | 実装済 | Blender CI | 7部品。実行証拠はPR #16のCI。台帳は承認を与えない |
| `PLAN-001` | 機能依存閉包・Blender互換性チェック | 実装済 | Pythonテスト | 5機能。許可リストにないコードは実行しない |
| `BUILD-001` | レシピからのBlenderアドオン生成 | 一部実装 | Blender CI | レガシー形式・固定の自作プレビューのみ |
| `EDIT-001` | Edit Mode選択頂点の安全な移動 | 実装済 | Blender CI | 単一メッシュ/有限オフセット/Blender UNDOフラグ |
| `EDIT-002` | 編集差分の監査とベストエフォート復元 | 一部実装 | Blender CI | 加工前不変スナップショット＋ライブ監査。XYZごとに変化を検証し、ゼロ指定軸・未選択頂点の変更は厳格拒否。異常時復元/再検査。PR #21のBlender 4.4.3/4.5.15/5.2.1 CIで実測成功 |
| `TEST-001` | Python/Windows/Blender 3バージョンCI | 実装済 | Blender CI | リポジトリ公開化後、PR #21でPython 3.11/3.12/3.13、Windows PowerShell 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1が全成功。mainの正式last_verifiedは未更新 |
| `UI-001` | 汎用アドオンUI組み立て | 未実装 | 未検証 | 任意レイアウトの生成は未対応 |
| `EXT-001` | 正式Blender Extensions形式と公開パッケージ | 未実装 | 未検証 | 法的/ライセンス確認を先に行う |
| `INST-001` | GitHubからBlenderへの直接インストール・更新 | 保留 | 未検証 | ユーザー希望で保留。UI確認段階まで実装しない |
| `PERF-001` | 巨大メッシュ向け監査・効率化 | 一部実装 | Blender CI | 20万要素の事前サイズ検査、加工後の座標・選択を2回目の全コピーなしで比較。実機70×70グリッドの測定をCIで実施、上限超は変更前に拒否 |
| `GUI-001` | 実際のGUI Undo・操作感の自動検証 | 未実装 | 未検証 | ヘッドレスではUndoフラグと編集結果まで確認 |
| `UNDO-001` | 背景BlenderでのネイティブUndo/Redo検査 | 一部実装 | Blender CI | PR #21でBlender 4.4.3/4.5.15/5.2.1の背景プローブを実行。背景ではundo.poll不可をunavailableとして正しく記録し、GUIショートカットは対象外 |
| `PLAN-002` | 全レシピと部品依存の一括静的監査 | 一部実装 | Pythonテスト | 6レシピ・5機能・7部品の整合性と3版の静的互換性を照合。PR #21のPython 3.11/3.12/3.13全体テスト成功 |
| `REG-001` | 自作部品・機能の登録計画自動生成 | 一部実装 | Pythonテスト | 未登録ID・依存・ソース衝突を検査して非実行のレビュー計画を生成。コード/台帳の自動追加・承認は行わない。PR #21のPython 3版CIで回帰テスト成功 |
| `REG-002` | 登録計画から未完成テストのひな形を安全に生成 | 一部実装 | Pythonテスト | 現行カタログと登録計画の完全一致を確認し、TODO失敗テストをignored領域に新規生成。Windows短縮パス差も修正し、PR #21のPython/Windows CI成功 |
| `REG-003` | 読み取り専用・メッシュ編集で未完成テストの内容を切替 | 一部実装 | Pythonテスト | --behavior read_only/mesh_editを明示指定。共通項目に不変性・Undo・選択範囲・復元を追加。PR #21のPython 3版CIで回帰テスト成功 |
| `GLB-001` | GLB静的構造解析とBlender多方向プレビュー | 実装済 | Blender CI | schema v2静的解析＋Blender本命7方向PNG＋最大32部品単独サムネイル＋neutral clay/Workbench。PR #21のBlender 4.4.3/4.5.15/5.2.1で合成GLB fixtureの構造JSON・scene metadata・全画像生成が成功 |
| `GLB-002` | BlenderなしGLB Quick Preview fallback | 実装済 | Pythonテスト | 任意依存trimesh+matplotlibで7方向PNGと最大32部品単独サムネイルを生成。外部URIを事前拒否し、50万頂点/25万面の安全上限。ユーザーGLB(7 mesh)で7方向+7部品画像をローカル生成確認。本命のBlender実レンダリングより低精度であることを明示 |

## 既知の問題・制約

| ID | 重要度 | 状態 | 内容と回避策 |
|---|---|---|---|
| `LIM-001` | medium | open | 監査後のトポロジー破損は座標復元だけでは修復不可。回避策: 作業ファイルのバックアップとBlender標準Undoを使い、危険な加工は正式採用しない |
| `LIM-002` | low | open | GUIのCtrl+Zと操作感はヘッドレスCIでは未検証。回避策: UIのある開発段階でWindows上で確認する |
| `LIM-003` | low | open | Blender公式アーカイブ取得で稀にHTTP 403。回避策: ダウンロード失敗とコード失敗を区別し、CIの失敗ジョブのみ再実行する |
| `LIM-004` | medium | open | 自作部品の採用・ライセンス/再配布確認は未完了。回避策: 開発用プレビューのみで、approved=falseを維持する |
| `LIM-005` | low | open | 大規模メッシュは監査20万要素上限を超えると操作しない。回避策: 小さなメッシュに分割するか、必要に応じ監査上限を再設計する。安全を確認せず上限を解除しない |
| `LIM-006` | low | fixed | 非公開時のGitHub Actionsランナー未割当(steps=null)は公開化で解消。回避策: 2026-11-06にリポジトリをpublicへ変更後、同じPRワークフローで実ランナー・steps・logsが生成され全CIが実行可能になった。Issue #19は解決としてclose |
| `LIM-007` | low | fixed | GLB多方向プレビューの実機CI未実行問題は解消。回避策: PR #21のBlender 4.4.3/4.5.15/5.2.1で7方向画像と部品単独画像を含むfixtureテストが成功。実ユーザーGLBのBlenderレンダリングは引き続き必要時に個別確認 |

## 次にやること（優先順）

1. `NEXT-006` **PR #18の公開リポジトリCI再検証とv0.16統合** (done)。完了条件: 公開化後にPython/Windows/Blender/パッケージ全CI成功を確認し、PR #18をmainへ統合済み
2. `NEXT-002` **Blender Undo・Redoの実機検証を拡充** (in_progress)。完了条件: 自動化可能なUndo/Redoの機械的チェックと、GUI操作未検証部分を切り分けて記録する
3. `NEXT-005` **v0.17：ベンチマーク実測を比較して監査の追加最適化・Undo/Redo回帰テストを検討** (todo)。完了条件: 3つのBlender版の監査結果とメモリ測定を比較し、速度/安全性の妥協点と残るGUI検証を記録
4. `NEXT-003` **機能登録と新レシピ構築の自動化を改善** (in_progress)。完了条件: 新規許可部品で台帳・依存・CIの不一致を検出する
5. `NEXT-004` **GitHubからBlenderへ直接インストール・更新** (deferred)。完了条件: ユーザーがUI確認の必要性を示すまで作らない
6. `NEXT-001` **v0.16：大きなメッシュ向け監査負荷軽減と上限時の安全な中断** (done)。完了条件: メモリ上限・タイミング・入力拒否をPython/Blenderの両方で測定し、意図しない編集を発生させない
7. `NEXT-007` **GLB Visual Inspectorの3バージョンBlender CIと実データ精度確認** (in_progress)。完了条件: 合成fixtureの3バージョンBlender CIは完了。実ユーザーGLBでも必要に応じBlender Previewを生成し、Quick Previewとの部品対応と形状を照合する
8. `NEXT-008` **参考GLB→アドオン生成→GLB再出力→形状差分の自動デバッグ** (todo)。完了条件: 参照GLB/画像を入力として生成アドオンをBlender CIで実行し、出力GLBの構造・7方向画像・部品単独画像を期待形状と比較して失敗理由を機械可読に記録する

## 前回、実際に確認されたテスト

- 対象リリース: v0.15.0 / 2026-11-05
- Python: 196件成功; 3.11, 3.12, 3.13 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366371)
- Windows PowerShell: 3.11, 3.13 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366384)
- Blender: 4.4.3, 4.5.15, 5.2.1; 共通部品 7件; 生成レシピ 6構成 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366369)
- Windowsキット生成 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/41954366315)
- 前回の[PR](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/16)
- 注意: CIは環境別・変更コミット別の検証記録。以後の変更やGUIの操作感まで保証しない。

## 継続する設計判断

- `DEC-001` GitHubが開発状況・仕様・検証の引き継ぎ元。チャット履歴に依存しない。新チャットはGitHubの引き継ぎ文書から開始
- `DEC-002` Blender実機CI優先、Windows GUI確認は必要時のみ。ヘッドレスCIを操作感のテストと偽らない
- `DEC-003` 未確認コードや私有元アドオンは自動実行・公開しない。各部品の正式採用、ライセンス、実機検査を分離
- `DEC-004` GitHubから直接インストールする管理機能は当面保留。UI確認が必要になる段階で検討
- `DEC-005` PR更新時の重複・陳腐化したCIを抑制し使用枠を節約。PythonはPRとmain pushに限定。全CIにPR単位concurrencyを適用し、引き継ぎCIはPRで重複unittestを実行しない。品質ゲート自体は維持
- `DEC-006` 編集失敗時のロールバックは非有限座標でも可能な限り復元し、結果を実際に再検証。復元前の接続関係を座標と独立に検証。元の値を書き戻してから座標・選択・接続関係を再検査し、完全に戻らなければ成功扱いしない
- `DEC-007` 背景Blender Undo/Redoの検査不可は成功と区別する。undo.poll/redo.pollが不可ならunavailableと記録。実機CI未実行・GUI Ctrl+Z未検証を明示し、v0.15の最終成功記録は更新しない
- `DEC-008` レシピ追加や部品登録の整合性を別の静的マトリクスで検査。新たなレシピ/機能は明示的な期待構成と全依存ファイルの検査が必要。静的検査をBlender実機やライセンス確認の代用にしない
- `DEC-009` 新規部品登録は提案生成と人手の許可を分離。CLIでレビュー案を出力しても許可リスト・元ソース・部品台帳を変更しない。新部品は正式採用せず、手動レビューとCIが必要
- `DEC-010` テストひな形はレビュー用の未完成コードと明示して非実行・非上書き。生成先はreports/latest/scaffolds内のみ。全TODOはself.failで成功偽装を防止し、tests/や元機能・台帳へ自動登録しない
- `DEC-011` 新機能の動作種別は開発者の明示申告とし自動推測しない。read_onlyとmesh_editの申告は静的メタデータであり実機での安全性証明ではない。既存ドラフトはunspecifiedとして共通5項目を維持し、生成ひな形はすべて失敗TODO
- `DEC-012` GLB形状理解は構造JSONとBlender実レンダリングを根拠にする。画像生成AIによる再構成を元GLBの正確な表示として扱わず、生成画像は説明図・設計案に限定する
- `DEC-013` Blender不能時は任意依存Quick Previewをfallbackとして使う。trimesh+matplotlib画像は実GLB形状から生成するが描画精度はBlenderより低い。外部URIを拒否し、Blender実レンダリングが利用可能ならそちらを優先する
- `DEC-014` 公開リポジトリではGitHub Actionsを実機デバッグ基盤として積極利用する。2026-11-06のpublic化でprivate時のランナー未割当が解消。追跡済み内容は公開情報になるため、ユーザーGLB・私有元アドオン・生成private report・秘密情報は今後もコミットしない
- `DEC-015` 積み上げPRは下位からmainへ順次統合し、正式バージョンは専用release PRのCIで確定する。v0.17では#18→#20→#21を通常mergeで履歴保持。release/v0.17.0でpyprojectと状態台帳を揃え、成功CI観測後にlast_verifiedを更新する

## 更新・プライバシールール

- 元の私有アドオンソース、派生レポート、個人情報、認証情報をGitHubに上げない。
- CIの成功は部品の正式承認・ライセンス許諾・GUIの操作感を証明しない。
- GitHubからBlenderへの直接インストールは保留。ユーザーの意思なく実装しない。
- 各節目でdocs/project/STATE.jsonを更新し、この引き継ぎを再生成する。
- 実行: python scripts/project_handoff.py --write
- 照合: python scripts/project_handoff.py --check

## 詳細と正本

- [開発状態台帳](project/STATE.json)（正本、機能・バグ・タスク・CI）
- [最新の開発仕様](PROJECT_SPEC.md)
- [実装履歴](PROGRESS.md)
- [開発時の安全ルール](../AGENTS.md)

この文書はSTATE.jsonから自動生成。内容の編集はSTATE.json側で行う。
