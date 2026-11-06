# CBDK｜新しいチャットの開発引き継ぎ

このファイルが新しい会話の入口。GitHub main と最新の実際のCIを優先する。古いREADMEやチャットの印象で開発状況を判断しない。

## 新しいチャットで最初にすること

1. リポジトリ mibesamiti-png/Chappy-Blender-DevKit の main を確認する。
2. このファイル、docs/project/STATE.json、docs/PROJECT_SPEC.md、AGENTS.md を読む。
3. pyproject.tomlのバージョンと、部品/機能カタログを照合する。
4. 前回のCI成功が現行コミットのものか確認する。未実施テストを成功とみなさない。
5. 次の優先タスクをブランチで実装し、テストと状態を更新してPRを作る。

## 最新の開発状況

- 現在のバージョン: `0.17.0`
- 開発段階: public_repository_v0.18_development
- 最新の節目: v0.18でworld bounds比較＋32x32シルエットIoU比較まで実装。PR #24でPython 347件×3版、Windows 2版、Blender 3版、Windows kit、handoffが全成功。同bounds異輪郭の実機検出も成功
- 次の予定リリース: `0.18.0`
- 自作部品: 7件 (BLCTX-001, BLCTX-002, BLGEO-001, BLMOD-001, BME-001, BME-002, BME-003)
- 組み込み機能: 5件 (edit_selection, mesh_bounds, modifier_summary, object_selection, vertex_nudge)
- 部品の正式採用と再配布ライセンス確認は未完了。個人用プレビューのみ。

## 仕様・実装・未実装の一覧

