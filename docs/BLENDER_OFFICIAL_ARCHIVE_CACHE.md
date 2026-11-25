# Blender公式アーカイブの固定SHAキャッシュ

2026-11-25 JST。R17のCIで公式チェックサムの取得がHTTP 403になったため、#109の旧キャッシュ方式から**公式SHAを固定する部分のみ**採用する。#109の他の変更は採用しない。

## 固定値の出典

PR [#109](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/109) HEAD `5dc20802ddc8f8f7e1ec6df2ed8d05d9ab4362c4`、[Blender run 42466221571](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42466221571)（2026-11-08）の3ジョブは、当時の公式 `download.blender.org/release/BlenderX.Y/blender-X.Y.Z.sha256` を取得し、その値でアーカイブを照合・実行して成功。ログの完全なcache keyから次を採録。今回の公式サイト直接再取得は成功していないので、現在の配布元の値を新たに確認したとは主張しない。

| Blender | 公式SHA-256（Linux x64 archive） | 実ジョブ |
|---|---|---|
| 4.4.3 | `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946` | [128686254929](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42466221571/job/128686254929) |
| 4.5.15 | `0d2b8bb2efe97e6c8eb57de6b7322f8800e1984e3125b60decca5f6771e4773e` | [128686254962](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42466221571/job/128686254962) |
| 5.2.1 | `a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9` | [128686254710](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42466221571/job/128686254710) |

## キャッシュ規約

- 固定バージョン・OS/arch・SHAによる完全一致キー。アーカイブのみrunner.tempに保存。展開済み実行ファイル、認証情報、ユーザーデータ、レポートは保存しない。復元キーの広いprefixは使わない。
- ヒットでもミスでも固定公式SHAの厳密照合後のみ展開・実行。壊れたキャッシュはfail closed、勝手に別SHAへ変更しない。必要なら該当キャッシュ削除をリポジトリ管理者が判断。固定SHA更新は公式値の取得・新しい候補CIを経たレビュー変更だけ。
- キャッシュミス時の公式本体の403は残り得る。キャッシュ保持・取得成功・速度改善は未実測。PR merge refのキャッシュは兄弟PRに共有されないため、開発ブランチへ本workflowが統合されたpushに限り既存の全3版smokeでキャッシュを初期化する。通常のPRゲート、workflow_dispatch、権限contents:read、nativeテスト・タイムアウトを維持。pull_request_targetなどの高権限イベントは使わない。
- [GitHub cache scope reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#restrictions-for-accessing-a-cache)。初期化成功後は実際の別PRログで共有ヒットを確認する。初回ミス・キャッシュ不整合・外部取得エラー・新規/既存native検証の成否は区別する。
- 既存R17候補#135の検証と別のA所有変更。R17候補を途中更新したり、旧#109をマージしたりしない。変更の統合時は最新devに基づく通常ゲートを確認し、main/正式公開/研究・私有データに触れない。
