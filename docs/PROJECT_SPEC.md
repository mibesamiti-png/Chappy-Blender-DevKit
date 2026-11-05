# CBDK 開発仕様（現行版）

このファイルは、以前の `docs/SPEC.md` に残っている初期計画を置き換える**現行の設計方針**。機能ごとの実装状態・未実装・制約・次の作業・テストへのリンクは `docs/project/STATE.json` を正本とし、読みやすい要約を `docs/PROJECT_HANDOFF.md` に自動生成する。

## 目的と対象

- 自作Blenderアドオンを**実行せず**にAST解析し、関数・クラス・依存関係・重複候補を整理する。
- 権利と動作を明確にした自作再利用部品に固定IDを割り当てる。
- 検証可能なレシピから**開発用レガシーアドオン**を作成する。現在の自作部品は7個、UI搭載機能は5個。
- Python 3.11〜3.13 / Blender 4.4.3、4.5.15、5.2.1でコードと生成アドオンのCIを実行する。
- チャットの長さ・表示不良・履歴の消失に影響されず、**GitHubの保存情報だけで継続開発**できるようにする。

## データの区分

| ファイル | 目的と変更ルール |
|---|---|
| `docs/project/STATE.json` | **正本**。要件・実装/未実装状態・問題・優先タスク・決定事項・最後の確認済みテストURL |
| `docs/PROJECT_HANDOFF.md` | 上記から自動生成。新チャットが最初に読む |
| `docs/project/LAST_CI.json` | 自動ワークフローがmainのPythonテスト通過時にのみ更新する観測記録。Blender CIの合格を勝手に代弁しない |
| `docs/PROGRESS.md` | バージョン別の時系列・原因分析などの過去履歴。古い内容を上書きしない |
| `catalog/authored_parts.json` | 自作部品のID、ソース、採用/権利確認状態 |
| `catalog/addon_features.json` | 生成レシピから呼び出せる機能と依存関係 |
| `AGENTS.md` | すべてのAI開発作業に適用する安全性と引き継ぎ手順 |

## 実装状態と検証状態

**実装状態**：`implemented`（実装済）、`partial`（一部実装）、`not_implemented`（未実装）、`deferred`（保留）。

**検証種別**：`python`（Python単体）、`blender_ci`（Blenderヘッドレス実機）、`manual_pending`（画面操作の確認待ち）、`not_tested`（未検証）。

この2つは独立。実装済が完全な実機保証・利用許諾・正式採用を意味することはない。CIに実際に対応するコミット、日付、Blenderバージョン、ワークフローURLを記録する。失敗/保留/未実施のテスト結果を成功と記録しない。

## 開発の節目ごとの作業契約

1. 新チャットではまず `docs/PROJECT_HANDOFF.md`、`docs/project/STATE.json`、`AGENTS.md` を読む。
2. 実装に着手する前に現在のブランチ・バージョン・要件ID・未解決の問題を確認する。
3. 機能を増やす/変える場合は対応する要件・検証種別を台帳へ反映し、コードと回帰テストを実装する。
4. 失敗したテストは問題・原因・対応策・実行URLを記録。実行待ちは「未検証」のまま扱う。
5. ブランチ上で `python scripts/project_handoff.py --validate` と `python scripts/project_handoff.py --write` を実行して、台帳と引き継ぎを同期する。
6. Pull RequestのGitHub Actionsを検査。必要なPython/Windows/Blenderテストが実際に成功してから、`last_verified`・次の作業・進捗履歴を更新する。
7. mainへのマージ後、`CBDK durable handoff`ワークフローが再度Pythonテストを実行し、実測を `docs/project/LAST_CI.json` に、引き継ぎを `docs/PROJECT_HANDOFF.md` に同期する（GitHubの権限/ブランチ保護により自動pushできない場合はCI成果物を確認）。

## 現行の安全上の制約

- ユーザーの元アドオン、個人の .blend、認証情報、プライベートな抽出レポートをGitHubへ自動でコミットしない。
- プレビューアドオンは明示的に `--preview-unapproved` を指定。承認済みの公開Blender Extensionと呼ばない。
- BMesh加工の監査と座標復元は完全な原子性・クラッシュ耐性を保証しない。
- Blender GUIの見た目・マウス操作・Ctrl+Zの実際の操作感はヘッドレスCIだけでは検証できない。
- GitHubからBlenderへの直接インストール・更新機能は**ユーザー希望で保留**している。

## 再開のための最小コマンド

```bash
python scripts/project_handoff.py --validate
python scripts/project_handoff.py --write
python scripts/project_handoff.py --check
python -m unittest discover -s tests -v
```

最新の「既知の問題」と「次にやること」は `docs/project/STATE.json` を確認すること。過去のチャットを再読する必要はない。


## v0.16: メッシュ編集監査の性能・安全基準

- 監査前の要素数を直接読み取り、上限超はデータコピーや変更の前に中断する。
- 選択頂点の編集結果はライブBMeshから読み取り、未選択頂点・移動量・選択・辺/面接続の異常を拒否する。
- 世界座標が巨大でも、差分の許容誤差は期待移動量基準で判断する。浮動小数点精度の限界で期待差分を確認できなければ安全側に拒否する。
- Python/Windowsの回帰テストに加え、3バージョンのBlenderで中規模格子を用いた時間・メモリ観測、制限超過時の変更前拒否を確認する。
- 観測値は該当するGitHub Actionsとコミットに結び付ける。環境をまたぐ絶対性能保証はしない。



### 非有限座標からの復元契約（v0.16追補）

- 異常なBMesh座標の復元前に、頂点/辺/面の接続関係だけを検査する。NaN/Infを含む元データをスナップショット化し直して復元を妨げない。
- 元の座標・選択の書き戻し後に再検証し、誤った成功報告を避ける。完全に戻らない場合は「復元不完全」として明示。
- トポロジーが変わっている場合は座標復元による修復を保証せず中断。
- Blenderの致命的クラッシュや外部データを含む完全トランザクションを保証しない。
