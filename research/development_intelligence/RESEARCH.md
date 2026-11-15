# DIL-01 調査と選定

## 調査時点

2026-11-11 JST。公開GitHub APIとgit fetchで更新。基点dev `8665a3c136ae81efbd28a820e7de50ef6ee59332`、main `c5b63ba50f4f53e22dea3ddc72486a17aa9dd939`。正式版はpyprojectの0.17.0、v0.18はDraft #25。指定のAGENTS/PROJECT_SPEC/STATE/HANDOFF/PARALLEL_DEVELOPMENT/ROLLING_QUEUE/R14割当/Astra R11-R12記録/未来019-022を読み、実装と照合した。

公開PR/最新HEAD別workflow結論は [github_snapshot.json](results/github_snapshot.json)。#25は7系統、R14 B#107/C#108/D#106と速度改善A#109は各5系統、Geometry #114は4系統successをAPI再確認。全てDraft/open。R13統合済みとR14未統合を区別する。今回は全matrixログを再認証したのではなく、exact-head workflow結論の取得。個別CI成功をR14統合成功とはしない。

## 既存設計との差分・重複防止

|根拠（基点またはPR）|既存でできること|長期像との差分/今回の扱い|
|---|---|---|
|PROJECT_SPEC/STATE、`scripts/project_handoff.py`|状態正本、生成引き継ぎ、CI/実装/許可の分離|維持。新しい状態正本は作らない|
|`docs/dashboard/index.html`とREADME|5分/手動の公開GitHub読取、HEAD一致CI、工程表示、更新エラー|executor生存や3D操作権は扱わない。時刻/読取表示は再利用候補|
|`docs/GLB022_RUN_REVIEW.md`、`cbdk/glb_synthetic_run_review.py`|有効な途中prefix、失敗・incompleteの保存、非実行のレビュー|既存checkpointを尊重。一般のクラッシュ復旧・自動再開・所有権移行とは別|
|#109 `5dc2080`の `scripts/ci_cycle_metrics.py`, `scripts/abdc_preflight.py`|CI時間集計、HEAD/matrixの事前確認、checksum付きcache|同じ収集器を作り直さない。まだdev未統合|
|`docs/ASTRA_COORDINATOR_R11_R12_BENCHMARK.md`|実測時刻、7件の重複dispatchを失敗記録、モデル推論量は未測定|高度AIの優劣は断定できない。集計/監視を通常ツールへ移す根拠|
|#113 `75cb752`の `docs/research/MODELING_KNOWHOW_INTAKE.md`|出典/版/権利/実験段階の取り込み仕様（docs-only）|検索索引は別研究候補、現存する知識手順を複製しない|
|#114 `b21da70` Geometry R4|合成・CGAL・2版で接続品質比較、自作DPの不採用記録|研究APIは未採用のまま。停止/改変/移設しない|

現行ライブボードの実コードを既存テスト同様のNodeオフライン環境で実行すると、CI欠損の担当PRは内部state=running、説明は「未確認・実行中を含む」。これは工程状態の設計であり、誤ってプロセスの生存証明に転用しないことが課題。今回の簡略baselineとライブボードを同じ実装・目的だとは扱わない。

## 候補と選定理由

|候補|価値・証拠|コスト/制約|今回|
|---|---|---|---|
|状態の鮮度/attempt/revision照合|進捗表示と権限の誤認を防ぐ基礎。現行表示は工程単位|小さな純粋関数と固定負例で比較可能|選択|
|知識検索/要約キャッシュ|毎回の全文入力を減らす可能性|検索goldと欠落による品質低下の測定が必要|次候補|
|CI集計/待機短縮|重複dispatchの実記録あり|#109で既に実装中、並行重複を避ける|再利用調査のみ|
|操作権・復元|人間とAIの安全な切替に必須|実Blender/OS/保存の故障注入が必要|契約設計のみ|
|チーム数変更|待機削減の仮説|難易度揃えた比較なし、正式再編権限なし|shadow比較案のみ|

## 技術資料・比較

- [Kubernetes Leases](https://kubernetes.io/docs/concepts/architecture/leases/): heartbeatとleader electionにleaseを利用。renewTimeを観測する考えを参考にする。Kubernetes導入は過大であり今回は使わない。lease期限と旧writer遮断は別途設計する。
- [Git update-ref](https://git-scm.com/docs/git-update-ref): old-oid一致時だけref更新する比較交換、複数ref transaction。revision照合の根拠。未commitファイル/.blend全体への排他はこのAPIだけで解決しない。
- [GitHub Actions runs API](https://docs.github.com/en/rest/actions/workflow-runs): run/status/conclusion/HEADの取得。ジョブ終了時刻は別途jobsから取得する必要があり、updated_atだけを正確な終了時刻と呼ばない。
- [SQLite FTS5](https://www.sqlite.org/fts5.html): 全文索引、BM25、tokenizer。将来の知識検索候補。日本語の分かち書き・trigramと検索精度の検証は未実施。
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html): サーバ不要DBを標準APIから利用。今回の独立判定はin-memory SQLite JSON述語。性能優位を主張しない。
- Blender公式recover資料はアクセス制限で本文を取得できなかった。自動保存/Undoの完全復旧保証を引用していない。Fowler fencing-token記事も取得不可で根拠には採用しなかった。

|操作権候補|長所|不足/失敗条件|方針|
|---|---|---|---|
|単純ファイルlock|容易、単一ホスト向け|クラッシュで残留、非協調アプリの書込を防げない|単独では不足|
|revision比較/CAS|古い基点の上書きを検出|保存前の作業重複・外部副作用は防げない|採用候補|
|lease+世代token|所有者の変更と旧writerの識別|全writer側のtoken検査が不可欠。TTLだけは危険|将来の限定実験|
|immutable checkpoint+履歴|再開根拠、失敗の監査|保存完了/読戻し/容量/依存asset整合が必要|既存GLB方式を参考に拡張|

知識方式は、JSONL/ファイル索引（単純だが全走査/関連検索が弱い）、SQLite/FTS5（版/条件との結合が容易、tokenizer依存）、意味検索（言い換えに強い可能性、モデル/費用/誤検索）、要約cache（入力削減、根拠欠落/鮮度問題）を候補にする。hash重複排除は同一bytes用、類似検索は同一意味を証明しない。未測定なので方式を正式選定しない。

実装は自作Python標準ライブラリのみ。CPythonはPSF、SQLiteはpublic domain、Nodeの検証runtimeはMIT系ライセンス。外部ソースのコピー/バンドル、新規有料依存なし。リポジトリ全体のライセンス未決定を本研究で変更しない。
