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

## 2026-11-25 A追補（未受入）

- R17 #135 は dev `84c9629b0db4707f43009fd819be9402f68580f7` へ統合済み。独立7系統中6成功、Blender 5.2.1 の公式取得段階で HTTP 403（[run 45530836361](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45530836361)）。4.4.3/4.5.15 は成功。R17の正式受入は保留。
- #136旧HEAD `ecf7b7712548643e1b7e8554c0de8caf47f9f424` の [Blender run 45530757098](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45530757098) は3版成功。Python run 45530756986 は旧YAML表記を前提とする静的テスト2件で失敗。今回の修正はテストを新しい固定SHA行列と照合順序に合わせ、R17統合済みdevを取り込む。新HEADのCI、warm cache、共有ヒットは未確認。


## R17統合後の検証

#136 `e4e2e3aa4fbda487b9619e0ba4bae2e69cbdf415` の run 45532395189 で全3版実ログのCACHE_HITとSHA256_PASS、nativeテスト成功を確認。旧run 45530757098の全3版MISS・SHA256_PASS・保存も確認。dev `236b9a3254928d7cb69d5c415fd8a3e792ee5de7` のrun 45533937378は全3版MISS・SHA256_PASS・保存・native成功、独立7CI成功。これはPR検証の証拠でありdev push初期化完了・別PR間HITを証明しない。速度改善未測定。
