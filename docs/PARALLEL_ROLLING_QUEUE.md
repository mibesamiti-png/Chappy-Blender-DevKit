# CBDK 並行開発 — 先読みキュー（A司令塔管理）

**目的:** B・C・Dが現ラウンドを実装している間に、Aが次の仕事を用意する。Codex上限でも進行可能。仕様は暫定で、GitHubの現在のPR・CI・最新STATEが常に優先。

## 現在の作業とゲート（2026-11-08 JST初版）

- 基点: `work/v018-integration-bcd`、SHA `e445b12c9a66541ba13bfb10ee6bc0007078c24b`。初回統合候補 [PR #29](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/29) はドラフト未マージ。
- **B：R2** `work/v018-glb-analysis-r2`、[PR #31](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/31)。境界エッジ数が同数でも穴の位置が違う合成GLBの対応判定。HEAD・CIは変わり得る。redならR2修正優先。
- **C：R2** `work/v018-ui-builder-r2`。誤有効のUIと登録/解除失敗復旧。PRの有無・HEAD・CIを開始時に再確認。
- **D：R2** `work/v018-extension-quality-r2`、[PR #30](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/30)。連結ZIP/ローカルヘッダー/extra/comment/provenance。TDD red phaseは想定内でも**完了とはみなさず**、最終の修正/成功まで担当を維持。
- Aは各PR出現時に差分とCIを先行レビューし、必要なら独立 `work/v018-integration-r2` で緑の変更だけ先行検証。B/C/Dの開発を全員停止させて統合する必要はない。
- 個別ブランチへのコミット/PR/CIの状態は変化する。**記載したPRを完成済みと自動判定しない**。

## 先読み済み：R3候補（R2がgreenになった担当から）

次の仕事は**1つだけ小さく選ぶ**。R2のテストが赤い間は新しいコード修正ではなく、R3負例の**読み取り専用設計**まで。R2成功時に、GitHubの現状と担当パスを再確認する。

### B / NEXT-008：輪郭の違いを追加負例で測る

- **目的:** 現行R2の境界レイアウト比較が、対称配置、穴の連結成分、細い切れ込み、再三角分割、スケール違いで不必要に同一判定/誤警告を出さないか検証し、最も重要な1種の見逃しに保守的な対応をする。
- 先行成果: 自作GLBの正常/負例の表、現行R2の `suggested/ambiguous` と処理コスト。根拠なく「同じ輪郭=同じ部品」と判定しない。
- 編集可: `cbdk/glb_*`、GLB専有テスト/fixture/文書。現行R2を壊さず必要最小差分。新パフォーマンス計測は予算/上限付き。
- 新ブランチ候補: `work/v018-glb-analysis-r3`。R2 green後に **R2 HEADから分岐し、PR baseはR2ブランチ**。

### C / UI-001・BUILD-001：失敗復旧とモード切替の反復回帰

- **目的:** 現行R2で修正した読み取り専用のUI readiness判定が、再登録、mode切替、複数回の解除/再登録と、Sceneの他アドオン保有プロパティに対して誤って成功を表示・破壊しないか調べ、明確な負例を最小修正。
- 先行成果: CBDK自作previewの反復登録/解除と foreign property 保護テスト。合成inject failureは本物のOOM/Windows GUIテストではないことを明記。
- 編集可: UI-owned `cbdk/ui_layout.py`, `templates/modular_preview/`, UI固有テスト/文書。共通 `scripts/blender_modular_addon_smoke.py` はAへ変更要求だけ。既存5機能・6レシピ維持。
- 新ブランチ候補: `work/v018-ui-builder-r3`。R2 green後にR2 HEADから、ドラフトPR baseはR2ブランチ。

### D / EXT-001：manifest・公式validatorログの誤分類防止

- **目的:** R2のZIP構造安全性とは別の **manifest/official validator観測** の未知/重複/矛盾したログが `complete_diagnostic_agreement=true` に誤昇格しないか、Blender 4.4.3・4.5.15・5.2.1の**合成データ**で比較する。
- 先行成果: 有効な公式ログと拒否すべき合成ログを別々に保存（秘密/パス/自由入力値は記録しない）。R2の正常legacy/modular ZIPを拒否しない。
- 編集可: `cbdk/extension_*`、Extensions専用Pythonテスト/文書。共通 `scripts/verify_extension_manifest.py`、CI YAML、STATE/HANDOFF/NotionはA管理。
- 新ブランチ候補: `work/v018-extension-quality-r3`。R2 green後にR2 HEADから、ドラフトPR baseはR2ブランチ。

## Aの仕事を常に先回りで進める

1. 少なくとも各チームに「今の仕事＋次の仕事」が1件ずつあることを維持する（ただし次の仕事は未承認/未着手でもよい）。
2. PRが提出されるたびにファイル差分・head SHA・CI・依存先を確認し、全員の完了を待たずレビューを開始。
3. CIが赤い理由をTDD意図・回帰失敗・環境不良に分類。意図的なredを不正にmergeしない。
4. 安全なgreenの成果だけ独立統合候補に反映して、結合後のCIを実測。元ブランチ/PRの履歴を勝手に書き換えない。
5. 次のキュー項目を先に更新。R3からR4への指示もR3が進行している間に用意。
6. Codexが利用可能なら複雑な独立問題だけを割り当て、利用不可でも工程を止めない。

## 作業チャット共通の継続指示（次ターンにそのまま使う）

> 現在の担当PRの実装・失敗修正・必要CIを完了し、HEAD SHA/未検証を記録してください。完了後は `docs/PARALLEL_ROLLING_QUEUE.md` の自チームの次の項目を読み、**現在PRがgreenかつ担当境界と依存が明確な場合だけ**、現在PR HEADからR3専用ブランチを作り、R2ブランチ宛てのスタックされたドラフトPRを提出してください。green未達なら現在PRの修正を優先し、R3は設計のみ。Codex不要、共有STATE/Notion/mainや他担当ファイルを変更せず、実際のテスト結果と未確認を必ず分けること。

このキューをもとにAは次サイクルで実測や優先度を更新する。手順の正本は[PARALLEL_DEVELOPMENT.md](PARALLEL_DEVELOPMENT.md)。


## 更新 2026-11-08 JST — R2統合検証とR3実装進捗

- [R2統合PR #33](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/33): `23f002eafa86b431cbf379990f09b8d165d9eb18`、各R2の12変更ファイルを含む結合コードで**Python・Windows・Blender3版・Chromium・handoffの5系統成功**。個別PR #30/#31/#32は引き続きドラフト・未マージ。
- [Aの最新版開発ブランチ向け統合候補PR #37](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/37): 初回R1とR2の累積21ファイルを最新のv0.18ドキュメント/スキル正本に合成。候補SHA `3dde041a8a487a59714fc1cff34cb2d6dc6f16c1`。**この候補自身の全CI結果を別途確認すること**。旧コードとR1/R2の合格は新SHAの検証を代替しない。
- [D R3 PR #34](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/34): validatorの未知/矛盾/重複ログを保守的に拒否。新規テスト後のCIを確認し、redなら修正優先。
- [B R3 PR #35](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/35): 同数境界の接触/非接触コンポーネント差異。レビュー専用、構造の真の同一性は未証明。
- [C R3 PR #36](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/36): foreign Sceneプロパティ保護、UIモード切替、登録解除反復の負例。
- R3はすべてR2への**スタックされたドラフトPR**であり、この段階ですでに各担当の追加PR上限1件を使用。**Aがスタックを解消し、次の基点とPR baseを再指定するまでは、R4の新ブランチ/PRを作らないこと。** B/C/Dは以下のR4を設計・調査するだけなら進行可。

## 先読み済み：R4候補（設計のみ・着手ゲートあり）

### B / NEXT-008：境界部品対応の計算予算と実用性

- **現行R3を尊重:** 境界グラフの connected-components 値は局所的なレビュー信号で、部品の同一性/穴の物理的存在を証明しない。
- **候補:** 自作合成GLBの複数部品で、256辺上限・512面上限・微小隙間・再三角化・相似スケールの組合せを設計し、時間・メモリ予算超過を安全に ambiguous とすることを確認。既に検出済みの差分に新しい理由コードを増やさない。
- **受け入れ条件:** R3の判定を壊さず、負例/正例/上限超過の再現可能な入力と処理コストを記録。1つでも実際の見逃しが再現した場合のみ最小修正。新しい座標・実データの公開は禁止。
- **所有:** `cbdk/glb_*`、GLB専用テスト/合成fixture/専用文書。共有CLI、CI、STATEはA管理。

### C / UI-001・BUILD-001：生成UI宣言と実動作の整合

- **現行R3を尊重:** foreign property 保護・mode snapshot・register/unregister失敗復旧を維持。助言UIと実operator成功を混同しない。
- **候補:** 既存5機能/6レシピの declarative UI plan → 生成プレビュー → 実Blender実行で、無効コンテキスト時の disabled 理由と実operatorの拒否結果が矛盾しないか調査。あわせて登録と解除を反復して他アドオン保有プロパティを破壊しないことを確認。
- **受け入れ条件:** 既存5機能/6レシピを維持し、空mesh/複数data/mode変更/失敗注入の各負例が通る。headless Blenderは人間のWindows GUI操作確認ではない。
- **所有:** `cbdk/ui_layout.py`、`cbdk/modular_builder.py`、`templates/modular_preview/`、UI専用テスト/文書。共通 `scripts/blender_modular_addon_smoke.py` の追加はAに依頼（勝手に編集しない）。

### D / EXT-001：安全診断の互換性と正常入力の維持

- **現行R3を尊重:** 公式validatorログの未知/矛盾は未分類として安全側に倒す。Blender版ごとの無害な行だけを許可し、入力値・パス・秘匿キーをレポートに出さない。
- **候補:** legacy/modularの有効な自作ZIP、問題のない合成manifest/officialログを使った正例を追加し、R2の構造拒否とR3の未知ログ拒否が**正常プレビューを誤って拒否しないか**を優先的に確認する。
- **受け入れ条件:** 壊れたZIP/未知ログはfail-closed、有効入力は従来の`blocked_for_extension_release`（公開準備未完了）を維持。実部品ライセンスや真正性を自動承認しない。
- **所有:** `cbdk/extension_*`、Extensions専用テスト/文書。共有公式validator fixtureスクリプトはAに変更要求だけ。

### 司令塔Aの並行タスク

1. PR #37の全CIと21ファイル累積差分を照合し、開発本流への統合可否を別途判断。個別PR #26〜32の**二重取り込みはしない**。
2. R3 (#34/#35/#36) は**各PRの厳密なHEAD SHA**でCIを確認し、赤い状態が解消されたら独立したR3結合候補で検証。#37の固定基点や専門R2/R3を無断force-pushしない。
3. その後、スタックされたR3の統合方式を確定し、R4を編集可能にする新基点SHAを通知。**上記R4はAの通知までは設計のみ**。
4. v0.18の未検証GUI/実ユーザーGLB/ライセンス/正式Extensions、v0.19以降の未有効条件を維持。Codexが上限でもこの運用は止めない。


## 2026-11-08 JST — A統合完了・R4実装への切替指示（旧ゲートより本節優先）

- AがR1〜R3の開発コードを統合：**[PR #38](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/38) merged**、開発コードSHA `12ddcfeef935a805f7316ffb3698c141328aac88`。このコミットの7CI系統（Python897件×3版、Windows、Blender3版、Kit、Chromium、Skill、Handoff）は全成功。正式`main`やv0.17.0リリースは変えていない。
- **R4新基点**: `feature/v0.18-shape-diagnostics` の**着手時点の最新HEAD**を確認し、`12ddcfeef935a805f7316ffb3698c141328aac88` が祖先であることを確認する。正本更新のため、後続のdocs-onlyコミットが増えてもその最新HEADから分岐する。古い統合実験 `work/v018-integration-bcd` やR2/R3専用ブランチからR4を始めない。
- R4ブランチ: B `work/v018-glb-analysis-r4`、C `work/v018-ui-builder-r4`、D `work/v018-extension-quality-r4`。それぞれ **base `feature/v0.18-shape-diagnostics` のドラフトPR**。追加R4 PRは1担当につき1件、担当外ファイルを編集しない。
- **旧PR #26〜37はPR #38によってコード内容が統合済みの履歴資料**。勝手に二重merge/force-push/closeしない。旧スタックを新規R4作業の基点にはしない。Aの明示的な新基点割り当てにより、旧R3の「追加1件」は新サイクルへ持ち越さない。
- R4の具体的なB/C/Dタスクと負例・受け入れ条件は直前の「先読み済み：R4候補（設計のみ）」節を使用。本節により**設計のみの制限を解除**する。ただし実装時は最新`STATE.json`/担当パス/PR依存を読み直し、未検証の実データ・GUI・ライセンスを自動で完了扱いしない。
- Codexが利用不可でも専門チームの小実装とPython/Blender/Windows CIを続ける。共通STATE/HANDOFF/Notion/共通CI、`main`、正式公開はA/所有者の別ゲート。


## 2026-11-08 JST — A R4統合結果・R5割当（post-merge CIゲート付き）

**R4統合記録:** AがB [#41](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/41) HEAD `e94febeb557be52474d5c17a08271d164cbef2d6`、C [#42](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/42) HEAD `ae6ad0b77feafc5db052eb658538adf5ec50691d`、D [#39](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/39) HEAD `f0fa73531ad3892040f5f01a64cb110fdb80e6b8` の各5系統CI成功を確認。11ファイルはチーム間で重複0。A統合候補 [#43](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/43) HEAD `667f2e4c9e4ad4b4e2b026c7fe1fd2464d2ca957` のPython3版、Windows2版、Blender3版、Chromium、Handoffの**5系統すべて成功**を確認した上で、v0.18開発ブランチにsquash merge済み。**統合コミットSHA: `a9a0a76a963ab4ae41b68126f419546b80871e2b`。** `main`、公開版v0.17.0、旧PR #26〜42は変更しない。

**重要な追加ゲート:** 上記CIはPR #43の結合HEADでの実測。squash統合後SHA `a9a0a76...` に対する7系統（Python、Windows、Blender3版、Chromium、Handoff、Kit、Skill）の**別のpush CIが成功したことをAが確認した時だけ**、下記R5着手許可を有効化する。これが未確認・赤の場合、B/C/DはR5設計/fixture調査のみ。Aは不足ジョブを確認し失敗を修正する。

### R5担当と受け入れ条件（#40の設計を正式キュー化する候補）

- **B / NEXT-008:** 既存の256境界・512面上限前後、面/部品順序入替と微小座標摂動で、判定の決定性・予算超過時の安全な`ambiguous`を検証。まず合成負例を再現し、再現した場合だけ最小修正。許可: `cbdk/glb_*`、GLB専用テスト/fixture/文書。共通スクリプト・STATE・CIはA所有。実GLB同一性・物理穴の証明は禁止。
- **C / UI-001・BUILD-001:** 生成previewの登録→mode変更→operator拒否→解除→再登録の反復と、foreign Scene property維持をBlender実機で追加観測。Python mockと実Blender/GUIを区別し、既存5機能/6レシピを維持。許可: `cbdk/ui_layout.py`、`cbdk/modular_builder.py`、`templates/modular_preview/`、UI専用テスト/文書。共通 `scripts/blender_modular_addon_smoke.py` の更新はAへの変更要求（直接編集しない）。
- **D / EXT-001:** R4の正常ZIP正例を保持しつつ、公式Blender 3版の既知validator出力と未知/矛盾ログの安定した区別・サニタイズの回帰を拡充。観測された誤分類がなければ製品コードに変更を加えない。許可: `cbdk/extension_*`、Extensions専用テスト/文書。共有validator/CIはA所有。正式Extensionの配布/権利承認なし。

### R5作業ゲート・ブランチ指示

1. Aが最新GitHubの `feature/v0.18-shape-diagnostics` HEADと、`a9a0a76a963ab4ae41b68126f419546b80871e2b` が祖先であることを確認。Aのdocs-only更新が後続にある場合は**新しい最新HEAD**を起点にする。旧R2/R3/R4のHEADから分岐しない。
2. post-mergeの実行済み7系統CIが成功し、各担当のR4 PRがgreenであることを確認後に着手。R5案は各担当1タスクだけ、追加未統合PR上限1件、Codex不要。
3. B: `work/v018-glb-analysis-r5`、C: `work/v018-ui-builder-r5`、D: `work/v018-extension-quality-r5`。いずれも新しい開発HEADから作成、ドラフトPRのbaseは `feature/v0.18-shape-diagnostics`。依存を跨ぐファイル変更/共有スモークはAに報告。
4. Python3版/Windows2版/Blender3版・Chromium・Handoff、および変更内容に必要なKit/Skillを**各R5厳密HEADで**実測し、失敗/中止/未実行を明確に分ける。合成fixture、実GUI、私有GLB、権利、公開に関する未検証を保持。
5. AはB/C/D稼働中にR6負例/受け入れ条件を先読みで設計し、R5 PRの差分・CIを先行レビュー。R5はv0.18開発ブランチ内のみであり、mainマージやv0.19有効化を意味しない。


## 2026-11-08 JST — R5統合完了・R6ローリング正式割当（post-merge CI確認後に実装可）

- **R5実装統合:** B [#47](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/47) `0d388155bf5c10e6dc76b1c73b51dc7d04adfc80`、C [#48](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/48) `c56b64178798796e5c1e8bbb9e4f57ccf09bb95e`、D [#46](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/46) `a86ebdb74dfb099398dd96fe8a5c03de99465a25`。各独立5系統CI全成功、専門領域9ファイルの重複0。
- A統合 [PR #49](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/49)：A所有Blender CIにCの新しい実機R5ライフサイクル検証を追加。**初回統合HEAD `b300e74356848ffbd9131c2c0d651991f7c10cbf` はBlender3版で失敗**（パネルの無効ボタンが非表示になるというテスト誤認）。実際は無効表示なのでテストのみ修正。**修正HEAD `106bf2504923346ac4cd25b51ebaaa87da9e7d7b` に対するPython/Windows/Chromium/Handoff/Blender3版の5系統すべて成功**。各Blender版で新設 `CBDK_R5_UI_LIFECYCLE_PASS` を確認し、R5をv0.18開発ブランチへsquashマージ。**統合コードSHA `a1c2f84715acce1f8cd33abaf003556708c13c07`**。旧R1〜R4 PR再取り込み禁止、main/正式v0.17.0変更なし。
- **R6実装許可の追加ゲート:** 上記統合後コードSHA `a1c2f847...` で、独立したpush CI **7系統**（Python3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1、Chromium、Handoff、Kit、Skill）がすべて実行完了・successしたことをAが確認した場合にだけR6着手可能。それ以前やCI赤の場合はR6設計・レビューのみ。PR #49の5系統成功を統合後7系統の代替にしない。

### R6担当タスク（既存安全境界・失敗再現優先）

- **B / GLB NEXT-008**: 境界256辺でR4に約数百msの観測があったため、厳密に同一な無向境界線分の**安全で上限付きの署名による高速経路**を設計/測定し、R2空間距離・R3連結成分ガードを絶対に省略しない。微小摂動・向き/順序入替・再三角化・スケール・255/256/257辺・64部品512面の合成対照で、誤一致/性能悪化がないか先に再現。明確な改善がなければ実装せずテスト/文書のみ。`auto_apply=false`、実部品同一性未証明を維持。所有 `cbdk/glb_*`、GLB専用tests/fixtures/docs。共有CI/スモークはA。
- **C / UI-001・BUILD-001**: R5でBlender3版実機合格した登録/解除とScene所有権を起点に、CBDK自作生成previewのモジュール再読込、descriptor入替、継承/影プロパティ、登録途中の明示的失敗、モード切替・共有mesh時の拒否を**実Blenderで**追加検証。外部アドオンを実行せず合成foreign宣言のみを使う。UI5機能/6レシピ保持、操作不可で変更・登録漏れ・foreign削除0。GUI/Undoホットキー未検証。所有 `templates/modular_preview/`、`cbdk/ui_layout.py`、`cbdk/modular_builder.py`、C専用tests/docs。共有 `scripts/blender_modular_addon_smoke.py`/CIはAに依頼。
- **D / EXT-001**: 既存公開停止フラグを維持し、CBDK自作7正例ZIPとともにZIPの総容量16MiB/各要素2MiB/64要素、および公式ログ200,000文字上限前後・不正局所/中央記録/未知/重複/矛盾出力の合成負例を厳密に評価。誤判定・過剰CPU/メモリ・値やパス漏洩が再現された場合のみ最小修正。公式出力許可リストを憶測で緩めない。所有 `cbdk/extension_*`、D専用tests/docs。共通validator/CI/STATEはA。

### R6ブランチと統合条件

1. **7系統CIの事後確認が成立した後のみ**、着手時の最新版 `feature/v0.18-shape-diagnostics` HEADを取得して、`a1c2f84715acce1f8cd33abaf003556708c13c07` の子孫であることを確認。R6作業を旧R5 PR #46〜49のHEADから始めない。Aの共有docs更新が先に入った場合はその後の最新HEADを優先。
2. B: `work/v018-glb-analysis-r6`、C: `work/v018-ui-builder-r6`、D: `work/v018-extension-quality-r6`。1チーム1専用ブランチ・未統合追加ドラフトPR最大1件。baseは `feature/v0.18-shape-diagnostics`。
3. 担当パス外変更禁止。実測Python 3版、Windows 2版、Blender 3版の実ジョブ、Chromium、Handoff、必要なKit/Skillと**R6専用の新規負例が実際に走ったか**を分けて報告。共有スモークを追加する必要があれば先にAへ依頼。個別CI成功は結合CIではない。
4. B/C/D稼働中にAがR6 PR先行レビュー・競合とCI資源を点検しR7を設計する。実ユーザーGLB、実Windows GUI/Undo、ライセンス、正式Extension発行、private data、main、v0.19以降のゲートは従来のまま。Codexは任意、なくても停止しない。


## 2026-11-08 JST — R7正式割当（R6統合後7CI検証済）

R6 B [#54](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/54) `0c2936874c9759242d262512685ec616705993f4`、C [#55](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/55) `4624c83c1161c4a26761f92494a8ab96743bd47a`、D [#53](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/53) `d6263f4dc8029930ddfe76d647e984059a5ee846` は各5系統CI成功（Kit/Skillは未実行）。Aが専用統合PR [#56](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/56)を作成し、候補初期HEAD `7400516a9ab8230eda60a0daea8141e0c03c2844` でB4/C5/D3の12ファイルを結合した。**上記ゲートは実測通過済み。** 本節のR7タスクは正式に割当済み。各チームは開始時に最新dev HEADとR6統合SHA祖先関係を再確認して、担当専用ブランチ・ドラフトPRを1件だけ作成する。

**正式発効の検証記録:** AがR6統合PR #56の正確な候補SHA `7400516a9ab8230eda60a0daea8141e0c03c2844` の5系統全成功を確認してdevへsquash merge、**統合コードSHA `e2f09e593d9c7bdff66695c7e8972eea98e160ca`** でpost-mergeの**7系統全成功**を別途確認：[Python #42410463309](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463309)、[Windows #42410463276](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463276)、[Blender 3版 #42410463269](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463269)、[Chromium #42410463349](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463349)、[Handoff #42410463353](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463353)、[Kit #42410463251](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463251)、[Skill #42410463244](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42410463244)。R7作業はこのR6統合SHAの**子孫である着手時点の最新 `feature/v0.18-shape-diagnostics` HEAD**から開始する。Aによるキュー統合・節目文書追記でHEADが進んだ場合はその新しいHEADを優先し、R6の旧個別PRから分岐しない。

### R7候補・所有範囲

- **B / NEXT-008（GLB-fastpathの負例強化）:** R6の厳密無向線分署名高速経路で、同数線分の分割位置変更、同じ輪郭に異なる連結構造、near-degenerate/zero-length、端点のfloat32量子化、64部品の重複motif、255/256/257辺の分岐と負荷を合成データで調査。R2双方向距離fallbackとR3境界連結チェックの実行を明示証明。誤一致/超過負荷が再現した場合に限り最小変更。速度倍率は合成matcher局所の観測であり実GLBへの汎化なし。 `auto_apply=false`、`cross_file_part_identity_proven=false`維持。担当 `cbdk/glb_*`・GLB専用test/docs、共通CIはA。
- **C / UI-001・BUILD-001（ネイティブ登録失敗回復）:** 部分的なoperatorクラス登録失敗後にScene宣言が欠落/外部差替されたとき、reload/enable-disableを繰り返してもCBDK所有物の漏れやforeign削除がないことをBlender 4.4.3/4.5.15/5.2.1の**実機ジョブで実測**。C自身の `tests/blender_ui_lifecycle_r5.py` にR7マーカー追加可能（既存A共通CIの実行を維持）。生成プレビュー5機能6レシピ、fail-closed、入力不変。第三者実アドオン/Windows GUI/Undoホットキーは未検証のまま。担当 `templates/modular_preview/`・C専用test/docs、共有CI/STATEはA。
- **D / EXT-001（TOMLレビュー上限）:** 現状の静的TOML manifest reviewの32KiBファイル/64項目周辺、UTF-8不正、入れ子/重複/未知キー、出力先symlink/逸脱のケースをCBDK自作合成データだけで検証。正常な固定ZIP preview 7例とBlender公式validator既知ログ正例を維持し、値・private path/maintainer等を漏らさない。未確認ライセンス・所有者・署名/公開を新たに承認しない。不具合を再現するまではテスト/文書のみ。担当 `cbdk/extension_*`・D専用test/docs、validator共有script/CI/STATEはA。

### R7正式許可に必要なAの確認

1. R6統合PR #56の**正確な最後のHEAD**でPython3/Windows2/Blender3/Chromium/Handoffが成功。特にCの新規R6ネイティブマーカーをBlender3版の実際のジョブログで確認。途中失敗・未完了・skipを成功と誤記しない。
2. R6の結合コミットだけを `feature/v0.18-shape-diagnostics` へ統合。旧R1〜R6個別PRは歴史参照として二重マージしない。開発SHAの**post-squash 7系統CI（Kit/Skill含む）**が全成功。
3. Aが最新開発HEAD SHA（R6統合後およびこのdocs-only変更の後続を含む）とR6統合コミットの祖先関係を確認し、R7の基点を正式確定。B `work/v018-glb-analysis-r7`、C `work/v018-ui-builder-r7`、D `work/v018-extension-quality-r7` はそこで初めて作成。各専用draft PRは未統合最大1件。
4. Codexは任意。privateソース/GLB、main、正式v0.17.0、将来v0.19有効化、Windows GUI、ライセンス/正式Extensions配布は触らない。AはR6節目STATE/生成Handoff/PROGRESS/既存Notionを追って同期し、R7開発中R8を先読みする。


## 2026-11-08 JST — R7統合完了・R8ローリング正式割当（post-merge 7CI成功確認済み）

- **R7入力:** B [PR #61](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/61) 最終 `182ae87a47ddd127c3ef1a2afc3c1ce502880722`、C [PR #62](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/62) 最終 `eef6bcea675f3198a19d9aea973c7dbeecf4e814`、D [PR #60](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/60) 最終 `040036c785d47229f735342352a2881157bd36ed`。各担当の5系統CI全成功、11ファイル重複0。
- **重要な失敗と修正:** Bの初期テスト専用SHA `fff82a6d67e6b531d5f9da6244a3e91bc1f5522d` でゼロ長境界線分がR6 exact fastpathに誤って流れるケースを再現（Python負例失敗）。Bが生産matcherに厳密な正長ガードを追加し、ゼロ長時はR2保守的fallbackを使用、R3独立連結ガードは維持。実ユーザーGLBの穴位置/部品IDを証明しない。
- **A結合:** [PR #63](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/63) 候補HEAD `52dea171587888be2c26045808bbaf24a76bee7c` にB4/C4/D3件を正確に取り込み、[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413415247)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413415263)、[Blender3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413415266)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413415159)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413415103) の5系統全成功を確認。R7開発統合コミット `687b2acdc920253d69eda8c5e9c1c102d02aaef3`。
- **R8実装許可ゲートは確認済み:** R7開発統合コミット `687b2acdc920253d69eda8c5e9c1c102d02aaef3` に対する**別系統のpush CI全7系統success**：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646111) 3.11/3.12/3.13、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646149) 3.11/3.13、[Blender 3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646135) 4.4.3/4.5.15/5.2.1、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646129)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646222)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646126)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42413646165)。統合候補#63の5系統とは厳密に別に確認した。**本PR #64がv0.18開発ブランチにマージされ次第、R8正式実装可。**

### R8候補 — B / GLB NEXT-008

R7のゼロ長誤一致を修正済みのmatcherを基点に、最悪O(256²)の**非厳密一致時のR2双方向線分距離fallback**が安全な限定フィルタで早くなるかを合成ベンチマークで検証。セグメントbbox・距離下界などの候補除外は「R2許容範囲内の真陽性を一切捨てない」ことを先に数学的/負例で示し、形状が複雑/近接/非有限/退化した場合は元R2へfail-closed fallback。retriangulation、同一境界で異なる内部形状、near-notch、float32量子化、255/256/257辺、64部品・512面で差分辞書一致と測定。実測利得が無ければテスト/設計のみ（必ずしも本体実装を要求しない）。`auto_apply=false`、`cross_file_part_identity_proven=false`、R3グラフ検証と予算保持。担当 `cbdk/glb_*`・GLB専用tests/docs。共有CIや他担当に変更が必要ならAへ。

### R8候補 — C / UI-001・BUILD-001

R7のBlender実機・登録途中fail-closedを基に、**unregister_class途中の人工的失敗**、Scene property差替後のcleanup再試行、enable/disable・モジュールreload反復においてCBDK所有クラス・登録済みSceneを漏らさないか検証。加えてCBDK自作プレビューの編集operatorが検証/例外でキャンセルされた場合の**入力mesh/selection/modeの不変性**をheadless Blenderで計測。実際に再現した不具合のみ担当範囲で最小変更。R7の4つの `native_r7_*` markerを残し、R8専用マーカーをBlender3版の実ジョブで観測（`tests/blender_ui_lifecycle_r5.py` の既存呼び出しを活用）。5機能/6レシピ保持。GUI Ctrl+Z実機確認や第三者Addon実併用は未検証。担当 `templates/modular_preview/`、C専用test/docs、A管理の共通smoke/CIは変更禁止。

### R8候補 — D / EXT-001

CBDK自作fixtureのみを使い、**ビルド形式の妥当性、公式validator結果、作者の同意、SPDX/再配布権限、公開承認を独立した証拠**として保持する静的provenance判定の負例を設計・テスト。TOMLでの64項目はトップレベルに限る既存実装、32KiB byte予算、過度な入れ子・相反するログ・ZIPパス・manifestの不明な権利主張などで、`blocked_for_extension_release` を誤って解除しないことを検証。正式パッケージの署名や実インストールを捏造せず、未承認コードを実行しない。安全性の欠陥が観測されるまでは本体修正せずデータだけのtests/docs。担当 `cbdk/extension_*`・D専用tests/docs。公式validator共通CI/STATEはA管理。

### ローリング規則

1. **R7 post-merge 7CI実測合格後、Aがこの割当PRをマージしたときにR8正式有効。** BCDは着手の瞬間に最新の `feature/v0.18-shape-diagnostics` のHEAD SHAを取得し、`687b2acdc920253d69eda8c5e9c1c102d02aaef3` の子孫であることを確認。#60〜63や旧R7ソースSHAから再利用・スタック禁止。
2. B: `work/v018-glb-analysis-r8`、C: `work/v018-ui-builder-r8`、D: `work/v018-extension-quality-r8`。各チーム未統合の追加ドラフトPR最大1件。targetは `feature/v0.18-shape-diagnostics`、担当専用ブランチと変更所有範囲を守る。共有STATE/Handoff/PROGRESS/Notion/CI/mainはA担当。
3. Python/Windows/Blender3版の正確なHEAD CIを新規負例が**実際に走ったか**まで確認。個別成功とA結合成功、統合後7CIは別ゲート。Codexが使えなくても継続、基点・依存や所有権が不明なら実装せずAに設計を報告。
4. 実ユーザーGLB、Windows GUI/Undoホットキー、第三者アドオン実併用、正式Extensionsの所有権・権利・ライセンス・公開許可、`main`と正式v0.17.0は引き続き承認待ち。R8はv0.18開発ブランチの範囲に限定。


## 2026-11-08 JST — R8統合完了・R9ローリング正式割当（post-merge 7CI成功）

**正式許可ゲート検証済み:** A R8結合 [PR #73](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/73) はB/C/Dの13ファイル（担当重複0）を候補HEAD `f5fd6585488e7d69501caf2ed48c54ec81e0cc2a` に集約し、Python/Windows/Blender3版/Chromium/Handoffの5系統success（新規 `native_r8_*` 5項目を各Blender実機ジョブログで確認）。v0.18開発ブランチへsquash SHA **`ded947f85f46fb8cce0943314d6e1a9fb41717ef`** として統合後、**独立した7系統CIもすべてsuccess**：[Python #42419734167](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734167)、[Windows #42419734210](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734210)、[Blender3版 #42419734261](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734261)、[Chromium #42419734226](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734226)、[Handoff #42419734193](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734193)、[Kit #42419734233](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734233)、[Skill #42419734172](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42419734172)。**本PR #74を開発ブランチにマージした時点でR9が正式に有効**。着手時点の最新版dev HEADを利用し、旧R8個別PRを再マージしない。

- B [#66](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/66) 正確なソースSHA `0c81b10cf1010b967b3a9b8dd8fd572dbf2b010c`、4パス、個別5系統CI success。R8のR2 AABB事前棄却はpadded 2tで非厳密R2の安全な最適化、同じ数学的R2結果を元のunpruned scannerと合成テストで比較。少数のmatcher局所性能測定を実GLB全体性能に拡大解釈しない。
- C [#70](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/70) 正確なソースSHA `07a742f124bda35d3474be45a461eef48df64d64`、6パス、個別5系統CI success。native headless Blender3版で5つの `native_r8_*` の実行確認が必要。
- D [#67](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/67) 正確なソースSHA `a8f1b28204f88169e0a581939b5114fc570a47c7`、3パス、個別5系統CI success。自作合成fixtureのZIP構造・validator観測・著作権/再配布/配布許可を分離し、根拠なき承認を阻止。
- R8統合時の本体変更はBの保守的GLB prefilterが中心。C/Dは合成・ネイティブの安全回帰を主とする。実GLB・Windows GUI・第三者実Addon・正式Extensions公開の証拠にはならない。

### R9 B：GLB（安全なR2 AABB最適化の「効かないケース」を可視化）

- **目標:** 256辺密集・重複motif・near-coincident/float32許容境界・非多様体near-weld/退化線分など、R8のbbox候補除外が利得を得られない／誤棄却しやすい条件を先に計測。R8の**全結果辞書と強制unpruned R2の一致**、R6 exact/R7ゼロ長guard/R3独立連結成分判定、256辺/64部品/512面の上限とfail-closedを維持する。
- 複雑なAABB事前計算や小型空間インデックスは**数学的にsafeで測定利益と予算を実測できる場合のみ**試作し、利得なしなら回帰テスト・性能記録だけ提出。メモリ消費・Python 3バージョン差を測定。ユーザーGLBによる精度/物理的穴位置/部品同一性の主張、`auto_apply`は引き続き禁止。担当はB所有の `cbdk/glb_*`、GLB専用tests/docsのみ。

### R9 C：Blender UI（Scene削除失敗と登録解除の再試行）

- **目標:** R8でクラスの `unregister_class` 失敗を試験できたので、今度は**クラス正常detach後のScene RNA属性削除だけを人工的に失敗させる**負例をCBDK自作fixtureで追加。cleanup ledger/tokenを欠損/誤消去せず、live reload拒否・foreign Scene property保全・再試行解除・新規登録の衝突拒否がBlender 4.4.3/4.5.15/5.2.1ヘッドレス実CIで成立するかを確認。
- 新規 `native_r9_*` 固有マーカーで3版実行を確認。問題が再現する場合のみ最小本体修正。R7/R8既存マーカーと5機能/6レシピを壊さない。合成失敗テストを「Windows GUI Ctrl+Z保証」「実第三者Addon併用保証」と取り違えない。担当は `templates/modular_preview/`、Cのtests/docs。A管理CI・STATE等は触らない。

### R9 D：Extensions（自己申告hashの整合性とソース真正性の差）

- **目標:** CBDK自作の既知ZIPを使用し、(a) 1部だけ変更してSHAを更新しない不整合、(b) 変更後にアーカイブ `files_sha256` と対応するsource SHAを**両方更新して自己整合にしたZIP**を合成。前者は静的構造/ハッシュ不整合としてfail-closed、後者は自己整合を認めても**真正性・作者同意・再配布/公開承認を絶対に昇格しない**ことを証明。
- ZIPの構造安全性、固定7件positive、実Blenderの合成official validator正例、未知/矛盾ログの保守的処理を保持。新しい未知コード実行や実Addonインストール、私有ソース・個人path使用は禁止。観測した不具合のみD所有 `cbdk/extension_*` で最小修正。その他D専用test/docs。

### ローリングR9の安全規則（本PR #74統合後に正式発効）

1. R8結合#73の正確なHEAD 5系統とdev squash SHA `ded947f85f46fb8cce0943314d6e1a9fb41717ef` の独立7系統は**既に全success確認済み**。本PR #74を正式統合した後のみ、R9担当専用ブランチを作成可能。
2. 着手の瞬間に最新 `feature/v0.18-shape-diagnostics` HEADを読み、**R8統合SHAを祖先に持つこと**を確認。B `work/v018-glb-analysis-r9`、C `work/v018-ui-builder-r9`、D `work/v018-extension-quality-r9`。各自の未統合追加ドラフトPRは最大1件。旧B #66/C #70/D #67をstack/再マージしない。
3. 担当専用ファイルのみ変更。共有 `STATE.json`・Handoff・PROGRESS・Notion・共通CI・mainはA管理。新負例が実際のCIで実行されたか検証し、未実行をgreenと扱わない。Codex不在でも継続。
4. 実ユーザーGLB、実Windows GUI/Undo、第三者Addonとの実共存、作者/ライセンス、公式Extensions公開、main、正式v0.17.0はすべて別承認。上記の正式統合前はR9実装禁止。


## 2026-11-08 JST — R10 プレ設計 — R9統合ゲート未達なら**設計のみ・実装禁止**

**Aの先読み案であって正式割当ではない。** R9個別 B [#78](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/78) / C [#77](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/77) / D [#76](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/76) は、各正確なHEADでPython / Windows / Blender3版 / Chromium / Handoffの5系統CIがsuccess。AのR9統合候補 [#81](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/81) はB3/C4/D3の10ファイルを担当重複0で最新devから独立結合。**以下の条件をすべてAが実測してから**R10の編集許可・ブランチ基点を正式発効すること。途中でCIがred / canceled / pendingなら設計・レビューのみ、PR追加なし。

1. R9統合PR #81の**最終厳密HEAD**に対し、Python 3.11/3.12/3.13、Windows 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1（実際の `native_r9_*` ログ）、Chromium、Handoffの**5つの独立workflow系統がすべてsuccess**。R9個別CIは統合CIの代用にしない。
2. #81を`feature/v0.18-shape-diagnostics`に**一度だけsquash統合**、開発統合コミットSHAを記録する。過去R1〜R9個別PRや古い統合PRを二重mergeしない。
3. 上記**統合後SHAそのもの**に対して別のpush CI **7系統**（Python、Windows、Blender3版、Chromium、Handoff、Kit、Skill）がすべてsuccessし、Aがジョブと対象SHAを確認する。
4. Aが最新の`docs/project/STATE.json`、生成`docs/PROJECT_HANDOFF.md`、`docs/PROGRESS.md`を節目同期し、R10正式割当文書を承認・統合した後のみ、各チームは**その時点の最新dev HEAD**を基点に新担当専用ブランチを作る。R9専門ブランチからstackしない。未統合追加PRは担当1件まで。

### R10 B候補 / NEXT-008：低選別率R2-AABBの適応判定を安全側で調査

- **出発点:** R8のpadded 2×t AABBは疎な合成輪郭で速度向上。R9密集128辺のmatcher局所では、AABB判定がほぼ全部通過し、3つのPython版で強制unprunedより遅い場合を観測。これは一般GLB全体の速度断定ではない。
- **設計:** 疎/密/境界許容値付近の対照を同一Python版で反復計測し、全結果辞書・R2距離述語・独立R3連結ガード・R6 exact署名・R7ゼロ長guard・256辺/64部品/512面・review_onlyを保持できる「適応的に不要なAABB処理を迂回」する安全な条件があるか検証。単なる速度推測で製品本体を変更しない。数学的保証と3版の独立測定が無ければtest/docsのみ。
- **許可候補:** `cbdk/glb_*`、GLB専用tests/docs。共通CI/スクリプト/STATEはA。ユーザーGLB、物理穴、部品同一性、auto applyは未証明。

### R10 C候補 / UI-001・BUILD-001：二重失敗の所有権ledger回復

- **設計:** CBDK自作生成previewで、同じ`unregister()`中にoperatorクラス解除とScene RNA削除が共に失敗する合成負例、失敗間にforeign Scene宣言が差替られる負例を実Blender 3版で試す。成功した除去だけledgerから消し、残りの正確なtokenと名前を保全、reload/再登録を安全に拒否、次の明示retryで完全回復して初めて成功とする。
- **検証:** R5〜R9既存nativeマーカー・5機能6レシピを保持し、R10専用nativeマーカーをBlender 4.4.3/4.5.15/5.2.1の実ジョブログで確認。合成foreign物のみ、実第三者アドオンやGUI Ctrl+Zは未検証。
- **許可候補:** `templates/modular_preview/`、C専用tests/docs。`scripts/`、CI、STATEはA。

### R10 D候補 / EXT-001：自己hashと別管理の既知ソース照合

- **設計:** R9はZIP自身が改変後のhash一覧を書き直しても「自己整合」は証明できる一方、作者真正性・同意・ライセンス・正式公開権限は証明しないと確認。R10は**リポジトリ内の明示された既知CBDK自作source**と生成ZIPのhelper bytesを、allowlistとサイズ・件数制限を設けて**読み取り専用で比較する候補**を検証。元を更新した場合の正例、再hash改変の負例、未知root・path逸脱・値/パス漏洩の負例を含む。
- **安全:** 比較一致ですら作者同意/SPDX/著作権/署名/公式validator/公開承認にはならない。未知Pythonはimport/exec/installせず、私有ソースを公開しない。問題が再現しなければtests/docsのみ、`blocked_for_extension_release`維持。既知7 ZIP正例も保持。
- **許可候補:** `cbdk/extension_*`、D専用tests/docs。公式validator共通script・CI・STATEはA。

**R10はまだNOT ACTIVE。** Aが上記ゲート後に正式基点・ブランチ名・受入基準を再公布するまで、B/C/Dは現在のR9 PR以外に新たな実装PRを作らない。Codex不在でも設計/負例候補調査は可能。main、正式v0.17.0、GitHub Pages、実ユーザー資産、Windows GUI、権利決定は変更しない。

## 2026-11-08 JST — R9統合成功・R10正式割当（本PR #82の開発ブランチ統合後に有効）

**R9のゲートは成立済み:** B [#78](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/78) SHA `60fcda39`、C [#77](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/77) SHA `a525fa8e`、D [#76](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/76) SHA `b29de167` は各5系統CIが成功し、変更10ファイル重複0。A結合 [#81](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/81) 最終HEAD `b5978eac7fde14387ca50e36569a1128fae9610d` の別5系統CIも成功（Blender3版の`native_r9_*`四項目を実ジョブログ確認）。開発squash SHA **`914f1c8ab8cf8dfe104f46054bfd4c84fc101e61`** の独立7系統CIもすべてsuccess：[Python #42423898180](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898180)、[Windows #42423898189](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898189)、[Blender3版 #42423898177](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898177)、[Chromium #42423898202](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898202)、[Handoff #42423898215](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898215)、[Kit #42423898188](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898188)、[Skill #42423898183](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42423898183)。これらは開発統合後に実行されたGitHubの`pull_request`イベントで、旧個別PRのCIではない。

**正式な実装開始条件:** このA所有のR10正式割当PR #82が`feature/v0.18-shape-diagnostics`へマージされ、担当者が着手直前に最新dev HEADと `914f1c8ab8cf8dfe104f46054bfd4c84fc101e61` が祖先であることを確認した場合に限りR10を開始。#82がdraft/CI赤/未統合なら上のプレ設計どおり**設計のみ**。専門R9個別PR #76–#78は統合済みコードの履歴資料で、二重マージ/force-pushをしない。各チームに新しい未統合ドラフトPRは最大1件。

- **B / NEXT-008:** 新ブランチ `work/v018-glb-analysis-r10`。上記プレ設計の疎/密AABB合成モデルで、危険な誤棄却がない適応的R2 AABB回避の数学的条件とPython3版同条件メモリ/時間測定を先に検証。密集モデルで繰り返し利益がなければtest/docsのみ。 `cbdk/glb_*`、GLB専用tests/docsだけ。R2/R3/256辺・64部品・512面、`auto_apply=false`維持。
- **C / UI-001・BUILD-001:** 新ブランチ `work/v018-ui-builder-r10`。クラス解除とScene RNA削除の二重失敗、失敗途中のforeign差替、所有token/ledgerを保持した複数retryを合成して、Blender 4.4.3/4.5.15/5.2.1の実ジョブで`native_r10_*`を確認。R5〜R9マーカー、既存5機能6レシピ保持。 `templates/modular_preview/`、C専用tests/docsだけ。
- **D / EXT-001:** 新ブランチ `work/v018-extension-quality-r10`。CBDK自作のrepo管理helperソースと、生成プレビューZIPのhash自己申告を、読み取り専用・上限付き・trusted-root固定で照合する負例/正例を検討。一致も真正性/作者同意/公開権限にならず、`blocked_for_extension_release`維持。実行/インストール・私有ソース公開禁止。 `cbdk/extension_*`、D専用tests/docsだけ。

各チームは着手時の最新dev SHAと作業対象ファイルをPR本文へ明記。正確なHEADでPython3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1、Chromium、Handoffの発火5系統CIを実測し、追加負例が本当に実行されたか区別する。Aが統合ブランチで再度5CIを確認し、開発squash後7CIで次ラウンドを許可。共通STATE/HANDOFF/PROGRESS/CI/Notionと`main`、正式リリースはA所有。Codex不在でも専門チームを止めない。Windows GUI/Undo、実ユーザーGLB、真の第三者Addon、ライセンス、正式Extensions、Pagesは引き続き別承認。
