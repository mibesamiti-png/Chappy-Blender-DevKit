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
