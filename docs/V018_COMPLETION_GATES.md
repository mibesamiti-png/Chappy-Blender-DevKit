# v0.18 到達状況・自動化残作業・人間ブロッカー

正本は`docs/project/STATE.json`。2026-11-07 JST。次期計画の承認を理由に、現行要件/NEXTを削除・保留化・形式的な完了へ変更しない。

| 現行ID | 自動化できた範囲 | 残りと終了条件 |
|---|---|---|
| NEXT-019 / GLB-021 | GLB-020差分→AST宣言/参照/構文経路の私有レビュー、合成変更履歴と反復。今回、測定元の集計SHAでASTレビューと実験を結ぶ | 79fea17の全6CI/Blender3版で接続を確認しNEXT-019完了。GLB-021全体と実プロパティ因果は未完了 |
| NEXT-009 | AST-only照合/測定元一致レビューにconstructor別名shadowing拒否・複数宣言triageを追加。b17fa4dの全6CI成功 | 任意実ユーザーの設定実体/登録/形状影響は未確認。対象の私有ソースやGLBを使う場合は別の明示許可が必要。全体は継続 |
| NEXT-003 / REG-001〜003 / PLAN-002 | 登録計画・依存/レシピ整合性・失敗TODO支援に加え、生成前AST依存/登録検査と実機/CI一覧照合 | c80f2a0/b5d3273の対象検証成功、NEXT-003受け入れ完了。静的に明示したhelper exportのみ対応。任意新部品の承認・採用は自動化しない |
| NEXT-002 / GUI-001 / UNDO-001 | 通常背景可否と明示undo_push制御条件を分離。単一/複数頂点・2連続操作・正確な接続/選択・取消無変更 | 対象3版の明示履歴2ケースUndo/Redo成功。通常背景Undoと制御条件は別の証拠。実Windows GUIでの操作・復帰・取消・操作感は未検証。ユーザー環境での協力/確認が必要 |
| NEXT-007 | 自作GLBの3版プレビュー/画像/metadata | 許可された実ユーザーGLBとの照合が残る。現時点で実データ利用許可はない |
| NEXT-008 | 合成生成/比較/診断/反復に、両方向focus・分類面割合・実験triageを追加。b17fa4d/Blender3版成功 | 実ユーザーの生成元との全工程・真の部品対応や細穴/内部形状は未保証。私有コードを無断実行しない |
| UI-001 / BUILD-001 | 固定5機能の宣言的見出し/順序のほか、OBJECT/EDIT_MESH mode・active meshのボタンガードと安全な頂点移動XYZ入力を追加。597ed5cのBlender3版/全6CI成功 | UI-001はpartial。汎用UI・任意operator・実Windows GUI操作/Undo・Extensions形式・権利・正式公開は未検証。次世代へ形式的に完了扱いして移行しない |
| EXT-001 / LIM-004 | 自作legacy/modular ZIPの出自・SHA/パス・承認フラグ検査とExtensions移行ブロッカーJSONを実装。1f31506のPython/Windows/Blender3版/Kit/Handoff/Chromium全6CI成功 | EXT-001はpartial。正式blender_manifest.toml/Extensions ZIPの生成、公式Blender extension validate、権利/ライセンス選択・配布/公開の個別承認は未完了。未承認内容の自動公開禁止 |
| EDIT-002 / PERF-001 | 監査/ベストエフォート復元/上限拒否/70×70実測 | クラッシュ耐性・全トポロジー復元・巨大/実メッシュ保証は未完了。未検証上限を緩和しない |
| NEXT-004 / INST-001 | 保留 | 直接インストール/更新は別の明示指示まで保留を維持 |

## 移行判断

今回の[次期計画](future/CBDK-FUTURE-019-022.md)は承認済みだが未有効。現行の自動化可能作業を完了し、上の人間ブロッカーと実際の到達点を確定し、PR #25の実測と統合方針を記録する。条件を満たせば開始承認の再取得なしでv0.19へ進む。

mainへのマージ・正式リリース・未承認採用・私有データ利用は引き続き別承認。承認待ちとコード未実装を混同しない。現行STATEに未来の要件やNEXTを追加しない。

