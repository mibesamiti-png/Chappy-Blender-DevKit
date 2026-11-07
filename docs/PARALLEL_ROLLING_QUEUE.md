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


## 2026-11-08 JST — R7候補（Aの事前割当案、R6統合後7CIまで未発効）

R6 B [#54](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/54) `0c2936874c9759242d262512685ec616705993f4`、C [#55](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/55) `4624c83c1161c4a26761f92494a8ab96743bd47a`、D [#53](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/53) `d6263f4dc8029930ddfe76d647e984059a5ee846` は各5系統CI成功（Kit/Skillは未実行）。Aが専用統合PR [#56](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/56)を作成し、候補初期HEAD `7400516a9ab8230eda60a0daea8141e0c03c2844` でB4/C5/D3の12ファイルを結合した。**R6の結合PRおよび開発ブランチ統合後の独立7系統CIを確認するまでは、以下R7を実装・新規PR化しない。** この節は先読みの非発効仕様であり、正式なR7作業基点の確定記録はCI後のAの追記で行う。

### R7候補・所有範囲

- **B / NEXT-008（GLB-fastpathの負例強化）:** R6の厳密無向線分署名高速経路で、同数線分の分割位置変更、同じ輪郭に異なる連結構造、near-degenerate/zero-length、端点のfloat32量子化、64部品の重複motif、255/256/257辺の分岐と負荷を合成データで調査。R2双方向距離fallbackとR3境界連結チェックの実行を明示証明。誤一致/超過負荷が再現した場合に限り最小変更。速度倍率は合成matcher局所の観測であり実GLBへの汎化なし。 `auto_apply=false`、`cross_file_part_identity_proven=false`維持。担当 `cbdk/glb_*`・GLB専用test/docs、共通CIはA。
- **C / UI-001・BUILD-001（ネイティブ登録失敗回復）:** 部分的なoperatorクラス登録失敗後にScene宣言が欠落/外部差替されたとき、reload/enable-disableを繰り返してもCBDK所有物の漏れやforeign削除がないことをBlender 4.4.3/4.5.15/5.2.1の**実機ジョブで実測**。C自身の `tests/blender_ui_lifecycle_r5.py` にR7マーカー追加可能（既存A共通CIの実行を維持）。生成プレビュー5機能6レシピ、fail-closed、入力不変。第三者実アドオン/Windows GUI/Undoホットキーは未検証のまま。担当 `templates/modular_preview/`・C専用test/docs、共有CI/STATEはA。
- **D / EXT-001（TOMLレビュー上限）:** 現状の静的TOML manifest reviewの32KiBファイル/64項目周辺、UTF-8不正、入れ子/重複/未知キー、出力先symlink/逸脱のケースをCBDK自作合成データだけで検証。正常な固定ZIP preview 7例とBlender公式validator既知ログ正例を維持し、値・private path/maintainer等を漏らさない。未確認ライセンス・所有者・署名/公開を新たに承認しない。不具合を再現するまではテスト/文書のみ。担当 `cbdk/extension_*`・D専用test/docs、validator共有script/CI/STATEはA。

### R7正式許可に必要なAの確認

1. R6統合PR #56の**正確な最後のHEAD**でPython3/Windows2/Blender3/Chromium/Handoffが成功。特にCの新規R6ネイティブマーカーをBlender3版の実際のジョブログで確認。途中失敗・未完了・skipを成功と誤記しない。
2. R6の結合コミットだけを `feature/v0.18-shape-diagnostics` へ統合。旧R1〜R6個別PRは歴史参照として二重マージしない。開発SHAの**post-squash 7系統CI（Kit/Skill含む）**が全成功。
3. Aが最新開発HEAD SHA（R6統合後およびこのdocs-only変更の後続を含む）とR6統合コミットの祖先関係を確認し、R7の基点を正式確定。B `work/v018-glb-analysis-r7`、C `work/v018-ui-builder-r7`、D `work/v018-extension-quality-r7` はそこで初めて作成。各専用draft PRは未統合最大1件。
4. Codexは任意。privateソース/GLB、main、正式v0.17.0、将来v0.19有効化、Windows GUI、ライセンス/正式Extensions配布は触らない。AはR6節目STATE/生成Handoff/PROGRESS/既存Notionを追って同期し、R7開発中R8を先読みする。
