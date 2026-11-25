# CBDK R24 — F020-02 非空依存閉包と互換性の限定縦断（C/D）

2026-11-26 JST。既承認v0.20計画とユーザー継続指示。**本書/future JSONのdev統合・独立7CI成功・Issue #125更新まで専門実装禁止。** B待機、GL/DIL独立。R25自動開始なし。

## 基点と差分

R23節目#166 dev 74458b072db5bf55090d3a85e275d40114a445a5 独立7CI（Python45700815698、Windows45700815565、Blender45700815591、Chromium45700815541、Handoff45700815542、Kit45700815896、Skill45700815567）成功、3版R23 marker、Notion既存ページ追記成功。F020-02既存6機能のrequires_featuresは全空。既存plannerの推移/循環Python検査は再利用し、R24 Cはテスト専用の非空依存閉包・登録/逆順解除/rollbackの実機縦断、Dはroot ZIPの依存閉包とmanifest互換範囲の独立照合/過大表示拒否。A同一物縦断。正式割当統合・独立7CI・#125更新前は着手禁止。B待機、GL/DIL独立、44要件/24 NEXT/正式版/main/last_verified維持。

現状 catalog/addon_features.json の6機能の requires_features はすべて空。plan_features は推移的閉包、順序、全グラフ循環、互換範囲交差、part source照合を実装済み。tests/test_feature_catalog.py に依存追加・循環・バージョン拒否のPython検証あり。build_modular は閉包からZIPと登録契約を生成。R23では4機能/2panel/2型の実機縦断済み。**既存の実機能に意味のない依存を追加しない。** 今回は非空依存による自動追加が生成/登録/解除まで正しく伝わるか、Extension固定manifestのmin4.4.0/maxなしが狭い依存閉包に対して過大にならないか、に絞る。

## C — F020-02 非空依存の生成・登録

branch work/v020-ui-builder-r24、専門PR1件。テスト専用固定合成グラフは既存6機能から次の4機能を選ぶ（製品の依存意味・新機能・実カタログ変更ではない）。vertex_nudge → edit_selection, mesh_center、edit_selection → mesh_bounds、mesh_center → mesh_bounds。要求 vertex_nudge のみ、閉包順は mesh_bounds, edit_selection, mesh_center, vertex_nudge。共有BLCTX-001/BLGEO-001は1回、合計 part IDs BLCTX-001, BLGEO-001, BME-001, BME-002, BME-003。R23 grouped UI定義は4機能の閉包に対して保持、要求だけを1機能にする。既存catalogのコピーとコード所有のソースをテスト用一時rootに限定、任意入力・外部rootの実行入口追加なし、実catalog SHA不変。必要なら既存テスト専用root経路を再利用。Aへ固定fixture関数と独立期待を渡す。

- Python：依存追加・順序・part/helper/member一意、generated init/BUILD_INFO/UI計画一致、明示全4機能要求と閉包同等（requested metadata差のためZIP全体byte一致は要求しない）、同じ要求の決定性。欠落/循環・狭い互換範囲の負例は既存検証を活用し、生成前拒否を独立確認。
- Blender 3版：自作合成ZIPの実登録順（operator 4 + panels）、解除逆順を記録して実際のクラス登録/解除を確認。依存途中または次operatorの制御失敗後のrollback/再登録、所有ledger・foreign保持。read/edit実操作と両パネル表示、型付き値、選択外不変、解除残存なし。R23等旧marker維持。実GUI/Undoは未検証。
- C所有：cbdk/feature_catalog.py、modular_builder.py、ui_layout.py、registration_audit.py、templates/modular_preview、C専用tests/docs/native lifecycle。既存製品変更は具体的失敗の再現がある場合のみ最小修正。カタログ本番requires_features全空維持。5CIと3版native markerで停止。

## D — F020-02/03 依存閉包とExtension manifest範囲

branch work/v020-extension-quality-r24、専門PR1件。R23 `extension_recipe_preview._assemble` は plannerから閉包を得るが、そのmanifestは固定fixture min4.4.0、maxなし。許容済みメタデータの一時合成変更による狭い互換範囲がroot ZIPで広がるかを独立再現する。**既存固定manifestと現在の6機能の正常出力を保持**し、最小保守策を選ぶ（固定範囲に合わない閉包は生成前拒否でよい。Blender最大境界意味を確認せず動的manifest一般化しない）。外部root/ZIP/metadata/code/新公開APIによる実行許可なし。固定テストの内部patch/信頼済みcheckoutコピーのみ。必要ならD側テスト独立の同じ固定グラフ・期待を使用し、Cのコードを待たない。A用に安全な依存fixture試験経路を渡す。

- 閉包順とZIP feature/helperの独立期待、共有部品一意、requestedとresolvedの区別、preflight/byte照合、SHA不変/決定性/fresh出力、承認フラグfalse。狭いmin/max・不整合閉包・循環などを生成前拒否、出力なし。固定R19とR23 read/edit/grouped、既定CLI挙動維持。実行が許される既存範囲の固定非空グラフに対し、3版公式validateと隔離offline native bl_ext enable/disable・依存自動追加された実機能の結果・cleanupを確認できる試験を追加。既存C所有ファイル/共有CLI/CI/STATEは変更しない。
- D所有：cbdk/extension_*.py、D専用tests/docs、既存Extension native検証入口。コード変更は再現した不具合に限定。5CI・3版実markerで停止。任意外部root、公式installer、配布、権利未確認コードは禁止。

## A — 統合と終了

C/Dの固定試験を同一の信頼済み一時checkout/非空依存fixtureで接続。要求1→閉包4→同一root ZIP公式validate→隔離native登録順、実read/edit、逆順解除・元SHA不変。必要な共有CLI/CI変更だけを担当し、非空依存fixtureを利用者向けオプションにしない。各5CI、結合5CI、dev独立7CIと全3版marker。差分がなければテストのみでよい。F020-02限定受入/残りF020-03やv0.20フェーズ判定は証拠後に別判断。正式版、main、44要件/24 NEXTの状態、last_verified、私有データ、権利/公開、GL/DILは変更なし。