## 過去判定（履歴）

79fea17の6CI成功でNEXT-019完了。NEXT-009は静的/自作合成の自動化範囲を拡充済みだが実データ実体・効果は未確認のため継続。次の自動化優先は既存NEXT-003の登録/依存/レシピ検査の残り、および現行UI準備。次期計画の開始承認は保持し、現行自動化未完了のためactive=falseを維持する。

### 登録/Undo節目の判定（履歴）

NEXT-003完了、NEXT-002は明示履歴のNative Undo/Redoを3版で成功確認したがGUI待ちで継続。上の過去判定より本節とSTATEを優先する。NEXT-008/009の実データ部分を未確認で残し、次の安全な自動化残項目を確認する。現行UI-001等の自動化は未完了なので将来計画はactive=falseのまま。[実測と失敗履歴](REGISTRATION_UNDO_VALIDATION.md)。

## 最新判定：双方向focus / AST曖昧さ節目

NEXT-008/009の今回の限定自動化はb17fa4dの全6CI成功。実ユーザー/GUI/権利/全形状保証を閉じず、両NEXTは継続。既存23件は18完了/4継続/1保留。次はUI-001の固定自作機能を対象とした宣言的レイアウト検証・生成。

移行条件は、(1)現行自動化完了=false（UI-001未実装、Extensions準備も残る）、(2)人間ブロッカー文書化=true、(3)最新PR #25の実測確認=true、(4)ドラフト継続/別承認の統合方針=true。したがって未来JSONのactive=falseを維持。開始承認は取得済みで再確認不要だが、未達を形式的に解消してv0.19へ飛ばさない。私有データ使用/実行、mainマージ、正式公開/採用の別承認も維持。

## 2026-11-08 JST 最新判定

EXT-001/UI-001/BUILD-001の今回拡充は63bddb9の全7CI成功。公式manifest検証はデータ専用合成例で、実部品のライセンスや正式Extensionの承認ではない。宣言UIは既存5機能/6レシピ+一時UI例、実画像は自作13レンダリング/4ブラウザ画面のみ。全体partial、23タスク18完了/4継続/1保留を維持。[証拠](EXT_UI_VALIDATION.md)。

移行ゲートは現行自動化完了=false（汎用UIと実Extension経路等に残り）、人間ブロッカー文書化=true、最新PR/CI確認=true、ドラフト継続/別承認方針=true。したがって次期計画active=falseを維持。承認待ちだけになったと形式的に扱わない。

## 2026-11-08 JST UI共通ガード節目

UI-001/BUILD-001の今回拡充はeac7453の全7CI成功。助言UI/実行監査を区別し、型付きSceneプロパティ生成失敗の復旧も3版で確認。[証拠](UI_GUARD_VALIDATION.md)。全体partialと23タスク18完了/4継続/1保留を維持。

移行ゲート：現行自動化完了=false（汎用UI/設定定義/実Extension経路に残り）、人間ブロッカー整理=true、最新PR #25実測確認=true、別承認/ドラフト統合方針=true。次期計画active=false、既存の開始承認は保持する。

## 2026-11-08 JST UI表示条件/設定計画節目

今回拡充は4b99068の全7CI成功。固定visible_in・範囲縮小・非実行UIレビューと生成物の計画を確認。旧仕様/レシピを維持し、実GUI/任意UI/実Extension/権利/実データを完了扱いしない。[証拠](UI_MODE_SETTINGS.md)。

現行自動化完了=false（汎用UI/設定/実Extension経路の残り）、人間ブロッカー整理=true、最新PR #25実測確認=true、ドラフト継続/別承認方針=true。次期計画active=false、既存の開始承認は保持。次の自動化はEXT-001診断と公式validatorの合成結果照合。

## 2026-11-08 JST EXT診断照合節目

EXT-001に値なしTOMLレビュー/共有案内/公式6例の項目照合を追加。Blender等はede29de、データパーサー修正後Python839件/Windowsは1e18232で成功。[証拠](EXTENSION_DIAGNOSTICS.md)。実部品の権利/ライセンス・正式Extension・GUIは未確認、全体partialを維持。