| 要件 | 機能 | 状態 | 検証種別 | 備考 |
|---|---|---|---|---|
| `SRC-001` | PythonアドオンのASTスキャン・関数台帳 | 実装済 | Pythonテスト | 元コードを実行せず解析 |
| `DUP-001` | AST・構造重複候補と検索 | 実装済 | Pythonテスト | 同等性は保証しない |
| `REV-001` | 候補の手動選択・来歴記録 | 実装済 | Pythonテスト | 選択は採用/ライセンス承認ではない |
| `ISO-001` | ソース内/複数ファイルの依存静的検査 | 一部実装 | Pythonテスト | 条件に合う安全側パターンのみ |
| `AUD-001` | Blender API静的監査・契約 | 実装済 | Pythonテスト | 実機検査とは分離 |
| `PART-001` | 再利用自作部品の台帳と実機スモーク | 実装済 | Blender CI | 7部品。実行証拠はPR #16のCI。台帳は承認を与えない |
| `PLAN-001` | 機能依存閉包・Blender互換性チェック | 実装済 | Pythonテスト | 5機能。許可リストにないコードは実行しない |
| `BUILD-001` | レシピからのBlenderアドオン生成 | 一部実装 | Blender CI | レガシー形式・固定の自作プレビューのみ |
| `EDIT-001` | Edit Mode選択頂点の安全な移動 | 実装済 | Blender CI | 単一メッシュ/有限オフセット/Blender UNDOフラグ |
| `EDIT-002` | 編集差分の監査とベストエフォート復元 | 一部実装 | Blender CI | 加工前不変スナップショット＋ライブ監査。XYZごとに変化を検証し、ゼロ指定軸・未選択頂点の変更は厳格拒否。異常時復元/再検査。PR #21のBlender 4.4.3/4.5.15/5.2.1 CIで実測成功 |
| `TEST-001` | Python/Windows/Blender 3バージョンCI | 実装済 | Blender CI | リポジトリ公開化後、PR #21でPython 3.11/3.12/3.13、Windows PowerShell 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1が全成功。mainの正式last_verifiedは未更新 |
| `UI-001` | 汎用アドオンUI組み立て | 未実装 | 未検証 | 任意レイアウトの生成は未対応 |
| `EXT-001` | 正式Blender Extensions形式と公開パッケージ | 未実装 | 未検証 | 法的/ライセンス確認を先に行う |
| `INST-001` | GitHubからBlenderへの直接インストール・更新 | 保留 | 未検証 | ユーザー希望で保留。UI確認段階まで実装しない |
| `PERF-001` | 巨大メッシュ向け監査・効率化 | 一部実装 | Blender CI | 20万要素の事前サイズ検査、加工後の座標・選択を2回目の全コピーなしで比較。実機70×70グリッドの測定をCIで実施、上限超は変更前に拒否 |
| `GUI-001` | 実際のGUI Undo・操作感の自動検証 | 未実装 | 未検証 | ヘッドレスではUndoフラグと編集結果まで確認 |
| `UNDO-001` | 背景BlenderでのネイティブUndo/Redo検査 | 一部実装 | Blender CI | PR #21でBlender 4.4.3/4.5.15/5.2.1の背景プローブを実行。背景ではundo.poll不可をunavailableとして正しく記録し、GUIショートカットは対象外 |
| `PLAN-002` | 全レシピと部品依存の一括静的監査 | 一部実装 | Pythonテスト | 6レシピ・5機能・7部品の整合性と3版の静的互換性を照合。PR #21のPython 3.11/3.12/3.13全体テスト成功 |
| `REG-001` | 自作部品・機能の登録計画自動生成 | 一部実装 | Pythonテスト | 未登録ID・依存・ソース衝突を検査して非実行のレビュー計画を生成。コード/台帳の自動追加・承認は行わない。PR #21のPython 3版CIで回帰テスト成功 |
| `REG-002` | 登録計画から未完成テストのひな形を安全に生成 | 一部実装 | Pythonテスト | 現行カタログと登録計画の完全一致を確認し、TODO失敗テストをignored領域に新規生成。Windows短縮パス差も修正し、PR #21のPython/Windows CI成功 |
| `REG-003` | 読み取り専用・メッシュ編集で未完成テストの内容を切替 | 一部実装 | Pythonテスト | --behavior read_only/mesh_editを明示指定。共通項目に不変性・Undo・選択範囲・復元を追加。PR #21のPython 3版CIで回帰テスト成功 |
| `GLB-001` | GLB静的構造解析とBlender多方向プレビュー | 実装済 | Blender CI | schema v2静的解析＋Blender本命7方向PNG＋最大32部品単独サムネイル＋neutral clay/Workbench。PR #21のBlender 4.4.3/4.5.15/5.2.1で合成GLB fixtureの構造JSON・scene metadata・全画像生成が成功 |
| `GLB-002` | BlenderなしGLB Quick Preview fallback | 実装済 | Pythonテスト | 任意依存trimesh+matplotlibで7方向PNGと最大32部品単独サムネイルを生成。外部URIを事前拒否し、50万頂点/25万面の安全上限。ユーザーGLB(7 mesh)で7方向+7部品画像をローカル生成確認。本命のBlender実レンダリングより低精度であることを明示 |
| `GLB-003` | 参考GLBと生成GLBのworld-space形状回帰比較 | 実装済 | Blender CI | scene metadata schema 3のworld bounds、shape/strict比較、geometry fallback matching、glb-regression CLIを実装。PR #23でPython 343件×3版、Windows 2版、Blender 4.4.3/4.5.15/5.2.1のsynthetic GLB metadata self-comparisonが全成功。bounds同一の輪郭差はLIM-008として継続 |
| `GLB-004` | 7方向・部品別シルエットIoU回帰比較 | 実装済 | Blender CI | scene metadata schema 4で32x32 binary silhouetteを全体7方向＋最大32部品のfront/right/top/isoへ保存。IoU比較をglb-compare/glb-regressionへ接続。PR #24でPython 347件×3版、Windows 2版、Blender 4.4.3/4.5.15/5.2.1が成功し、Cubeと同boundsの八面体をsilhouette差だけで失敗判定できることを実機確認 |
| `GLB-005` | 形状診断の数値根拠集約と矛盾データ拒否 | 実装済 | Blender CI | 参考/候補GLBのscene・部品差分を影響視点、最悪IoU、相対誤差、体積割合、重大度別で集約し、異常JSON・矛盾カウンタを拒否。PR #25のコードcommit e971b784でPython3版/Windows2版/Blender3版の実機診断と回帰テスト成功。公開・実ユーザーGLB再現の保証なし |
| `GLB-006` | GLB差分から確認すべきアドオン設定候補を提示 | 実装済 | Blender CI | GLB診断から設定候補群・確認手順・最悪IoU・代表軸をレビュー専用JSONへ出力。PR #25のコードcommit d9c5c925でPython3版・Windows2版・Blender 4.4.3/4.5.15/5.2.1・Windowsキット・引き継ぎCIが全成功。実アドオン内にその設定が存在することや完全形状一致は未検証 |
| `GLB-007` | GLB修正候補とローカル自作アドオンのプロパティ宣言を静的照合 | 実装済 | Blender CI | 元アドオンを実行せず指定Pythonのbpy.props宣言とGLB修正候補を名前完全一致で照合。匿名ソース名/クラス/行/種類のみ出力。PR #25のコードcommit c3635075でPython3版、Windows2版、Blender3版の合成fixture、Windows kit、handoffが全成功。実アドオンでの登録と形状影響は未検証 |
| `GLB-008` | Blenderプロパティ候補の静的参照・書き込み追跡 | 実装済 | Blender CI | AST-onlyで同名属性へのread/write/read_write/deleteの可能性を匿名ソース、関数、行番号、件数で出力。PR #25実装commit c640ad06でPython3版・Windows2版・Blender 4.4.3/4.5.15/5.2.1の合成fixture・kit・引き継ぎCI全成功。受信オブジェクトの実体と実際の形状への影響は未検証 |
| `GLB-009` | プロパティ宣言と同クラスself参照を別オブジェクトの参照から区別 | 実装済 | Blender CI | 匿名ソース/同クラスself参照と別クラス・別オブジェクト参照をAST上区別しread/write等を全件集計。PR #25の実装commit 2c000dadでPython3版・Windows2版・Blender 4.4.3/4.5.15/5.2.1・kit・handoff CI全成功。宣言プロパティの実体同一/登録・ジオメトリ効果は未検証 |
| `GLB-010` | プロパティ式からメッシュ生成APIまでの構文上の経路を追跡 | 一部実装 | 未検証 | bpy.ops.meshのプリミティブ、bmesh.opsの一部、object寸法等へselfプロパティまたは直線的ローカル別名が引数として届くAST上の経路を検出。関数内共起のみでは判定しない。分岐/ループ/関数間は未追跡、実際の形状効果は未証明。新規20回帰テスト・Blender3版合成fixtureを追加、現head CI成功確認前 |
| `GLB-011` | プロパティ値からBoolean/Bevel/Solidify等のモディファイア設定までAST上で追跡 | 実装済 | Blender CI | 直線的selfプロパティ/別名からmodifier.width/thickness/operation/object等の代入・複合代入までAST経路を検出。PR #25 commit b1a57e57のPython3版・Windows2版・Blender 4.4.3/4.5.15/5.2.1合成fixture・kit・handoff CI全成功。実際のモディファイア実体・形状効果は未検証 |
| `GLB-012` | 信頼済み合成Blenderアドオンのパラメータ変更前後を定量測定 | 実装済 | Blender CI | CBDK製合成アドオンの球半径/Bevel幅変更を生成直後とGLB再読込後で平均/最大頂点変位と変化点数として測定し、他の部品が不変の対照実験を確認。PR #25 commit 04526f1dのPython3版/Windows2版/Blender4.4.3/4.5.15/5.2.1/kit/handoff全CI成功。任意GLB・ユーザーアドオンへ一般化できない |
| `GLB-013` | CBDK合成GLBの設定値を上下プローブして参考形状への改善方向を判定 | 実装済 | Blender CI | 自作合成モデルで基準・参照2・上下4の計7 GLBを生成/再読込。頂点順不変の局所半径分布で球半径とBevel幅の増加方向のみ参考に近づくこと、減少方向で遠ざかること、非対象部品が不変であることをBlender4.4.3/4.5.15/5.2.1 CIで検証。PR #25 commit e73f7ebaはPython3版/Windows2版/Blender3版/kit/handoff全成功。実ユーザーGLBには適用保証なし |
| `GLB-014` | 三角面サンプリングの双方向表面距離で頂点順・面分割の違いと開口差を検出 | 実装済 | Blender CI | 24 Haltonサンプル/三角形の面積重み付き双方向3D表面距離（最大128面）で、同じ面の別三角分割=0、同外寸の中央開口=非ゼロ、Z+0.25=0.25を自作合成4 GLBで実測。実装/文書commit f7e9e114のPython3版/Windows2版/Blender4.4.3/4.5.15/5.2.1/kit/handoff CI全成功。Blender4.5.15の対称距離: 別分割0、中央開口0.0081329、Z+0.25=0.25。小穴/密閉空洞/大規模GLBと真のHausdorffは未検証 |
| `GLB-015` | 三角面の最近接距離をBVHで高速化し安全上限を512面へ拡張 | 実装済 | Blender CI | 決定的な三角形AABB-BVHの枝刈りで精密点→三角面距離の候補計算を削減し128→512面/meshへ拡張。Python総当たり照合含む新規10回帰テスト成功。PR #25 commit bcef8572でPython3版、Windows2版、Blender4.4.3/4.5.15/5.2.1、kit/handoff CI全成功。256面GLB（Blender4.5.15）の精密三角形距離計算は総当たり1,572,864回→BVH49,152回（32分の1）。実測実行時間の改善と実大規模GLBの処理は未検証 |
| `GLB-016` | BVH/総当たりの実時間中央値を比較し512面の合成GLBを実機測定 | 実装済 | Blender CI | 同一合成64面でBVHと総当たりのウォームアップ後3回の時間中央値を比較、512面GLBはBVH単独で測定。合成GLB6種をBlender4.4.3/4.5.15/5.2.1で生成→再読込し、距離一致/512面距離0を確認（commit 9581ab20、Blender run 42240589340成功）。64面ms: Blender4.4.3 BVH35.510505/総当たり161.156313、4.5.15 BVH19.356758/86.027068、5.2.1 BVH32.46785/149.716417。512面BVH ms: 352.050953/192.798623/321.247609。Python3版/Windows PowerShell2版/kit/handoff含む全5 CI成功。速度比はCI閾値でなくランナー依存 |
| `GLB-017` | 粗い8点から疑わしい面と探索枠だけ48点へ細分化する多解像度表面比較 | 実装済 | Blender CI | 粗8点/面から疑わしい最大8面＋面積上位2面を48点/面まで選択精査するレビュー専用双方向距離。従来24点と粗8点で見逃した幅0.44の中央開口を精査で検出（最大距離0.0657466）。Blender4.4.3/4.5.15/5.2.1で自作合成7 GLBの書出・再読込に成功。コード+文書commit 4c7248c8のPython3版、Windows2版、Blender3版、Windows kit、handoff全CI成功。閉じた内部空洞・任意の微小穴の検出保証なし |

