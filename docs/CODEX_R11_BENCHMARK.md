# Codex単独開発・速度比較実験 R11

本書は実験専用の引き渡し資料。既存のABCD運用・正本STATE・担当所有権を置き換えない。
R12は提案のみで、正式割当・実装開始・次世代移行を意味しない。

## 実施範囲と計測方法

- 実験開始：`2026-11-07T23:58:03Z`（clockツールで開始直後に採取）。以下はUTC。
- 単独Codex、B→C→Dの逐次実装。sub-agent不使用。CI・API読み取りは並行し、実装中も先行PRのCIを継続。
- 基点・終了時dev：[`a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0)。開始時fetchと終了時ls-remoteで照合。開発ブランチへpush/mergeしていない。
- main/正式v0.17.0、共通CI、STATE形式・ID、自動Handoff、既存ABCD役割・履歴は変更なし。Notionも指示どおり未変更。
- PR REST APIのcreated_at/merged_at/head.sha、commits APIのcommitter.date、Actions runs/jobs APIを使用。
- 「全成功時刻」は最終HEADの指定5系統すべてがsuccessとなったrunの **updated_at最大値**。これはGitHub APIで観測できる終了時刻代理値であり、内部で結論が確定した瞬間の高精度測定ではない。ジョブ終了は別表のcompleted_atを使用。
- 既存パスfilterが今回の新テストをBlender発火対象に含めないため、Blenderのみ同一ブランチ・同一HEADでworkflow_dispatch。PR eventのmerge ref検証と、dispatchの厳密HEAD checkoutを混同しない。共通workflowは変更していない。
- キュー代理値＝workflow created_at→各job started_at（最小–最大）。依存待ち・runner割当を含み、純粋なGitHub内部queueを分離できない。job時間＝completed_at−started_at。合計job秒は並列実行を足した消費時間、実経過時間とは別。
- PRのupdated_atは本文更新等でも変わるため「最終修正」は最終コードcommit時刻を使用。レビュー待ち・内部思考時間・純粋な実装労働時間・トークン/コストは未計測。開始→完了はCI待ちと並行作業を含む経過時間。
- PR作成前にpushされたcommit、別branchの同一SHA、削除されたrun等をGitHubだけから完全復元できない。再試行・失敗数の範囲は対象PRに含まれるcommitと、その担当head_branchの可視run（ページ上限100）。R10チャット開始時間は不明。

## 開始時CIと成果物の正確な参照

開始devの7系統はいずれもsuccess（以下は過去の開始状態で、R11候補の代用ではない）。

| 系統 | run | 終了代理時刻UTC |
| --- | --- | --- |
| CBDK durable handoff | [run 42426798042](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798042) | 2026-11-07T23:47:16Z |
| CBDK Agent Skill package | [run 42426798076](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798076) | 2026-11-07T23:47:15Z |
| CBDK Windows kit package | [run 42426798132](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798132) | 2026-11-07T23:47:14Z |
| CBDK offline 3D browser interaction smoke | [run 42426798163](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798163) | 2026-11-07T23:47:57Z |
| CBDK Python tests | [run 42426798099](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798099) | 2026-11-07T23:47:56Z |
| CBDK Windows PowerShell launcher regression | [run 42426798049](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798049) | 2026-11-07T23:48:13Z |
| CBDK Blender multi-version runtime smoke | [run 42426798065](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426798065) | 2026-11-07T23:49:44Z |

| R11領域 | ブランチ | draft PR | 最終HEAD |
| --- | --- | --- | --- |
| B | `work/v018-glb-analysis-r11-codex` | [#88](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/88) | [`de2a5e12b15acb2b14281738619a4ef909db0117`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/de2a5e12b15acb2b14281738619a4ef909db0117) |
| C | `work/v018-ui-builder-r11-codex` | [#89](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/89) | [`8ec215c97dd20e2cea2597589899b98904282eaf`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/8ec215c97dd20e2cea2597589899b98904282eaf) |
| D | `work/v018-extension-quality-r11-codex` | [#90](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/90) | [`a5bda5bc46c69fd936de73f7fb50350b2109b505`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a5bda5bc46c69fd936de73f7fb50350b2109b505) |
| 統合候補 | `work/v018-integration-r11-codex` | [#91](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/91) | [`faab6ab023f50495c719d091b29f320aa6ab36df`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/faab6ab023f50495c719d091b29f320aa6ab36df) |

レポートは別ブランチ `work/v018-r11-codex-benchmark` のdraft PR（本書を含むPR）。基点devとの差分はこのファイルのみ。専門PR・統合候補もすべて未マージ。

## 開発経過時刻

| 区分 | 着手記録UTC | 最初のテスト実装commit UTC | PR作成UTC | 最終commit UTC | 最終HEADの5系統全成功UTC |
| --- | --- | --- | --- | --- | --- |
| B | 2026-11-07T23:59:54.756694+00:00 | 2026-11-08T00:01:48Z | 2026-11-08T00:01:51Z | 2026-11-08T00:02:03Z | 2026-11-08T00:07:05Z |
| C | 2026-11-08T00:02:03.131445+00:00 | 2026-11-08T00:03:45Z | 2026-11-08T00:03:49Z | 2026-11-08T00:04:36Z | 2026-11-08T00:07:36Z |
| D | 2026-11-08T00:04:23.538745+00:00 | 2026-11-08T00:05:52Z | 2026-11-08T00:05:56Z | 2026-11-08T00:08:52Z | 2026-11-08T00:12:00Z |
| 統合候補 | 2026-11-08T00:06:12Z | 2026-11-08T00:06:12Z | 2026-11-08T00:07:32Z | 2026-11-08T00:08:58Z | 2026-11-08T00:14:04Z |

Bの着手欄は分析を記録したcheckpoint。最初の調査はそれ以前に始まっており厳密な領域初読時刻は未計測。主要順B→C→D、修正時は前領域へ戻る逐次作業。領域の開始→最終commitは他作業/CI待ちを含むので純粋実装時間ではない。製品本体の実装commitはなし（許可されたtests/docs中心のR11）。

## CI実測（最終HEAD）

PRのPython3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1、Chromium、Handoffを区別。キューと実行は秒。実行欄はjob合計/最長job、終了は最後の非skip job。handoff sync-main等の条件付きskipは対象外。

| 対象 | 系統とrun | 結論 | queue代理 最小–最大秒 | job秒 合計/最長 | 最後のjob終了UTC |
| --- | --- | --- | ---: | ---: | --- |
| #83 | [Blender×3 42425328833](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425328833) | success | 3–4 | 430/164 | 2026-11-07T23:30:18Z |
| #83 | [Python×3 42425328851](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425328851) | success | 3–4 | 89/35 | 2026-11-07T23:28:08Z |
| #83 | [Windows×2 42425328866](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425328866) | success | 4–4 | 115/61 | 2026-11-07T23:28:35Z |
| #83 | [Handoff 42425328859](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425328859) | success | 3–3 | 6/6 | 2026-11-07T23:27:39Z |
| #83 | [Chromium 42425328875](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425328875) | success | 4–4 | 33/33 | 2026-11-07T23:28:07Z |
| #84 | [Blender×3 42425333380](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425333380) | success | 3–4 | 434/161 | 2026-11-07T23:30:18Z |
| #84 | [Python×3 42425333402](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425333402) | success | 3–4 | 81/35 | 2026-11-07T23:28:12Z |
| #84 | [Windows×2 42425333366](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425333366) | success | 4–4 | 103/54 | 2026-11-07T23:28:32Z |
| #84 | [Handoff 42425333371](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425333371) | success | 4–4 | 8/8 | 2026-11-07T23:27:46Z |
| #84 | [Chromium 42425333379](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425333379) | success | 3–3 | 27/27 | 2026-11-07T23:28:04Z |
| #85 | [Blender×3 42425364434](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425364434) | success | 3–7 | 459/174 | 2026-11-07T23:31:01Z |
| #85 | [Python×3 42425364572](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425364572) | success | 6–13 | 95/38 | 2026-11-07T23:28:44Z |
| #85 | [Windows×2 42425364431](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425364431) | success | 3–3 | 113/57 | 2026-11-07T23:29:00Z |
| #85 | [Handoff 42425364440](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425364440) | success | 3–3 | 8/8 | 2026-11-07T23:28:11Z |
| #85 | [Chromium 42425364553](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425364553) | success | 9–9 | 31/31 | 2026-11-07T23:28:40Z |
| #86 | [Blender×3 42425995934](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425995934) | success | 3–4 | 477/188 | 2026-11-07T23:39:21Z |
| #86 | [Python×3 42425995892](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425995892) | success | 3–4 | 111/45 | 2026-11-07T23:36:58Z |
| #86 | [Windows×2 42425995843](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425995843) | success | 3–4 | 124/71 | 2026-11-07T23:37:24Z |
| #86 | [Handoff 42425995915](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425995915) | success | 3–3 | 6/6 | 2026-11-07T23:36:19Z |
| #86 | [Chromium 42425995902](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42425995902) | success | 3–3 | 31/31 | 2026-11-07T23:36:44Z |
| #87 | [Blender×3 42426581941](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581941) | success | 3–4 | 385/149 | 2026-11-07T23:46:41Z |
| #87 | [Python×3 42426581928](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581928) | success | 3–4 | 133/47 | 2026-11-07T23:45:00Z |
| #87 | [Windows×2 42426581847](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581847) | success | 3–4 | 127/72 | 2026-11-07T23:45:24Z |
| #87 | [Kit 42426581959](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581959) | success | 4–4 | 6/6 | 2026-11-07T23:44:19Z |
| #87 | [Handoff 42426581855](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581855) | success | 3–3 | 10/10 | 2026-11-07T23:44:22Z |
| #87 | [Chromium 42426581933](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42426581933) | success | 4–4 | 43/43 | 2026-11-07T23:44:56Z |
| #88 | [Blender×3 42427899683](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427899683) | success | 148–149 | 409/149 | 2026-11-08T00:07:04Z |
| #88 | [Python×3 42427904678](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427904678) | success | 19–20 | 130/51 | 2026-11-08T00:03:19Z |
| #88 | [Windows×2 42427904651](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427904651) | success | 19–19 | 123/69 | 2026-11-08T00:03:37Z |
| #88 | [Handoff 42427904763](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427904763) | success | 4–4 | 8/8 | 2026-11-08T00:02:21Z |
| #88 | [Chromium 42427904702](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427904702) | success | 3–3 | 29/29 | 2026-11-08T00:02:41Z |
| #89 | [Blender×3 42428098225](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428098225) | success | 4–4 | 478/172 | 2026-11-08T00:07:35Z |
| #89 | [Python×3 42428102447](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428102447) | success | 3–3 | 107/39 | 2026-11-08T00:05:25Z |
| #89 | [Windows×2 42428102218](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428102218) | success | 8–8 | 121/64 | 2026-11-08T00:05:54Z |
| #89 | [Handoff 42428102338](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428102338) | success | 3–3 | 6/6 | 2026-11-08T00:04:52Z |
| #89 | [Chromium 42428102238](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428102238) | success | 3–3 | 28/28 | 2026-11-08T00:05:13Z |
| #90 | [Blender×3 42428428282](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428428282) | success | 7–8 | 449/174 | 2026-11-08T00:11:59Z |
| #90 | [Python×3 42428430101](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428430101) | success | 4–4 | 111/43 | 2026-11-08T00:09:45Z |
| #90 | [Windows×2 42428430087](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428430087) | success | 3–4 | 135/78 | 2026-11-08T00:10:20Z |
| #90 | [Handoff 42428430077](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428430077) | success | 4–4 | 6/6 | 2026-11-08T00:09:08Z |
| #90 | [Chromium 42428430076](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428430076) | success | 3–3 | 28/28 | 2026-11-08T00:09:29Z |
| #91 | [Blender×3 42428437205](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428437205) | success | 112–113 | 464/187 | 2026-11-08T00:14:04Z |
| #91 | [Python×3 42428440872](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428440872) | success | 3–4 | 115/49 | 2026-11-08T00:10:00Z |
| #91 | [Windows×2 42428440871](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428440871) | success | 4–4 | 140/77 | 2026-11-08T00:10:28Z |
| #91 | [Handoff 42428440875](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428440875) | success | 3–3 | 8/8 | 2026-11-08T00:09:18Z |
| #91 | [Chromium 42428440910](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428440910) | success | 3–3 | 35/35 | 2026-11-08T00:09:45Z |

### R10対照PR

| PR | 作成UTC | 最終HEAD | 最終commit UTC | merge UTC | 5系統全成功UTC |
| --- | --- | --- | --- | --- | --- |
| [#83](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/83) | 2026-11-07T23:27:27Z | [`9f3df76df7356acb3670d6c44a53325f7bda6eba`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/9f3df76df7356acb3670d6c44a53325f7bda6eba) | 2026-11-07T23:26:56Z | null（専門PR自体は未マージ） | 2026-11-07T23:30:18Z |
| [#84](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/84) | 2026-11-07T23:27:31Z | [`262d646dc6de394755349fab6fdc864e3ae4a3b5`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/262d646dc6de394755349fab6fdc864e3ae4a3b5) | 2026-11-07T23:27:07Z | null（専門PR自体は未マージ） | 2026-11-07T23:30:19Z |
| [#85](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/85) | 2026-11-07T23:27:57Z | [`a3c57d9b8450e18033741c87d9ba41625dd7ac2a`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a3c57d9b8450e18033741c87d9ba41625dd7ac2a) | 2026-11-07T23:27:23Z | null（専門PR自体は未マージ） | 2026-11-07T23:31:02Z |
| [#86](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/86) | 2026-11-07T23:36:06Z | [`6a12b7fa1926912f501c80b133d0d457cdc19999`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/6a12b7fa1926912f501c80b133d0d457cdc19999) | 2026-11-07T23:36:01Z | 2026-11-07T23:39:44Z | 2026-11-07T23:39:21Z |
| [#87](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/87) | 2026-11-07T23:37:14Z | [`f850996e71ed989e53120732bd50fa4427e33fec`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/f850996e71ed989e53120732bd50fa4427e33fec) | 2026-11-07T23:44:02Z | 2026-11-07T23:46:59Z | 2026-11-07T23:46:41Z |

#87は状態同期/割当の別工程で最終HEADにKit含む6系統、今回の開発5系統比較とは分ける。専門#83–#85自体のmerged_atはnullだが、内容は#86経由でdevに統合済み。

### 直接比較できるGitHub経過時間

| 指標 | R10 ABCD | R11 Codex |
| --- | ---: | ---: |
| 最初の専門PR→3専門最終HEAD全成功 | 3分35秒 | 10分09秒 |
| B PR作成→最終HEAD全成功 | 3分05秒 | 5分14秒 |
| C PR作成→最終HEAD全成功 | 2分51秒 | 3分47秒 |
| D PR作成→最終HEAD全成功 | 2分48秒 | 6分04秒 |
| 3専門最終HEAD成功→結合CI全成功 | 8分19秒 | 2分04秒 |
| 統合PR作成→結合CI全成功 | 3分15秒 | 6分32秒 |
| 統合候補commit作成→結合CI全成功 | 3分20秒 | 7分52秒 |

CI待ちは実装と重なるため上表の工程時間は足し合わせられない。Codexは全専門CI完了前に候補を組み立てて独立検証している。R10/R11の課題難易度と成果（R10は本体変更、R11は負例・検証中心）が異なる。これらから開発生産性の優劣や速度比を一般化しない。

参考：Codex開始→結合CI全成功 16分01秒。R10のチャット着手時刻は不明なので直接比較不可。レポート編集/レビュー待ちはこの開発ゲート時間に含めない。

### 可視run履歴の失敗・再実行

| 対象 | 可視run数 | failure | cancelled | 同run再試行(run_attempt−1) |
| --- | ---: | ---: | ---: | ---: |
| #83 | 5 | 0 | 0 | 0 |
| #84 | 5 | 0 | 0 | 0 |
| #85 | 5 | 0 | 0 | 0 |
| #86 | 5 | 0 | 0 | 0 |
| #87 | 9 | 0 | 0 | 0 |
| #88 | 10 | 0 | 2 | 0 |
| #89 | 9 | 0 | 1 | 0 |
| #90 | 10 | 1 | 0 | 0 |
| #91 | 10 | 1 | 0 | 0 |

修正HEADでの新runは再検証として上のrun数へ含むが、GitHubの同run retryとは区別。B文書1回・Cローカルharness1回・D Windows fixture1回の修正に伴う再検証。統合候補はD修正で1度更新、旧候補のWindows失敗はDと同根で別の製品欠陥ではない。キャンセルはPR更新時の既存concurrencyによる。手動同一run再試行は0。R10のチャット上の手戻り/テスト失敗はGitHubから復元不能で不明。

| 旧失敗run | 事象 |
| --- | --- |
| [#88 / 42427885113](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427885113) | CBDK Windows PowerShell launcher regression / cancelled / HEAD [`3b430e8b1c5ce5f9c872f12a73ee7ae0fa2310af`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/3b430e8b1c5ce5f9c872f12a73ee7ae0fa2310af) |
| [#88 / 42427885160](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42427885160) | CBDK Python tests / cancelled / HEAD [`3b430e8b1c5ce5f9c872f12a73ee7ae0fa2310af`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/3b430e8b1c5ce5f9c872f12a73ee7ae0fa2310af) |
| [#89 / 42428039235](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428039235) | CBDK Windows PowerShell launcher regression / cancelled / HEAD [`6d9ac34516c45ad43a225a0859eaa1f9b39131bf`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/6d9ac34516c45ad43a225a0859eaa1f9b39131bf) |
| [#90 / 42428203959](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428203959) | CBDK Windows PowerShell launcher regression / failure / HEAD [`2c11e6a7d4fe27923a5809ecaf70a14ea0775069`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/2c11e6a7d4fe27923a5809ecaf70a14ea0775069) |
| [#91 / 42428325224](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428325224) | CBDK Windows PowerShell launcher regression / failure / HEAD [`3984f878dbb4071c1ee58f6cc0d9309d2b03b223`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/3984f878dbb4071c1ee58f6cc0d9309d2b03b223) |

### 失敗から修正・再検証までの観測時間

| 対象 | 失敗run作成→終了代理 | 失敗終了代理→修正commit | 修正commit→最終5系統成功 |
| --- | ---: | ---: | ---: |
| D #90 | 00:06:00Z→00:07:07Z＝67秒 | →00:08:52Z＝105秒 | →00:12:00Z＝188秒 |
| 統合 #91（同じD fixture） | 00:07:35Z→00:08:48Z＝73秒 | →00:08:58Z＝10秒 | →00:14:04Z＝306秒 |

105秒は調査・artifact取得失敗・修正・他作業を含む経過時間で、純粋な編集時間ではない。
統合の10秒は修正済みDの取り込み間隔であり、別の欠陥修正ではない。
Cの失敗ローカルrun開始/終了時刻は個別未計測。first→last commit 00:03:45Z→00:04:36Z（51秒）は修正経過の参考値で、失敗検出からの正確な作業時間ではない。
GitHubの同run再試行0、修正HEADでの再検証を別計上する。

## B性能実測（最終B PRのPythonログ）

5回warmed中央値ms、tracemalloc peakはPython traced heapでRSSではない。時間の小さな差・ばらつきを根拠に最適化を採用していない。

| Python | sparse_first | 固定R8 ms | 適応R10 ms | 元R2 ms | peak bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| 3.13 | False | 1.418 | 1.616 | 1.563 | 37008 |
| 3.13 | True | 1.435 | 1.418 | 1.586 | 37008 |
| 3.12 | False | 1.721 | 1.697 | 1.604 | 37008 |
| 3.12 | True | 1.747 | 1.716 | 1.624 | 37008 |
| 3.11 | False | 1.065 | 1.086 | 1.034 | 37000 |
| 3.11 | True | 1.074 | 1.053 | 1.027 | 37000 |

性能/メモリログはリンク先Python runで再確認できる。合成上限以下の測定であり、任意の私有GLBの性能・精度保証ではない。

## 結合native実行・受け入れ記録

| Blender | R11マーカー数 | R10マーカー数 | headless | GUI |
| --- | ---: | ---: | --- | --- |
| 4.4.3 | 4 | 5 | True | False |
| 4.5.15 LTS | 4 | 5 | True | False |
| 5.2.1 LTS | 4 | 5 | True | False |

証拠：[最終結合Blender run 42428437205](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42428437205) の既存R5 native lifecycle step。R11の4固有マーカーすべてを各版のJSONで確認。R5–R10既存経路は削除なし。

R11の3領域とも指定された安全な合成検証を実施。全体要件/NEXTを新たにdoneへ昇格していない。数学的な全入力証明・任意実モデル・GUI・権限判断・本流post-merge検証は受け入れ外/未実施として維持。

### 速度改善余地とボトルネック

- 基本環境のPython版を先に確認し、native fixtureの期待状態をローカルで確定してからpushすればB/Cの余分な更新を避けられた。
- Windows short-name等の正規化はR10のroot定義をそのままfixtureにも適用するべきだった。Linuxでの成功だけではWindows証拠にならない。
- テスト専用変更がBlender path filterに含まれないため手動dispatchが必要。Aの運用判断が必要だが、本実験でCI構造は変更しない。
- runnerキュー・target3版のダウンロード/実行と、修正HEADに対する独立再検証が終盤の待ち時間。単独の実装でもCIはパイプライン化できる。
- GitHubから同基準で取れるPR→greenを使い、チャット開始/モデル内部時間/費用を推測で埋めない。

再取得例：`gh api repos/mibesamiti-png/Chappy-Blender-DevKit/pulls/91`、`gh api "repos/mibesamiti-png/Chappy-Blender-DevKit/actions/runs?head_sha=<final_sha>&per_page=100"`、各runの`/jobs?per_page=100`。head_branchとhead_shaを照合し、統合PRに含まれる専門commitのCIを統合CIに数えない。

## 成果と品質

| 領域 | R11で実施した内容 | 結果・制約 |
| --- | --- | --- |
| B / NEXT-008 | 最初の64判定にdense→sparse / sparse→dense偏り、候補順、float32、255/256/257辺、64部品/512面、退化線分 | 4新規Pythonテスト。全辞書の固定R8/非pruned R2一致、R3独立接触判定を保持。偏りcontourでは64回/388回のbbox判定差、結論同じ。演算数はbbox呼び出し/除外数を計測、R2算術演算数そのものは未計測 |
| C / UI-001・BUILD-001 | 両Scene属性×missing/foreign/owned-looking、未解放class ledger、部分retry後のreload/register拒否、実addon_utils.disable一過性失敗 | 2新規Pythonテストと既存native経路への4マーカー。完全一致した内容でもtoken identityが異なればforeign保全。明示unregisterで回復し再enable/disable。5機能/6レシピ維持 |
| D / EXT-001 | 一時checkout更新と自己rehash ZIPの比較、CRLF/LF、大小文字inventory/未知root/allowlist、symlink親逸脱 | 4新規Pythonテスト。ソースを開く前の逸脱拒否。旧snapshotとの不一致だけでは改変と合法更新を識別不能。7プレビュー正例・既存予算・公開禁止を保持 |

### 品質・完了率の比較範囲

| 指標 | R10 ABCD | R11 Codex |
| --- | --- | --- |
| 専門最終HEADの5系統ゲート | 3/3専門PR成功 | 3/3専門PR成功 |
| 独立結合HEADの5系統ゲート | 1/1成功 | 1/1成功 |
| 担当変更パス | 12、担当重複0（正式キュー記録） | 7、担当重複0、結合競合0 |
| 製品変更 | 適応AABB・二重解除失敗回復等（既存コード/記録） | 製品欠陥未再現、本体変更0 |
| 新規回帰 | 過去PRの新規件数は今回独立計数していない | Python 10件、native固有4マーカー×3版 |
| 自動化対象の受け入れ | 正式キューにAのR10達成記録あり。今回の独立再審査率は不明 | R11 B/C/Dの安全な合成検証3/3領域実施（演算数はbboxのみ） |
| 人間/実データ/GUI/権利 | 未保証のまま | 未保証のまま、完了率へ算入しない |
| 状態同期と本流post-merge | #87と開始dev証拠あり | 禁止指示につき未実施、Aへ更新提案のみ |

R10とR11の「全機能完了率」を同一分母にできない。両方が同一安全基準のCIゲートを通過したことと、任意実モデルや全仕様を満たしたことは別。

本体の意味的な不具合は今回再現していない。性能利益の一貫した証拠もないため、本体変更・上限緩和・新trust API追加はしていない。
Bの偏りcontourでのR2/R8判定一致と、三角形fixtureの全辞書比較は異なる検証単位。
サンプル一致は完全幾何一致や物理穴・真の部品対応を証明しない。原因候補は因果証明ではない。

ローカル：Python 3.12.14、B新規4件、C新規2件（関連lifecycle 44件）、D新規4件（R10/R11関連12件）成功。
初期結合HEAD [`3984f878dbb4071c1ee58f6cc0d9309d2b03b223`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/3984f878dbb4071c1ee58f6cc0d9309d2b03b223) の全体1,064件成功、54.481秒。
最終結合HEADではDのroot正規化4件をローカル再実行し成功、全体回帰は対応CIで再確認。
登録監査はstatic_checks_passed、5機能/6レシピ。ローカルBlender4.3.2の成功は対象3版の代用にしない。

### 発見・修正・手戻り（隠さず計上）

1. B文書にローカルPythonを誤って3.11と記載し、3.12.14へ修正。コード不具合ではないが追加commit/CI発火を生んだ。
2. C初期ローカルnativeテストで、保全したforeign属性があるのにassert_detachedを呼ぶ新規harness矛盾を検出。foreign保全→fixture削除→detach検査へ修正、再実行成功。初回PR本文の先走った成功記載を訂正。製品側token判定の欠陥ではない。
3. D初期Windows3.11/3.13で新規fixtureが失敗（1failure/2errors）。synthetic rootを未正規化で固定していたため、Windowsの一時パス別名とresolve結果が不一致。rootを既存R10同様resolveしてから固定。拒否条件は緩めていない。修正をD専用commitとして統合候補へ追随。
4. 変更前からtracked Handoffに生成結果より7つ余分な空行があり、単独 `project_handoff.py --check` は失敗。非空行本文は一致、--validateは成功。初期の成功報告はテスト中の出力との取り違えとして訂正。CIは--write後に--checkするため緑でもtrackedファイルの一致証明ではない。共有文書の直接変更禁止に従いAへ再生成を依頼。
5. gh pr editは旧Projects GraphQLエラー。履歴/運用を変えずREST PATCHで本文更新。Windowsの詳細artifactダウンロードは接続先403で不可、Actionsの失敗jobログは取得済み。未取得artifact内容は証拠にしていない。

製品の回帰は今回のテスト範囲では未検出。実GLB・私有addon・第三者実共存・Windows GUI/Ctrl+Z・権利・正式Extensions公開は未検証/未承認。既存制限の解除なし。

## 最終照合

最終結合Python CI（run 42428440872）は3.11/3.12/3.13すべて1,064件成功。各jobの実測秒は上記runログで確認可能。
終了dev HEADの再取得：[`a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0)（2026-11-08T00:15:44.535932+00:00）。開始時と一致。
レポート作成に先立ち、専門3件と結合1件のdraft/未マージ、各最終HEAD5系統successをAPIで再確認。
レポートPR自体はdocs-onlyであり、開発ゲート時間/CI成功率の比較から除外する。

