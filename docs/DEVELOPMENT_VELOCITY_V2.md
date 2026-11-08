# CBDK 開発速度 v2：測定・安全なCI短縮・A統合準備

> 2026-11-08 JST、A司令塔の開発改善。**段階導入**。本書を追加しただけでFast CIが必須Full CIを代替することはない。R14 B/C/Dの割当・担当外コード・正式v0.17.0/main・私有データ・権利ゲートは不変。

## 1. 実測したボトルネック

R13のA側4段階で実行されたBlender CIは、それぞれ約183、195、190、189秒。1回平均約189秒。Python約55秒、Windows約78秒。4つの結合/統合/文書CIの各クリティカルパスを単純加算すると約12分37秒（工程間の作業を含む壁時計時間ではない）。

問題はBlenderの品質確認自体ではなく、複数のSHAに対して同種の3版Blender実機検証を繰り返し、Aのレビュー・統合・次ラウンド指示が直列になりやすい点。CI時間だけでは実装時間やチーム待機を測れないため、PR作成/最終CI/統合/次チーム初回コミットの4時刻を別々に記録する。

## 2. 第1段階（このPRで実装・効果未測定）

### Blenderの公式アーカイブキャッシュ

- .github/workflows/blender-smoke.yml は毎回、Blenderの**公式SHA-256一覧をネットワーク取得**して、バージョンとSHA-256を含む厳密なキーで **tar.xzアーカイブだけ** をGitHub Actions cache v4から復元する。
- 初回またはcache miss時は公式サイトから取得。**cache hit時も必ずsha256sum --check --statusで再検証してから展開・実行**する。改ざん・一致しないキャッシュ・不正なSHA一覧・ダウンロード障害を正常と見なさない。
- 検証済みの実行ファイルや展開済みディレクトリはキャッシュしない。各ジョブのBlender 4.4.3/4.5.15/5.2.1は引き続き正式バイナリから展開し、全実機チェックを通す。
- cache missは遅くなる場合もある。PR内の同一Blenderバージョンで冷/温2回の実ジョブログとactions/cache hit/miss、zip転送/展開/実機各時間を比較し、純利益が観測できなければ撤回する。

### 開発時間をSHA単位で可視化

- python scripts/ci_cycle_metrics.py --sha <40桁> --gate 5 は、GitHubからそのSHAの5系統（Python/Windows/Blender/Chromium/Handoff）を読み、完全成功数・遅いworkflow・開始から完了までの時間をJSON表示する。
- --gate 7 はKit/Agent Skillも含めて7系統。--runs-json local-fixture.jsonはネットワーク不要の再現テスト。--output reports/latest/ci_timing.jsonでローカル保存できる。通信時のGITHUB_TOKEN/GH_TOKENは認証にのみ使用し、結果JSONへ書かない。
- 別SHAの成功、欠落ジョブ、処理中、失敗は全件greenに昇格しない。GitHub updated_atとcreated_atの差はキュー待ち・準備を含み、純粋なテスト処理時間ではない。
- 将来の開発ライブボードでは、このschema_version: 1の非機密集計JSONを読む。トークン、個人パス、私有ソース、実GLBを送らない。

### Aの読み取り専用・統合前チェック

- python scripts/abdc_preflight.py --pr B=107 --pr C=108 --pr D=106 を例とする。**必ず実際の当該ラウンドのPR番号に読み替える**。最新dev SHA、各専門PRのHEAD・base・ファイル所有範囲と当該HEADの5CIをGitHub APIから取得してJSON化。
- 変更パスの重複、共有/担当外ファイル、SHA不正、未提出、必須CI欠落を止める。正常に見えても結果はready_for_manual_integration_reviewだけで、**自動結合/自動承認/自動マージは行わない**。変更ファイルが衝突0でもAPI・振る舞い・依存の人手レビューは必須。
- 現状のR14 B #107 / C #108 / D #106をAが再検証する際は、最新のPR HEADを都度取得する。R13以前の専門PRを再マージしない。