## 既知の問題・制約

| ID | 重要度 | 状態 | 内容と回避策 |
|---|---|---|---|
| `LIM-001` | medium | open | 監査後のトポロジー破損は座標復元だけでは修復不可。回避策: 作業ファイルのバックアップとBlender標準Undoを使い、危険な加工は正式採用しない |
| `LIM-002` | low | open | GUIのCtrl+Zと操作感はヘッドレスCIでは未検証。回避策: UIのある開発段階でWindows上で確認する |
| `LIM-003` | low | open | Blender公式アーカイブ取得で稀にHTTP 403。回避策: ダウンロード失敗とコード失敗を区別し、CIの失敗ジョブのみ再実行する |
| `LIM-004` | medium | open | 自作部品の採用・ライセンス/再配布確認は未完了。回避策: 開発用プレビューのみで、approved=falseを維持する |
| `LIM-005` | low | open | 大規模メッシュは監査20万要素上限を超えると操作しない。回避策: 小さなメッシュに分割するか、必要に応じ監査上限を再設計する。安全を確認せず上限を解除しない |
| `LIM-006` | low | fixed | 非公開時のGitHub Actionsランナー未割当(steps=null)は公開化で解消。回避策: 2026-11-06にリポジトリをpublicへ変更後、同じPRワークフローで実ランナー・steps・logsが生成され全CIが実行可能になった。Issue #19は解決としてclose |
| `LIM-007` | low | fixed | GLB多方向プレビューの実機CI未実行問題は解消。回避策: PR #21のBlender 4.4.3/4.5.15/5.2.1で7方向画像と部品単独画像を含むfixtureテストが成功。実ユーザーGLBのBlenderレンダリングは引き続き必要時に個別確認 |
| `LIM-008` | medium | open | 32x32シルエット比較でも小さな穴・内部形状・サブグリッド細部は見逃しうる。回避策: world bounds＋全体7方向＋部品4方向シルエットIoUを併用し、必要なら次段階で表面距離/ボクセル比較を追加する。シルエット一致だけで完全な形状同一を主張しない |