### dev未統合の変更ファイル一覧

- B：`tests/test_glb_match_bias_r11.py`、`docs/GLB_R11_PROBE_BIAS.md`
- C：`tests/test_ui_lifecycle_r11.py`、既存 `tests/blender_ui_lifecycle_r5.py` へのR11 probe追加、`docs/UI_R11_OWNERSHIP.md`
- D：`tests/test_extension_source_reference_round11.py`、`docs/EXTENSION_R11_SNAPSHOTS.md`
- レポート専用：`docs/CODEX_R11_BENCHMARK.md`（統合候補には含めず別PR）

専門コードの取り込み順はB→C→Dを再現できるが相互未統合依存なし。報告書の採否はコード候補と独立してAが判断する。

## Aへの引き渡しとABCD復帰

1. 下表の専門PRと統合候補の最終SHA、差分7ファイル、CI・nativeマーカーを照合する。全PRはdraftで未マージ。
2. 追加指示またはAのレビュー後に取り込みを判断。**統合候補だけを取り込むか、B→C→Dを新たな統合候補へ一度だけ集約するか、どちらか一方**。専門PRと統合候補を重複採用しない。旧#83–#85等は#86に反映済み、再マージしない。
3. devが進んでいれば最新版基点で新候補を作り、結合5系統を再確認。force push/rebaseによる履歴置換は不要。共通API依存追加なし、担当ファイル重複0、結合競合0。
4. 本流取り込み後の独立7CIは今回**未実行**（本流マージ禁止のため）。Aが従来ゲートを維持し、必要な時点で実行する。Kit/Skillも今回の各専門・統合候補で未実行。開始devの過去成功を候補の成功に流用しない。
5. AがSTATEのlast_verified/decision等へR11 exact SHAと実測CI、B/C/Dの限定達成・修正/失敗履歴・人間ブロッカーを同期。機能/NEXTの安易なimplemented/done昇格は不要。開始正本は要件44＝実装済26/一部16/未実装1/保留1、NEXT24＝完了18/継続5/保留1で、今回未変更。
6. AがHandoffをSTATEから再生成し--check、PROGRESSへR11範囲とCI/未統合を追記。既存Notionへ公開安全な要約だけを節目同期（本実験ではNotion未変更、同期成功扱いにしない）。本レポートはその提案であり正本の代替ではない。
7. R12は下記候補をAが正式割当するまで実装しない。v0.19承認は保持するが、現行自動化/人間ブロッカー整理/PR25統合方針等のゲートを飛ばさない。正式release/main/私有データ利用は別承認。

