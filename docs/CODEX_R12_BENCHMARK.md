# CBDK Codex第2回開発実験 R12

実験専用資料。正本STATE・ABCD運用を置換しない。R12実験はユーザー承認済み、R13は候補のみ。

## 基点・安全境界・計測

- 開始UTC：`2026-11-08T00:35:22Z`。添付指示を取得した直後、リポジトリ調査・環境準備前の最初のclock実測値。添付取得に先行する正確な時刻は未計測であり補っていない。
- 開始dev：[`a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0)。#91未統合をAPI確認し、最新R11結合HEAD [`faab6ab023f50495c719d091b29f320aa6ab36df`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/faab6ab023f50495c719d091b29f320aa6ab36df) を全R12専門・結合の共通基点とした。
- 専門・結合PRのbaseは `work/v018-integration-r11-codex`。R11変更をPR差分へ重複させていない。レポートはdev基点docs-onlyの別PR。
- Codex単独、sub-agent不使用。C→D→Bの逐次編集と、独立したCI/API取得の並行実行。開始前にPython3.12.14/Blender4.3.2を実測。4.3.2は対象3版の代用にしない。
- R11のPR/ブランチ、dev/main、STATE/Handoff/PROGRESS/共通CI/Notionは未変更。既存ID/形式・役割・ライセンス/公開・私有データ境界を維持。正式マージ/リリースなし。
- GitHub PR created_at、commit committer.date、run/job APIを使用。「5系統全成功時刻」は最終head_sha・担当head_branchの各runがsuccessであることを確認した上でupdated_atの最大値を使う。結論確定の内部瞬間ではなく終了時刻代理値。
- queue代理値＝workflow created_at→job started_at、実行＝completed_at−started_at。前者にはrunner割当/依存待ちを含む。job合計は消費秒で並列経過秒と異なる。実装中にCIを進めたので工程時間を加算しない。
- 開始/領域着手は直接clock/UTCで記録。GitHubから取れるPR→greenを直接比較し、純粋実装時間・内部思考時間・費用/トークンは未計測。人間への追加確認/介入は0回。API・CI待ちと並行した実装の正確な時間分解は未計測。
- 各領域はローカル関連テストと文書をまとめてから1commit/1push。Blender path filterが新テストを対象にしないため、既存workflow_dispatchを各確定HEADに1回使用。共有CI変更なし。
- 過去比較の正本：[R11レポート最終HEAD](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/blob/4c2a25a78ed4a1c28806830de92ba4138d12a29c/docs/CODEX_R11_BENCHMARK.md)。R10のチャット開始は不明。難易度・作業量が異なるため、短縮を能力向上や特定手法の因果効果と断定しない。

## 最新R11確認とR12成果物

| R11 PR | 開始時/最終HEAD | branch | 状態・CI |
| --- | --- | --- | --- |
| [#88](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/88) | [`de2a5e12b15acb2b14281738619a4ef909db0117`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/de2a5e12b15acb2b14281738619a4ef909db0117) | `work/v018-glb-analysis-r11-codex` | draft/open/未統合、5系統success |
| [#89](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/89) | [`8ec215c97dd20e2cea2597589899b98904282eaf`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/8ec215c97dd20e2cea2597589899b98904282eaf) | `work/v018-ui-builder-r11-codex` | draft/open/未統合、5系統success |
| [#90](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/90) | [`a5bda5bc46c69fd936de73f7fb50350b2109b505`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a5bda5bc46c69fd936de73f7fb50350b2109b505) | `work/v018-extension-quality-r11-codex` | draft/open/未統合、5系統success |
| [#91](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/91) | [`faab6ab023f50495c719d091b29f320aa6ab36df`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/faab6ab023f50495c719d091b29f320aa6ab36df) | `work/v018-integration-r11-codex` | draft/open/未統合、5系統success |
| [#92](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/92) | [`4c2a25a78ed4a1c28806830de92ba4138d12a29c`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/4c2a25a78ed4a1c28806830de92ba4138d12a29c) | `work/v018-r11-codex-benchmark` | draft/open/未統合、3系統success |

R11の状態/ブランチに変更なし。R12専門はすべてR11結合HEADの直接の子。R11を自動統合していない。

| 領域 | branch / draft PR | 最終HEAD |
| --- | --- | --- |
| C | `work/v018-ui-builder-r12-codex` / [#93](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/93) | [`51e7b3b707e7dedbc699789f6bbc97a45d1c2ba8`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/51e7b3b707e7dedbc699789f6bbc97a45d1c2ba8) |
| D | `work/v018-extension-quality-r12-codex` / [#94](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/94) | [`6f96a7e7cd0d034dada4e950c850db6a250c551e`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/6f96a7e7cd0d034dada4e950c850db6a250c551e) |
| B | `work/v018-glb-analysis-r12-codex` / [#95](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/95) | [`315d29847c651642fbf10dc7417dda5448eeef7d`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/315d29847c651642fbf10dc7417dda5448eeef7d) |
| 統合 | `work/v018-integration-r12-codex` / [#96](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/96) | [`f222e20d01995489ed4612ec37230defe054fbd7`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/f222e20d01995489ed4612ec37230defe054fbd7) |

レポート：`work/v018-r12-codex-benchmark`、本書を含む独立draft PR。baseはdev、変更は本書のみ。report自身のCI/commitは開発比較から除外。[report branch commits](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commits/work/v018-r12-codex-benchmark)。

## UTC時刻・計測値

| 領域 | 直接記録した調査/実装着手 | 最初/最終の専門commit | PR作成 | 5系統全成功代理時刻 |
| --- | --- | --- | --- | --- |
| C | 2026-11-08T00:36:16.266783+00:00 | 2026-11-08T00:37:45Z | 2026-11-08T00:37:48Z | 2026-11-08T00:40:26Z |
| D | 2026-11-08T00:38:50.829599+00:00 | 2026-11-08T00:39:30Z | 2026-11-08T00:39:33Z | 2026-11-08T00:42:27Z |
| B | 2026-11-08T00:39:35.471659+00:00 | 2026-11-08T00:41:32Z | 2026-11-08T00:41:36Z | 2026-11-08T00:44:45Z |
| 統合 | 2026-11-08T00:42:04.240920+00:00 | 2026-11-08T00:42:04Z | 2026-11-08T00:42:11Z | 2026-11-08T00:45:23Z |

専門は各1commitなので最初/最終が同時。統合欄は最終merge commit、最初の専門commitではない。専門/結合の全commitは各PR commitsに保持。結合merge commitリンク：

- [a560ef92009fb46d130e113bed572a37c0517a36](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a560ef92009fb46d130e113bed572a37c0517a36) / 2026-11-08T00:42:04Z
- [8c6cf004cd7555c613003bbbef5baf515a872d95](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/8c6cf004cd7555c613003bbbef5baf515a872d95) / 2026-11-08T00:42:04Z
- [f222e20d01995489ed4612ec37230defe054fbd7](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/f222e20d01995489ed4612ec37230defe054fbd7) / 2026-11-08T00:42:04Z

### R10 / R11 / R12比較

R10/R11値は#92上の正本レポートのUTCから同基準で再計算。開始clock指標はCodex側直接記録の参考値、GitHub PR基準は直接比較可能。

| 指標 | ABCD R10 | Codex R11 | Codex R12 |
| --- | ---: | ---: | ---: |
| 開始→最初commit（直接clock/参考） | 不明 | 3分45秒 | 2分23秒 |
| B PR→専門全CI成功 | 3分05秒 | 5分14秒 | 3分09秒 |
| C PR→専門全CI成功 | 2分51秒 | 3分47秒 | 2分38秒 |
| D PR→専門全CI成功 | 2分48秒 | 6分04秒 | 2分54秒 |
| 最初専門PR→3専門成功 | 3分35秒 | 10分09秒 | 6分57秒 |
| 3専門成功→結合CI成功 | 8分19秒 | 2分04秒 | 0分38秒 |
| 最初専門PR→結合CI成功 | 11分54秒 | 12分13秒 | 7分35秒 |
| 統合PR作成→結合CI成功 | 3分15秒 | 6分32秒 | 3分12秒 |
| 開始→結合CI成功（直接clock/参考） | 不明 | 16分01秒 | 10分01秒 |
| 候補作成checkpoint→結合CI成功 | 3分20秒 | 7分52秒 | 3分18秒 |

R11→R12：開始→結合ゲートは 16分01秒→10分01秒（差 +360秒）、最初専門→3専門は10分09秒→6分57秒（差 +192秒）、最初専門→結合は12分13秒→7分35秒（差 +278秒）。差の正値は短縮、負値は悪化。
開発検証終了UTC（全ゲート成立代理）：`2026-11-08T00:45:23Z`。レポート集計cutoff：`2026-11-08T00:48:15.831476+00:00`。レポート編集/自身CIは別工程。

### 品質・実行量・効率を含む比較

| 項目 | R10 | R11 | R12 |
| --- | --- | --- | --- |
| 専門/結合指定5系統 | 3専門+1結合成功 | 同左 | 下記exactHEAD 20workflowで確認 |
| 新規Python method | 今回独立計数せず | 10 | 12 |
| 結合Python発見数 | 過去記録参照、再実行なし | 1,064 | 1,076（Linuxは2skip、Windowsは実測別記） |
| native新規marker | R10固有5 | R11固有4 | R12固有4、既存保持 |
| 担当変更ファイル | 12/重複0 | 7/重複0 | 7/重複0、blob全一致、583追加行 |
| 製品変更 | 適応AABB/台帳回復等あり | なし | なし |
| 初期失敗/手戻り | チャット上は不明 | B文書版/C native/D Windows fixture修正 | push前B trace校正1、CIは履歴表参照 |
| 人間への追加介入 | GitHubだけでは不明 | 細粒度時刻は未計測 | 0回 |

改善の観測：環境版確認→fixture前提検査→ローカルnative成功→文書込み1pushを守り、R11の版誤記/C detach矛盾/D root未正規化は回避。C native CIを先行させD/B実装と重ねた。専門成功の全待ちではなく、安定した専門HEADで早期結合も開始。
一方、課題の違い・runner負荷/queue・ローカル全体37.345秒 vs R11 54.481秒などの環境変動を分離できない。全ての短縮を手順変更の因果効果とはしない。本体性能最適化やCodex能力向上の証明でもない。
ABCDは独立領域の並列実装とAのレビュー分担に強み。Codex単独は同じ担当境界でfixture/CIを一貫して追跡できるが、専門実装は逐次。両方式でexactHEAD結合ゲートと人間承認を維持する。

## exactHEAD CI・queue/job実測

| PR | 系統 / run | 結論 | queue代理最小–最大秒 | job秒 合計/最長 | 最後のjob終了UTC |
| --- | --- | --- | ---: | ---: | --- |
| #93 | [Blender×3 42430620650](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430620650) | success | 4–4 | 372/151 | 2026-11-08T00:40:26Z |
| #93 | [Python×3 42430622186](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430622186) | success | 3–4 | 100/41 | 2026-11-08T00:38:37Z |
| #93 | [Windows×2 42430622134](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430622134) | success | 4–6 | 144/77 | 2026-11-08T00:39:15Z |
| #93 | [Handoff 42430622279](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430622279) | success | 4–4 | 8/8 | 2026-11-08T00:38:04Z |
| #93 | [Chromium 42430622226](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430622226) | success | 4–4 | 34/34 | 2026-11-08T00:38:30Z |
| #94 | [Blender×3 42430750711](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430750711) | success | 3–4 | 406/167 | 2026-11-08T00:42:26Z |
| #94 | [Python×3 42430752670](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752670) | success | 3–3 | 111/51 | 2026-11-08T00:40:30Z |
| #94 | [Windows×2 42430752699](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752699) | success | 3–4 | 150/77 | 2026-11-08T00:40:57Z |
| #94 | [Handoff 42430752707](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752707) | success | 4–4 | 7/7 | 2026-11-08T00:39:47Z |
| #94 | [Chromium 42430752676](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752676) | success | 4–4 | 35/35 | 2026-11-08T00:40:15Z |
| #95 | [Blender×3 42430912520](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430912520) | success | 4–4 | 502/182 | 2026-11-08T00:44:44Z |
| #95 | [Python×3 42430913755](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430913755) | success | 3–4 | 121/46 | 2026-11-08T00:42:28Z |
| #95 | [Windows×2 42430913696](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430913696) | success | 3–3 | 129/66 | 2026-11-08T00:42:48Z |
| #95 | [Handoff 42430913832](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430913832) | success | 4–4 | 6/6 | 2026-11-08T00:41:49Z |
| #95 | [Chromium 42430913709](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430913709) | success | 3–3 | 38/38 | 2026-11-08T00:42:20Z |
| #96 | [Blender×3 42430958786](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430958786) | success | 4–4 | 456/184 | 2026-11-08T00:45:22Z |
| #96 | [Python×3 42430960577](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960577) | success | 3–4 | 126/48 | 2026-11-08T00:43:07Z |
| #96 | [Windows×2 42430960588](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960588) | success | 3–4 | 134/68 | 2026-11-08T00:43:26Z |
| #96 | [Handoff 42430960387](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960387) | success | 3–3 | 7/7 | 2026-11-08T00:42:25Z |
| #96 | [Chromium 42430960498](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960498) | success | 4–4 | 28/28 | 2026-11-08T00:42:47Z |

job版matrixはPython3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1。5workflow＝10非skip jobs/PR、指定4PRで20workflow/40非skip jobs。handoff sync-mainの条件skipは除外。Blenderはdispatch、その他PR event。

| PR | 可視run数 | failure | cancelled | 同run再試行 | 専門commit数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| #93 | 5 | 0 | 0 | 0 | 1 |
| #94 | 5 | 0 | 0 | 0 | 1 |
| #95 | 5 | 0 | 0 | 0 | 1 |
| #96 | 5 | 0 | 0 | 0 | 3専門+3merge |

履歴はPRに含まれるcommitと当該head_branchを照合、別branchの同一SHA runを混ぜない。run API各100件、可視範囲のみ。report-only CIは除外。再試行/修正に追加されたCI時間はrun/jobから確認、失敗なしなら失敗修正CI秒0。ローカルB校正の純粋編集秒は未計測。

### 実ログのnativeとskip確認


[#94 Python×3 log](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752670)：

- unittest (3.13): Ran 1070 tests in 28.062s
- unittest (3.13): OK (skipped=2)
- unittest (3.12): Ran 1070 tests in 46.032s
- unittest (3.12): OK (skipped=2)
- unittest (3.11): Ran 1070 tests in 20.821s
- unittest (3.11): OK (skipped=2)


[#94 Windows×2 log](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430752699)：

- powershell-unittest (3.11): Ran 1070 tests in 53.620s
- powershell-unittest (3.11): OK
- powershell-unittest (3.13): Ran 1070 tests in 46.682s
- powershell-unittest (3.13): OK


[#96 Python×3 log](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960577)：

- unittest (3.13): Ran 1076 tests in 24.038s
- unittest (3.13): OK (skipped=2)
- unittest (3.12): Ran 1076 tests in 41.968s
- unittest (3.12): OK (skipped=2)
- unittest (3.11): Ran 1076 tests in 41.373s
- unittest (3.11): OK (skipped=2)


[#96 Windows×2 log](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42430960588)：

- powershell-unittest (3.11): Ran 1076 tests in 48.575s
- powershell-unittest (3.11): OK
- powershell-unittest (3.13): Ran 1076 tests in 46.785s
- powershell-unittest (3.13): OK

| Blender | R12 | R11 | headless | WindowsGUI |
| --- | ---: | ---: | --- | --- |
| 4.4.3 | 4 | 4 | True | False |
| 4.5.15 LTS | 4 | 4 | True | False |
| 5.2.1 LTS | 4 | 4 | True | False |
WindowsがOK（skipped表示なし）なら6新規D methodすべてが実行済み。LinuxのWindows専用2skipはWindows実証へ算入しない。新nativeもmarkerのstatic存在だけではなく各target実ログを確認する。

### B Python3版の実測

| Python | excludes | R8 ms / peak B | adaptive ms / peak B | R2 ms / peak B |
| --- | --- | --- | --- | --- |
| 3.13 | 7 | 1.312 / 39392 | 1.545 / 37888 | 1.517 / 39368 |
| 3.13 | 8 | 1.325 / 39392 | 1.309 / 37888 | 1.529 / 39368 |
| 3.12 | 7 | 1.238 / 39368 | 1.274 / 37880 | 1.193 / 39344 |
| 3.12 | 8 | 1.242 / 39368 | 1.236 / 37880 | 1.218 / 39344 |
| 3.11 | 7 | 0.748 / 39360 | 0.776 / 37880 | 0.740 / 39336 |
| 3.11 | 8 | 0.720 / 39360 | 0.718 / 37880 | 0.730 / 39336 |

5 warmed samplesの中央値、trace無効。heapはPython traced allocationsでRSSではない。投影回数は7除外時174/381/388、8除外時171/171/388（R8/adaptive/R2）、既知6投影で別校正。意味の変化なし、反復一般利得なしで本体変更なし。

## blob一致と未統合ファイル一覧

| 担当 | R12変更path | 専門=結合のblob SHA |
| --- | --- | --- |
| B | `docs/GLB_R12_PROBE_WORK.md` | `69af5729ec1974bf981c280f893bfbff6b2d58bb` |
| B | `tests/test_glb_match_probe_r12.py` | `e64621f6143636ae821aac234fd42f8e7e7afbca` |
| C | `docs/UI_R12_DISABLE_RECOVERY.md` | `085c5eedc9383a1a98a44bd38a8bab2dc74f32b5` |
| C | `tests/blender_ui_lifecycle_r5.py` | `721ef05d848b68f5d6a383437d69872c4c31dc46` |
| C | `tests/test_ui_lifecycle_r12.py` | `14a7ae05bbe2171621e6526fea7745126ceead5b` |
| D | `docs/EXTENSION_R12_REFERENCE_BASIS.md` | `9f9d15a9129cc99f6e634f8ec7981fcecf153121` |
| D | `tests/test_extension_source_reference_round12.py` | `48d532774ee8b61d4af8c1d343041ca98df99a31` |

R12結合差分は上記7pathだけ。report branch差分は `docs/CODEX_R12_BENCHMARK.md` だけ。R11で追加されたpathの内容をR12差分へ重複採用していない（既存C scriptのR12追加は意図した新差分）。

終了照合dev HEAD：[`a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0`](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/commit/a0aa25eae608494eab4f2eb02d7aefd1bd4d40a0)。R11結合HEADも開始と同じ、全R11/R12 PRは未統合。本流post-merge7CI/Kit/Skillは今回候補上で未実行。report-only発火CIは別PRのchecksで確認。

再取得：`gh api repos/mibesamiti-png/Chappy-Blender-DevKit/pulls/96`、`actions/runs?head_sha=<exact>&per_page=100`、各runの`jobs?per_page=100`。R11正本#92との比較は本書に列挙した共通基準だけを用いる。

## 実装・検証成果と未検証

| 領域 | R12成果 | 限界 |
| --- | --- | --- |
| B / NEXT-008 | 固定seed0/1/17/2026順列、実first64の除外7/8閾値、後半密度反転。R2非退化投影評価回数をtest-only traceで計測。別のuntraced中央値/heap測定。float32 face順序/予算の全辞書R8/R2一致、独立R3維持 | 製品の意味的不具合・一貫した性能利得なし、本体変更0。元R2 modeは既存no-rejection wrapperであり歴史的source checkoutの速度再生ではない |
| C / UI-001・BUILD-001 | class-only/Scene-only/同時失敗×foreign有無×Scene2属性の12nativeケース。2回目disable、reload/再enable拒否、enabled flagとpending台帳不一致、元参照での明示cleanup→再有効化 | 再enable失敗でBlenderがsys.modulesを除去することを観測。元module参照を保持する明示回復手順を検証、自動修復は追加しない。GUI/第三者実共存は未保証 |
| D / EXT-001 | test-only snapshot基点commit/inventory digest/改行方針。基準不明・相違はinconclusive。正規化root、unknown/allowlist/case、CRLF、親/leaf symlink・Windows junction・8.3/root caseのnative filesystem検証 | bytes差だけで合法更新と改変を識別しない。参照一致も真正性・作者同意・SPDX・公式検証・公開承認ではない。OS権限不足はskip |

新規Python test method数：B4+C2+D6＝12。新nativeマーカー4項目（Cの実経路）。R5–R11マーカー、5機能/6レシピ、ZIP7正例/16MiB/2MiB/64member、レビュー専用false flagsを保持。
担当差分7ファイル・583行追加、本体変更0、重複ファイル0、結合競合0。統合候補は専門3領域以外の変更なし。
既存44要件（実装26/一部16/未実装1/保留1）、NEXT24（完了18/継続5/保留1）の正本は変更せず、R12検証を理由に完了へ昇格していない。

### ローカル結果

- C：新規2件・関連46件成功。Blender4.3.2で12ケースと4 native_r12_*が初回成功。
- D：新規6件中4成功/Windows専用2skip。関連18件も2skip。fixture rootは作成時からresolveし、R11のWindows失敗要因を避けた。
- B：4件成功。trace初案は複数行factor文のline eventを重複カウントしたため、push前に単一行norm2分岐へ移し、既知6投影ケースで校正。廃棄した初期値を結果に含めない。traceを時間計測に混ぜずfinallyで復元。
- 結合：Python3.12.14、1,076件発見、1,074成功/2 Windows-only skip、37.345秒。登録監査static_checks_passed、5機能/6レシピ。
- STATE --validate成功。tracked Handoff --checkは開始時からの空行7行差で失敗、非空行本文は生成結果と一致。共有文書を変更せずAへ引き継ぐ。CIの--write後--check成功とtrackedファイル一致を混同しない。

R11のC foreign-preservation後のdetach検査矛盾は再発なし。D未正規化root失敗は再発なし。Python版の文書取り違えもなし。
Bのtrace初案校正はpush前の手戻り1件として計上し、「手戻り0」とはしない。製品欠陥は未再現。
私有GLB/未承認addon/Windows GUI/Ctrl+Z/実第三者addon/権利・正式Extensions・公開・本流post-merge7CIは未実施/未承認のまま。

## ABCD方式へ戻す手順とAの確認事項

1. 下記のR11/R12 base・head・draft/未マージ状態を再取得。R11 #91を先にレビューし、R12 #96はその上の差分としてレビューする。R11 #88–#90、R12 #93–#95を結合候補と重複採用しない。古いR10専門PRも再マージしない。
2. R11→R12の順に、各結合候補か専門成果を一度だけ取り込む。user追加指示/Aレビュー前に本流へマージしない。スタックbaseを勝手に変更/rebase/force pushしない。R11統合状態が変わったらAが基点/差分を判断し、必要な新候補でCIを行う。
3. 下記blob表で専門→結合の完全一致、担当専用パス、最終HEADのPython3/Windows2/Blender3/Chromium/Handoffを照合。Blenderログでnative_r12四項目とR11四項目を各版確認。Windows skip数と未実行を区別。
4. Aが必要な承認を得て統合後、別の本流7CIを実行（今回は禁止指示につき未実行）。STATEへR11/R12限定達成・exactSHA/CI/未確認を記録、Handoffを自動再生成して--check、PROGRESS更新、既存Notionへ安全な要約を節目同期する。本実験は更新案のみでNotion同期なし。
5. レポートPRはコード候補と独立採否。dev基点docs-onlyでコードのstackを混ぜていない。ABCD役割と所有権は既存のまま、Codex独自状態管理へ移行しない。
6. 次世代計画の承認は保持するが、v0.18自動化残作業と人間ブロッカー/PR25方針のゲートを省略しない。R13候補は以下、正式割当まで実装禁止。

## R13候補 — PROPOSED / NOT ASSIGNED / NOT STARTED

### B / P2：計測の順序偏りと閾値周辺を広げる

- 目的：R12の7/8単一構成に対する演算回数差を、一般的速度改善と混同しない。
- 内容：同一の安全なsegment集合でseed数・密度反転位置・6–9除外を拡張。untraced paired測定の実行順を回転し、traceを独立校正。利益なしならtests/docsのみ。
- 対象：B専用GLB tests/docs、欠陥または反復利得がある時だけcbdk/glb_part_match.py。
- 受け入れ：全辞書R2/R8一致、R3独立、既存予算/false flags保持。Python3版の中央値/ばらつき/heapと投影回数を別記し、trace overheadを速度に含めない。
- テスト：seed permutation、float32/ゼロ長/境界予算/接触、投影回数既知ケース。ユーザーGLB不要。

### C / P1：failed re-enable後の元参照喪失リスクを明示

- 目的：Blenderが失敗moduleをsys.modulesから除いた状態で、新規importが古いpending ledgerを隠す危険を検証する。
- 内容：CBDK自作fixtureのみで、旧module参照保持/新module生成の差とclass衝突・Scene ownershipを制御検証。明示回復の必要な情報/診断案をレビューし、自動採用/再import/foreign削除は追加しない。
- 対象：C native lifecycle/Python tests/docs、製品修正は欠陥再現時だけtemplate最小範囲。
- 受け入れ：3版でnative_r13実行、元所有クラスの漏れ0を明示cleanupで確認、foreign保全、R5–R12/5機能6レシピ保持。module見失いを回復成功と表示しない。
- テスト：class/Scene/両失敗、複数残存entry、2回disable、失敗enable後のsys.modules/台帳、GUI保証と分離。

### D / P2：参照基点の整合とWindows aliasの追加負例

- 目的：test-only basisと参照bytesが変化した時に、比較可能/不確定を明確にする。
- 内容：同じcommit名でinventoryが異なる、read前後にsnapshotが変わる、内部junction/leaf aliasの境界を合成checkoutで検証。未知基点はinconclusive、self-declared commitで権利を認めない。
- 対象：D専用source-reference tests/docs。新public trust APIや共有CI変更を暗黙依存にしない。
- 受け入れ：許可外読取0、基準相違で偽のsame判定なし、値/path/PII漏洩0、7正例/ZIP予算/全権限false維持。
- テスト：Python3版/Windows2版、case/8.3/junction/parent+leaf symlink、CRLF/LF、OS capability skipを明記。

R13に追加の実行許可は与えていない。Aの別管理作業はHandoff再生成と既存Blender path-filter運用判断。今回共有CIには触れない。