## 次にやること（優先順）

1. `NEXT-006` **PR #18の公開リポジトリCI再検証とv0.16統合** (done)。完了条件: 公開化後にPython/Windows/Blender/パッケージ全CI成功を確認し、PR #18をmainへ統合済み
2. `NEXT-002` **Blender Undo・Redoの実機検証を拡充** (in_progress)。完了条件: 自動化可能なUndo/Redoの機械的チェックと、GUI操作未検証部分を切り分けて記録する
3. `NEXT-005` **v0.17：ベンチマーク実測を比較して監査の追加最適化・Undo/Redo回帰テストを検討** (todo)。完了条件: 3つのBlender版の監査結果とメモリ測定を比較し、速度/安全性の妥協点と残るGUI検証を記録
4. `NEXT-003` **機能登録と新レシピ構築の自動化を改善** (in_progress)。完了条件: 新規許可部品で台帳・依存・CIの不一致を検出する
5. `NEXT-004` **GitHubからBlenderへ直接インストール・更新** (deferred)。完了条件: ユーザーがUI確認の必要性を示すまで作らない
6. `NEXT-001` **v0.16：大きなメッシュ向け監査負荷軽減と上限時の安全な中断** (done)。完了条件: メモリ上限・タイミング・入力拒否をPython/Blenderの両方で測定し、意図しない編集を発生させない
7. `NEXT-007` **GLB Visual Inspectorの3バージョンBlender CIと実データ精度確認** (in_progress)。完了条件: 合成fixtureの3バージョンBlender CIは完了。実ユーザーGLBでも必要に応じBlender Previewを生成し、Quick Previewとの部品対応と形状を照合する
8. `NEXT-008` **参考GLB→アドオン生成→GLB再出力→形状差分の自動デバッグ** (in_progress)。完了条件: 参照GLB/生成GLBをBlenderで別々に実レンダリングし、world-space bounds・部品対応・7方向画像・構造を比較して、ズレの種類と対象部品を機械可読JSONへ記録する。boundsだけでは判別できない形状差は次段階で画像/表面距離比較を追加する
9. `NEXT-009` **診断した設定候補と実アドオンのプロパティの安全な照合** (in_progress)。完了条件: bpy.props宣言とGLB候補の一致、属性read/write、同クラスself参照、Blenderメッシュ生成API引数への直線的AST経路をレビュー限定で実装。分岐/ループ/他関数や実プロパティの正確な実体・形状効果は未検証。次は承認済み合成アドオンの形状変化を実機で別途比較する
10. `NEXT-010` **安全な合成アドオンで形状変化を数値実証** (done)。完了条件: CBDK製合成アドオンで球半径/Bevel幅の単独変更をGLB再読込後まで定量比較。変更対象の頂点移動が正・非対象は0を3版Blender CIで確認（commit 04526f1d）
11. `NEXT-011` **合成GLBの上下パラメータ探索で改善方向を検証** (done)。完了条件: 生成前後・GLB再読込後の7条件に対し半径分布スコアを使い、正方向で誤差減、負方向で誤差増、非対象の頂点変化0をBlender3版で確認（commit e73f7eba）。
12. `NEXT-012` **合成GLBの3D表面距離で異三角分割・中央開口・高さ方向のズレを検証** (done)。完了条件: 自作4 GLBをBlender4.4.3/4.5.15/5.2.1で実生成→再読込し別分割=距離0、同外寸中央開口は差分検出、Z+0.25=0.25を確認（CI commit f7e9e114）。元アドオン非実行・自動承認なし
13. `NEXT-013` **BVHで256面GLBの比較計算を削減し512面まで回帰検証** (done)。完了条件: 総当たりとBVHの距離結果一致、400/512面比較・過大入力拒否をPython CIで確認。256面合成GLBのBlender4.4.3/4.5.15/5.2.1実再読込比較は距離0・4倍以上の精密距離計算削減で成功（commit bcef8572）。Blender4.5.15の計算回数1,572,864→49,152
14. `NEXT-014` **Blenderの合成64面/512面GLBで実行時間中央値と正確性を検証** (done)。完了条件: 3版Blenderで6 GLB生成/再読込、64面の同一入力BVH/総当たりの距離一致と実行時間中央値、512面BVH単独中央値を観測（Blender run 42240589340）。速度倍率をCI合否条件としない。実ユーザーGLBに対する性能は未検証
15. `NEXT-015` **細い開口を検出する多解像度表面サンプリングを合成GLBで検証** (done)。完了条件: 実測済: Pythonの13回帰テストとBlender4.4.3/4.5.15/5.2.1自作合成7 GLB。従来24点最大距離0、粗8点0、精査48点0.0657466（run 42244257499）。同一性認定・私有モデルの実行/公開なし