## R12先行提案 — NOT ASSIGNED / NOT STARTED

### B候補：順序偏りの継続観測と再プローブ必要性の判断（優先度P2）

- 目的：first64の非代表性が大きな実害になる条件を特定し、根拠なく適応方式を複雑化しない。
- 実装内容候補：R11の2順序だけでなく、同一segment multisetの固定seed permutation、7/8除外の決定境界、後半で密度が反転する非厳密一致モデルを追加。テスト専用traceでR2最近接評価回数も測定。再プローブ等の本体変更は反復利益と安全性が確認できた場合だけ別途レビュー。
- 変更対象：B所有 `tests/test_glb_match_*`、GLB専用docs。欠陥/測定利得がある時だけ `cbdk/glb_part_match.py`。共通CI/scripts/STATEはA。
- 受け入れ条件：全辞書が元R2/固定R8と一致、R3独立、256辺/64部品/512面/auto_apply=false保持。Python3版のpaired中央値・peakと順序ばらつきを提示。改善なしならtests/docsのみを許容。
- 必要テスト：float32近接/ゼロ長/255–257辺、同一境界・異内部形状、contact/gap、再順序・両方向比較、performanceとメモリ上限。ユーザーGLB不要。

### C候補：失敗disable後のBlenderフラグと再試行境界（優先度P1）