現行自動化完了=false（optional構造レビュー/汎用UI/実Extension経路等に残り）、人間ブロッカー整理=true、最新PRの影響範囲別実測確認=true、別承認/ドラフト統合方針=true。将来計画active=false、開始承認は保持する。


## 2026-11-25 JST — R17受入後の残条件

独立7CI成功のdev `236b9a3254928d7cb69d5c415fd8a3e792ee5de7` を根拠にR17の限定成果を受入。全体の完成判断は別。

| 分類 | 残条件 | 次の判断 |
|---|---|---|
| 既存自動化 | UI-001/BUILD-001: 固定5機能のレシピ別宣言UIは実測済み。汎用UI/型付き構成の未対応範囲 | 既存仕様との差を確認し、必要な機能のみ限定。任意コード/権限拡大なし |
| 既存自動化＋owner | EXT-001: optional残項目、正式manifest/Extension ZIP生成・公式検証経路 | 合成データで可能な生成/検証と、実部品のライセンス/権利/公開判断を分離。勝手に実配布しない |
| 実ユーザー入力待ち | NEXT-007/008/009: 実GLB照合、実プロパティ登録/因果、真の部品対応 | 私有入力の個別明示許可とローカル検証。合成追加だけで全体完了にしない |
| 実環境待ち | NEXT-002/024: Windows GUI Undo/Redo、ライブボード音/実通信 | ユーザー環境確認。公開は別承認 |
| 保留 | NEXT-004: GitHub直接インストール | 既存保留を維持 |

移行ゲート：現行自動化完了=false、ブロッカー整理=true、最新PR独立7CI確認=true、ドラフト/別承認方針=true。R18は自動割当せず、Aが既存仕様から残作業を限定判断。次期active=false、正式v0.17.0/last_verified維持。


## 2026-11-25 JST — R18限定受入後の残条件

#142統合dev `36d4090402f66f49d5644fbef91f1c03d95a6b34` 独立7CI成功。[Blender実測](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45547798994) 3版各67 lifecycle、R18 global/inline center、合成Extension ZIP/公式build/validateを確認。既存7部品、6機能、旧6レシピの互換維持。実行を拒否する固定sentinel付き合成Extensionは実用アドオンではない。

| 分類 | 現在の到達点 | 残る完成条件 |
|---|---|---|
| UI-001/BUILD-001 | コード所有descriptorで第6機能追加と安全なレシピ別UIを実証 | 汎用型付き設定・任意の新規機能の契約は未対応。固定機能を増やすだけの追加ラウンドは禁止。既存仕様との必要差を限定 |
| EXT-001 | 明示metadataからTOML/合成ZIP生成と公式build/validate、実previewの6機能検査 | 実際に動くCBDK自作previewのExtension化、登録/解除/実operator検証は未実装。合成sentinelの合格を正式配布の承認と混同しない。実ライセンス/owner承認は別 |
| NEXT-007/008/009 | 合成GLBとtriage | 許可済み実データと実因果のローカル確認 |
| NEXT-002/024 | headless/合成ブラウザ | 実Windows GUI Undo/Redo、ライブボード実通信/音 |
| NEXT-004 | 保留 | 明示指示まで維持 |

次の判断はAが既存仕様の必要最小限の縦断経路（動作する自作preview→Extension形式→公式validate→隔離Blenderで登録・実行・解除）とUI設定契約を確認すること。権利のないコードや実ソースを勝手に変換・公開しない。追加の研究/負例/ラウンドを自動発行せず、既存の未達を一括で扱う。現行自動化完了=false、ブロッカー整理=true、独立7CI確認=true、ドラフト/別承認方針=true。次期active=false。44要件/24 NEXT/正式版/last_verified不変。


## 2026-11-25 JST — R19限定受入・v0.18基盤完成候補

#147統合dev `538e0b58a9d4c05fce49de617a7d84342e5290cd` 独立7CI成功。[Blender実測](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/45557833046) jobs139014085712/139014085377/139014085639、各69 lifecycle、R19両入力UI、R18合成ZIP/build、R19実生成ZIP validate/runtime/typed vertical、HIT/SHA。PR #25同HEAD draft・main未統合。