## 前回、実際に確認されたテスト

- 対象リリース: v0.17.0 / 2026-11-06
- Python: 334件成功; 3.11, 3.12, 3.13 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42183135653)
- Windows PowerShell: 3.11, 3.13 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42183135667)
- Blender: 4.4.3, 4.5.15, 5.2.1; 共通部品 7件; 生成レシピ 6構成 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42183135712)
- Windowsキット生成 [実行記録](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42183135650)
- 前回の[PR](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/pull/22)
- 注意: ヘッドレスCIはGUI Ctrl+Z/操作感を保証しない。GLB fixtureの実レンダリングは検証済みだが、個別のユーザーGLBは必要時に別途Blender Previewで確認する。

## 継続する設計判断

- `DEC-001` GitHubが開発状況・仕様・検証の引き継ぎ元。チャット履歴に依存しない。新チャットはGitHubの引き継ぎ文書から開始
- `DEC-002` Blender実機CI優先、Windows GUI確認は必要時のみ。ヘッドレスCIを操作感のテストと偽らない
- `DEC-003` 未確認コードや私有元アドオンは自動実行・公開しない。各部品の正式採用、ライセンス、実機検査を分離
- `DEC-004` GitHubから直接インストールする管理機能は当面保留。UI確認が必要になる段階で検討
- `DEC-005` PR更新時の重複・陳腐化したCIを抑制し使用枠を節約。PythonはPRとmain pushに限定。全CIにPR単位concurrencyを適用し、引き継ぎCIはPRで重複unittestを実行しない。品質ゲート自体は維持
- `DEC-006` 編集失敗時のロールバックは非有限座標でも可能な限り復元し、結果を実際に再検証。復元前の接続関係を座標と独立に検証。元の値を書き戻してから座標・選択・接続関係を再検査し、完全に戻らなければ成功扱いしない
- `DEC-007` 背景Blender Undo/Redoの検査不可は成功と区別する。undo.poll/redo.pollが不可ならunavailableと記録。実機CI未実行・GUI Ctrl+Z未検証を明示し、v0.15の最終成功記録は更新しない
- `DEC-008` レシピ追加や部品登録の整合性を別の静的マトリクスで検査。新たなレシピ/機能は明示的な期待構成と全依存ファイルの検査が必要。静的検査をBlender実機やライセンス確認の代用にしない
- `DEC-009` 新規部品登録は提案生成と人手の許可を分離。CLIでレビュー案を出力しても許可リスト・元ソース・部品台帳を変更しない。新部品は正式採用せず、手動レビューとCIが必要
- `DEC-010` テストひな形はレビュー用の未完成コードと明示して非実行・非上書き。生成先はreports/latest/scaffolds内のみ。全TODOはself.failで成功偽装を防止し、tests/や元機能・台帳へ自動登録しない
- `DEC-011` 新機能の動作種別は開発者の明示申告とし自動推測しない。read_onlyとmesh_editの申告は静的メタデータであり実機での安全性証明ではない。既存ドラフトはunspecifiedとして共通5項目を維持し、生成ひな形はすべて失敗TODO
- `DEC-012` GLB形状理解は構造JSONとBlender実レンダリングを根拠にする。画像生成AIによる再構成を元GLBの正確な表示として扱わず、生成画像は説明図・設計案に限定する
- `DEC-013` Blender不能時は任意依存Quick Previewをfallbackとして使う。trimesh+matplotlib画像は実GLB形状から生成するが描画精度はBlenderより低い。外部URIを拒否し、Blender実レンダリングが利用可能ならそちらを優先する
- `DEC-014` 公開リポジトリではGitHub Actionsを実機デバッグ基盤として積極利用する。2026-11-06のpublic化でprivate時のランナー未割当が解消。追跡済み内容は公開情報になるため、ユーザーGLB・私有元アドオン・生成private report・秘密情報は今後もコミットしない
- `DEC-015` 積み上げPRは下位からmainへ順次統合し、正式バージョンは専用release PRのCIで確定する。v0.17では#18→#20→#21を通常mergeで履歴保持。release/v0.17.0でpyprojectと状態台帳を揃え、成功CI観測後にlast_verifiedを更新する
- `DEC-016` 形状差分は修正判断の証拠であり、比較結果だけでアドオンコードを自動採用・承認しない。v0.18のglb-compare/glb-regressionはズレを機械可読化する。修正は通常のコードレビュー・Python/Windows/Blender CIを再度通し、ユーザー私有GLBは公開GitHubへ保存しない
- `DEC-017` GLB診断は検証可能な比較差分に基づくレビュー仮説であり、自動修正・完全一致認定をしない。最悪IoUと差分誤差を証拠として並べ、32x32輪郭の死角を明示。未知の差分コードやwarning/infoが存在したら未確認事項として記録し、比較結果の矛盾は拒否する
- `DEC-018` 診断から生成した設定候補は推測として表示し自動変更しない。ボール/ソケット/ヒンジ名称は弱いロール推測に限り、元ソースとの実一致・数値修正量は判断しない。候補→人手確認→生成GLB再出力→再比較を推奨し、コード実行/書換/自動承認/私有GLB公開を禁止
- `DEC-019` プロパティ宣言の静的検出をBlender登録や形状への影響の証明と混同しない。未確認アドオンはimport/execせず明示選択されたファイルのみAST検査。完全一致した宣言も登録済みとはみなさず、非一致を不存在と断定しない。私有コード本文/値/元パスはignored領域のレポートにも出さず、結果は自動適用/承認しない
- `DEC-020` ASTの同名属性参照は実際のBlenderプロパティや形状変更の証拠に昇格しない。関数・クラス名とアクセス区分はレビュー用の手がかりのみ。receiver一致・Blender登録・実行時の効果はnot_verified。動的getattrや他モジュール参照は未捕捉、参照サンプル数に上限。コード・値・パスは保存せず全データをignored reports領域に限定
- `DEC-021` 同クラスself属性参照は強めのレビュー手がかりに限り実行時の同一プロパティと断定しない。匿名ソース+クラスの一致とself構文のみで分類。未解決/他クラス/他ファイルを分離し、長いクラス名の匿名化衝突は照合から除外。関数呼出・実登録・メッシュへの影響・設定値の自動提案は未証明で、私有ソースを実行/公開しない
- `DEC-022` プロパティ値とメッシュAPIの構文的データフローは原因確定・自動修正の根拠にしない。許可リスト内Blender APIに明示的なselfプロパティ値/簡易ローカル別名が流れる場合に限って静的証拠を報告。分岐/ループ/ネスト/メソッド間は安全側で未検証。コード本文・数値・私有パスを出力せず、受信実体・ジオメトリへの効果・Blender登録は常に未確認
- `DEC-023` モディファイア名に似た属性への代入は未確認の構文上の経路に限定して表示する。modifier.widthやthickness等は任意のPythonオブジェクトにも存在可能。変数の型・実modifier・Boolean効果は証明できず、潜在経路をpossible_modifier_setting_assignmentとしてのみ記録。私有ソース実行/コード変更/自動承認は行わない
- `DEC-024` 幾何の実測はCBDK自作の合成fixture限定としユーザーアドオンへ一般化しない。同一頂点順の合成メッシュだけで局所頂点距離を数値化。一般モデルの別頂点順/トポロジ/内部穴には不適用。パラメータ単独変更と他部品非変化の対照実験を必須とし、私有アドオンは実行/公開しない
- `DEC-025` パラメータ上下プローブの最適化方向は同一合成fixture・同一距離指標内だけでレビュー提案する。参考を固定し基準・増加・減少の形状距離を比較。小差/曖昧/非改善はinconclusive。丸め済みの頂点距離を使用し、GLB一般形状や実アドオンの最適設定値、原因確定は推論しない。ソース自動変更、ユーザーアドオン実行を禁止
- `DEC-026` 3D表面距離は双方向・サンプルベースと明記し完全な幾何同一性や内部空洞の証明には使わない。座標一致・同じ頂点番号・同じ三角分割は不要。サンプルが実表面を覆う範囲のみ検査するため微小穴/密閉内部空洞/閉体積/非多様体は証明できない。入力三角面数と座標を制限し、degenerate面は拒否。大きな実ユーザーGLBや非公開アドオンは公開CIに入力・実行しない
- `DEC-027` 表面距離の探索だけBVHで高速化しサンプル密度・距離精度の限界を変えない。AABB下界で三角形候補を枝刈り。真の距離算出には従来の点→三角面処理を使い、総当たり経路と一致を回帰試験。改善は比較回数で示し、ウォールクロックの高速化や任意GLBの完全形状一致を断定しない。Python CPU/Blender3版での合成モデルに限り実行する
- `DEC-028` BVH性能は同一実験入力のウォールクロック中央値と計算回数を分けて記録し高速化倍率を保証しない。同一64面の総当たり結果と3回・交互順序で照合。512面はCIコスト上総当たりを実行せずBVH実時間のみ測定。時間はrunner/CPU負荷依存のため合否閾値を設けず実ユーザーGLBの予測にも使わない
- `DEC-029` 多解像度では差分が大きい面だけでなく未検出面も少数探索し『誤差ゼロ＝同一』と扱わない。粗8/精48点、疑わしい面最大8＋探索2面/方向の上限を固定し、実際の追加サンプル数を報告。面積上位の探索は無差分保証ではなく選択バイアスあり。サンプル数が異なる面の加重平均は単調とは限らず、元GLBアドオンを自動実行/修正しない

## 更新・プライバシールール

- 元の私有アドオンソース、派生レポート、個人情報、認証情報をGitHubに上げない。
- CIの成功は部品の正式承認・ライセンス許諾・GUIの操作感を証明しない。
- GitHubからBlenderへの直接インストールは保留。ユーザーの意思なく実装しない。
- 各節目でdocs/project/STATE.jsonを更新し、この引き継ぎを再生成する。
- 実行: python scripts/project_handoff.py --write
- 照合: python scripts/project_handoff.py --check

## 詳細と正本

- [開発状態台帳](project/STATE.json)（正本、機能・バグ・タスク・CI）
- [最新の開発仕様](PROJECT_SPEC.md)
- [実装履歴](PROGRESS.md)
- [開発時の安全ルール](../AGENTS.md)

この文書はSTATE.jsonから自動生成。内容の編集はSTATE.json側で行う。