- 目的：R11で観測した「Blender側は無効、CBDK class ledgerはpending」の状態を誤って回復済みと扱わない。
- 実装内容候補：disable一度失敗→二度目disable/enable/reloadの挙動を明示観測。class-only/Scene-only/両方失敗とforeign差替を組み合わせ、各段階の__addon_enabled__と台帳を検証。明示unregister後にのみ復帰する手順を文書化。問題再現時だけ最小の診断/所有権修正（自動retry・foreign削除は導入しない）。
- 変更対象：C所有 `tests/blender_ui_lifecycle_r5.py`、UI専用Python tests/docs、欠陥時のみ `templates/modular_preview/`。共有smoke/CIはA。
- 受け入れ条件：新native_r12_*が3版すべてで実行、pending中の偽成功なし、原token以外を削除しない、明示回復後漏れ0、既存R5–R11マーカー/5機能6レシピ維持。
- 必要テスト：Blender4.4.3/4.5.15/5.2.1のaddon_utils実経路、複数retry、reload拒否、同内容別token、Python/Windows回帰。実GUI/第三者Addon証明とは分離。

### D候補：参照snapshot基準の明示とWindows正規化負例（優先度P1）

- 目的：checkout更新差を真正性判定と取り違えず、Windows短名/大小文字/junctionを含むroot制約を実証する。
- 実装内容候補：テスト専用snapshot記録に独立基点commitと比較条件（LF正規化・inventory digest）を付し、古い/変更された基準の比較をレビュー上区別。commit自己申告で公開権限を付与しない。Windows実行可能な一時junction/親symlink/leaf symlink/短名rootのケースを追加。未知rootをalias認定する本体APIは追加しない。
- 変更対象：D所有 `tests/test_extension_source_reference_round*.py`、Extensions専用docs。実問題が確認された場合だけ `cbdk/extension_*`。共有validator/CIはA。
- 受け入れ条件：基準不明/相違はinconclusiveまたは拒否、許可外読取0、出力にpath/payload/PIIなし。CRLF/LF仕様を明示。ZIP制限/7正例/blocked_for_extension_release/全権限false保持。
- 必要テスト：Python3版/Windows2版での一時checkout、source変更前後とself-rehash比較、case alias、親/leaf逸脱。symlink作成不可は明示skipで、保証として数えない。既存公式validator合成正例を3Blender版で維持。

R12には共通台帳/CI改修を暗黙依存させない。Aの別作業候補は、開始HEADに存在するHandoff空行差の再生成と、Blenderのtests path filterを今後どう運用するかの判断。後者も本実験では変更しない。