R18時点で未達だった二つの限定自動化は実証完了。コード所有の2型入力の共有経路、固定CI用の2機能レシピの実生成→Extension ZIP→公式validate→隔離bl_ext手動stage/enable→RNA default2・range1..4→実中心表示→precision1へ変更→disable/cleanup。R19同一ZIPでの接続成功であり、一般のユーザー向け変換コマンド/公式installer/任意UI/権利承認ではない。

| 残る範囲 | 判断・既存計画との対応 |
|---|---|
| UI-001/BUILD-001/PLAN-002/REG-001〜003 | 固定自作のレシピ/2型/登録計画・検査基盤は成立。任意の新規部品、追加型、汎用レシピ・登録生成・利用者向けExtension出力は未実装。既存F020-01〜03（v0.20）の実用化範囲に対応。要件partial維持 |
| EXT-001 | 固定実行可能CI ZIPは合格。一般レシピ変換・公式installer・他metadataは未実装/未検証。F020-03/F022-03に対応、権利/採用/配布は別owner承認。partial維持 |
| GLB-010/020/021/022・NEXT-007/008/009 | 合成MVPと限定triageは成立。大規模/部品対応/穴/内部形状はF019-01〜03、汎用因果/反復はF021-01〜03。許可済み実GLB・実ソースのローカル検証は残る。partial/NEXT継続 |
| ISO-001/EDIT-002/PERF-001 | 条件付き静的検査、復元、上限拒否の実装を維持。任意ソース依存/全トポロジー・原子性/巨大メッシュ保証は未達、将来の安全な部品組立・修正・計算予算の範囲で必要性を実測。完了にしない |
| GUI-001/UNDO-001/DASH-001・NEXT-002/024 | 実Windows GUI、Undo、live GitHub通信、可聴音は実環境待ち。F022-01/02のGUI/統合範囲と区別し、NEXT継続。Pages公開は別承認 |
| INST-001/NEXT-004 | 既存保留。直接GitHubインストールを開始しない |

完成判断候補：v0.18の限定的な自動化基盤（既存の安全なプレビュー、分析MVP、登録支援、型付きUI、固定Extension実行）についてはR19で区切れるとAは判断。残るコード未実装は明示して既存次期計画との対応を記録し、人間待ちだけと偽らない。一般変換/任意UI等を現行でさらに作るかは既存F020/F022との重複を基に判断し、R20を自動発行しない。本節目同期PRのCIと統合後独立7CI確認前に移行ゲートを変更しない。現行JSON active=false、v018_automatable_work_completed=falseのまま。最終移行判断は節目確認後の別手順、正式版/main/権利/私有データ/last_verified/状態数は不変。


## 2026-11-25 JST — 移行最終判断（#148後）

dev `d4aa43016ad85159584a0d88b33e7cbb58368b97` 独立7CI成功。#25同HEAD draft、未マージ。Python45560603306、Windows45560603301、Blender45560603365（jobs139023118362/139023118742/139023118639、3版各69 lifecycle、R18/R19 marker、同一ZIP typed vertical、HIT/SHA）、Chromium45560603489、Handoff45560603287、Kit45560603398、Skill45560603308。

Aの範囲判断：現行仕様の固定自作legacyプレビュー、依存/登録支援、GLB合成MVP、2型UIと固定実行可能Extensionの限定経路は成立。旧仕様の残る広い要件を完了とはしないが、上節の対応表の通り、追加の汎用生成・公式installer準備・大規模GLB・任意因果・統合GUIは既承認の次期実用化計画内で進める。現行基盤を際限なく拡張しない。この判断における v018_automatable_work_completed=true は限定基盤の区切りであり、全partial解消ではない。私有実データ/GUI/権利の未確認と保留はそのまま。新規権限なし。

4移行ゲート成立と判断し、承認済み独立JSONをactiveに変更する候補を提出する。v0.19のみin_progress、v0.20〜22未着手。44要件/24 NEXTの状態、正式v0.17.0、last_verified、mainは不変。移行候補のCI・統合・独立CIまではIssue #125 paused、実装開始なし。その後AがF019既存実装とGL研究を読取照合し、限定割当を作る。GL研究の無断採用なし。Notion同期は確認後。
