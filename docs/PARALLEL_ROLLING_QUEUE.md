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
