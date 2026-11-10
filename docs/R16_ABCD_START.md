# CBDK通常開発 R16 — ABCD正式割当（同期ゲート後に有効）

2026-11-11 JST。**本書・DEC-077・PROGRESS・ローリングキューを含むA節目同期PRがv0.18開発ブランチに統合され、その最新HEADで独立7系統CIが成功するまで、R16実装ブランチ/PR作成は禁止。** それまでは読み取り専用の設計・負例検討のみ。これはv0.19や正式v0.18公開の開始ではない。

## R15の厳密な受入証拠

- B [#120](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/120) `70b27ab40b9c129d780fd26fdd177c9e67368b65`、C [#121](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/121) `54832e779c5cd26a10e392120bcb7bb2f514b874`、D [#119](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/119) `cae75c51c9004d8bbaecdce432761da3d981c31d`：各専門HEADのPython3/Windows2/Blender3/Chromium/Handoff、5系統CI success。11ファイルの担当間重複0。
- A [#122](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/122) 結合HEAD `25180ce91453613e2524226df2c324654ad0818b` の5系統成功。初回Windows Python3.13は**既存ダッシュボードNode子プロセスの15秒timeout**、失敗した1ジョブだけコードや制限を変更せず再実行してsuccess。初回失敗は記録、原因/再発なしの保証はしない。
- 一回統合dev `08ddb3e3a51e526ddfe857268f31b2de443c0fec` の**別途独立7CI success**：[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915099059)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915098806)、[Blender3版](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915099109)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915098872)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915098940)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915098954)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42915098964)。Cの実Blender各版57チェック内にR15の6項目。旧R15 PRは二重マージしない。

## B/C/Dの最小P1

| 担当 | 専用ブランチ（ゲート後） | 目的・編集可能パス | 受入条件・停止条件 |
|---|---|---|---|
| **B GLB NEXT-008/GLB-021** | `work/v018-glb-analysis-r16` | R15の自己申告basisと独立ソースの非真正性を踏まえ、**自己申告が一致しても再利用/古いrevision/異なる試行は証明不能**な負例を厳密に整理。B専用 `cbdk/glb_*`・tests/docs | syntheticだけで、偽/欠落/差替え/batch境界を限定検証。既存statusのunknownとreview_onlyを守る。独立authenticityを証明できないなら新manifest API/大規模本体変更は**作らずtests/docsのみで終了**。私有GLB/path/座標を公開しない。hash・token一致は編集/ライセンス許可ではない。 |
| **C UI-001/BUILD-001** | `work/v018-ui-builder-r16` | 既存5機能/6レシピの**Panel.draw後にmode/selectionが変わる負例**をBlender実operatorで検証。C専有 `templates/modular_preview/`・tests/docs | 旧表示のenabled=trueは後続操作を許可しない。mode変更/ゼロ選択/foreign Sceneを作ったfixtureで実`bpy.ops`を確認、CANCELLED時に座標/Sceneを不変。4.4.3/4.5.15/5.2.1実ログ。再現した不具合だけ最小修正し、失敗なければtests/docsで停止。Windows GUI/Undoは未検証。 |
| **D EXT-001** | `work/v018-extension-quality-r16` | R15の同inode・既知digestの**2回読み取りの間の合成書換え/復元**で、検出できる場合とできない場合を区別。D専用 `cbdk/extension_*`・tests/docs | 同じdigestの反復観測を現在の安定性と同一視しない。テスト専用・時間/サイズ予算内、未知はunknown。ZIP上限16MiB/2MiB/64 members、7正常プレビュー、Windowsのnative reparse不保証を維持。作者承認/実ソース安全/正式Extension配布に昇格しない。負例で改善利益が確認できなければtests/docsのみで終了。 |

**A並行担当:** 各PRの新HEAD/所有パス/実CIを必要最低限で確認し、重複作業を増やさない。既存CIで確認済みの同一SHAの証拠は再利用するが、統合候補HEADには必須5系統、統合後dev HEADには独立7系統を新たに要求。CI改善PR #109は速度向上の実測なしに統合しない。研究Geometry #114、Development Intelligence #115は独立。

## 制約・開始ゲート

1. A節目同期PRの候補HEADが必要CIを通過しdevへ一回統合され、**その新dev HEADの独立7CI全成功を確認して初めてR16実装可能**。B/C/Dは最新dev HEADを開始時に再取得。
2. 各担当は自身のR16専用ブランチ→dev向けDraft PRを最大1件。互いの担当パス、A専有STATE/Handoff/PROGRESS/共通CI/Notion、main、旧専門PR、研究PRを編集・二重統合しない。
3. 各専門HEADの必須5CI→A結合HEADの5CI→一度だけdev統合→新dev独立7CIの4段階は別々に確認。Pythonだけのmock成功はBlender実テストを代替せず、静的manifest名一致は第三者コードの安全証明ではない。
4. 実ユーザー私有GLB/元アドオンの公開・実行、Windows GUI確認済み表示、著作権/作者許諾の決定、正式Extensions公開、直接GitHubインストール、GitHub Pages公開範囲変更、v0.19のactive化は禁止。品質ゲートを緩和しない。