## 3. 第2段階（未実装・次のPRで実験）

**Fast Feedback** は担当ブランチの途中で対象ユニットテスト、静的解析、影響する短いBlenderスモークを先に回す選択式。Full CIの正式ゲートを変更せず、早期欠陥検出までに限定する。

**Full Gate** は専門PRの最終HEADで必要5系統、Aの組合せHEADで必要5系統、dev統合最終HEADで独立7系統。上記で安全の証拠を省略して「成功」にしない。

STATE.jsonや文書だけの変更で重いBlenderを起動しない案は、まず必須チェック/Branch Rulesetsの実構成と変更分類のテスト、文書修正のみの回帰を設計してから別PRへ。GitHub Actionsのpathsで必須workflowを丸ごとskippedにするとPendingになりマージ不能になる可能性がある。固定名の必須gate jobを常時発火させ、影響判定と実ジョブを分ける方式を検討する。CI不要を未実行の成功として記録しない。

## 4. 第3段階（未実装・開発ローリングの短縮）

- B/C/D作業中にAがそのラウンドの3 PRを逐次レビューし、さらに次ラウンドの所有パス・受入条件・未知のリスクを**read-only設計**しておく。
- B/C/Dが完了しても、自動で旧SHAから次PRを量産しない。Aが一度だけ結合して独立CIに成功するまでは、次のラウンドの文書/テストケース設計だけ先行する（公式割当が許す場合を除く）。
- R15候補（**未承認・未着手**）：BはGLB triageの誤診断負例を測る、Cは登録回復UIの実機と表示のずれを縮める、DはTOCTOU診断の拒否理由を定量評価。R14の成果/最新STATE次第で変更・撤回する。
- GitHub開発ライブボードへsubmitted_at→final_CI_at→combined_CI_at→dev_merge_at→next_first_commit_atを記録し、「BCD完了後Aが待たせた時間」「CI時間」「機能実装の成果」を別メーターにする。

## 5. 採用判定と停止条件

- 最初の導入候補は**Blender cache + 時間計測 + PR前チェック**だけ。導入PRはA専用ブランチからドラフトにし、影響する全CIが成功するまでdevにマージしない。既存R14 B/C/Dブランチは一切触らない。
- 冷キャッシュ・温キャッシュの実測、CI失敗率、誤拒否件数、A統合作業時間を比較する。目標例：A側4段階で約12分37秒のCI単純合計を6〜9分へ。ただしこれは目標であって達成済みの成果ではない。
- Fast/Full変更後も安全上必須のゲートは残し、品質と速度の両方を確認。原因不明のCIスキップ、SHA不一致、cache hash不一致、未実証の速度改善、private情報漏えい懸念があれば停止・差し戻す。
- 正式リリース、main、私有GLB/アドオン、実Windows GUI、ライセンス/公開/権利に関する承認は別途必要。


## 6. 第1回実測（冷キャッシュ、2026-11-08 UTC）

PR #109の初期候補HEAD: 31fdff9560c053faabc300e57c457460fcfdd96d。
[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42459418028)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42459418405)、[Blender 3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42459418062)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42459418132)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42459418095)が**初回5系統すべて成功**。

- Blender workflow wall時間（作成→終了）は184秒（07:35:21〜07:38:25 UTC）。旧4回平均約189秒より僅差で、**速度改善が実証されたとは言えない**。
- Blenderの3バージョンは新しい公式SHA取得/キャッシュ復元/再検証/Blender起動・実機テストを正常通過。初回の各ジョブログで対象版ごとのchecksum-keyed cache保存を確認。
- この記録だけではcache hitが未観測。次のPR内の別HEADで、同じBlender実装・版・チェックサムキーを使った**温キャッシュ1回**を測定し、時間を比較する。温キャッシュが遅い、cache integrityが失敗する、品質回帰がある場合は採用を見送る。
