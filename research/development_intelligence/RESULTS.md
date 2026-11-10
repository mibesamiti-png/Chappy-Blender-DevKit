# DIL-01 実測 — 状態鮮度の読取試作

2026-11-11 JST。Python3.12.14 / Linux、SQLite3.53.1、Node v24.22.1。全入力は新規作成の人工記録。私有ファイル・実モデル・実ユーザーログを読み込まない。

## 実装と実験予算

`prototype/status_view.py:observe(record, expected, now)`は、仕事/対象/attempt/revisionの一致、型、工程数、snapshot TTL、別のheartbeat TTLを照合する純粋関数。出力は固定理由コード・鮮度・申告工程数、`edit_authorized=false`、`eta=null`。入力不変、ネットワーク/ファイル書込/実プロセス操作なし。現在時刻/期待するIDは呼出側が信頼できる方法で渡す必要がある。

実装/fixture/benchmarkのSHAを初回holdout評価前にFROZEN.jsonへ保存。開発12ケース、未使用評価12ケース。最大60秒/benchmark、各方式7反復×100回×12件（同じケースの計時反復であり独立標本ではない）。モデル調整はholdout後0回。不一致・予算超で打切り、合わない結果を隠さない。SQLite照合は24件1回、旧dashboard probeは2シナリオ1回。計測はローカルのみ。

## 数値比較

正解は「指定attempt/revisionについて直近の実行観測が記録されているか」。プロセスが今も動いているという真値ではない。ラベルは実装の戻り値で生成せずfixtureに明記。独立SQL述語（Python評価器をimportしない）でも24/24一致。ただし設計者が同じ人工例であり第三者blind検証ではない。

|方式|開発FP/FN（12件）|未使用FP/FN（12件）|未使用1件中央値|Python peak allocation|
|---|---:|---:|---:|---:|
|status文字列のみ|7 / 0|8 / 0|0.086 µs|48 bytes|
|status + snapshot TTL|5 / 0|7 / 0|0.162 µs|48 bytes|
|ID/版/heartbeat付き評価|0 / 0|0 / 0|7.180 µs|1966 bytes|

FPは根拠の足りない記録を直近観測ありと表示、FNは直近観測を落とす件数。未使用12件の正例は2件。負例に偏るためこの比率を実運用の誤表示率へ一般化しない。新方式は約44倍（TTLのみ比）遅く、**高速化成果ではない**。単一記録はmicrosecond規模だが本番のUI/ネットワーク/保存負荷は未測定。計時とtracemallocは別実行、native/RSSは測っていない。

compact JSONの人工記録は204〜218 bytes（予定プレビュー/ログを含まない）。60秒更新・1対象・24時間保存なら最大約314 KB/日のpayloadという算術見積りであり、実測のディスク使用/書込時間ではない。実更新頻度、保存容量、ネットワーク、モデル編集への影響は未測定。

## 現行方式との関係

`probe_dashboard.py`は基点の実HTML内の純粋関数を既存テスト同様のNode stubで実行。CI情報のない担当PR1件は内部state=running（説明には未確認を含む）、統合PRなし/担当なしはwaiting。2ケースの観測はresults/dashboard-probe.json。現行の工程ラベルがプロセス生存を意味しないことを確認した。**上表のstatus_only/ttl_onlyは比較用の簡略方式であり、現行CBDK全体を置き換えた性能比較ではない。** 既存ボードも未確認の説明を表示しており、実利用者の誤認を観測した証拠はない。

## 成功・失敗・未検証

- 4 unittest成功。型不正、入力不変、権限不付与、未知項目の診断への漏出防止、設定不正を確認。benchmark24ケースとSQL oracle24件は別検証。
- snapshot TTLだけではfreshな記録に紛れた古いheartbeat、別仕事/対象/attempt/版を見抜けなかった。heartbeatとrevisionを組にする価値を限定実証。
- 本試作は監視runner、操作権lock、checkpoint保存、復元、GitHub/Blenderアダプター、UIを実装していない。artifactを実際に検証しないため工程数は`declared_verified`、終端状態は`reported_*`と呼ぶ。
- heartbeat欠落はunknownであって死亡・停止ではない。直近heartbeat後に落ちたプロセスを今も生存中と保証できない。信頼境界/署名/単調sequence/時計同期/通信断の実試験は未実装。
- 同じattempt内の過去snapshotのreplay防止には永続的なsequence下限が必要。今の関数はTTL内のreplayを区別しない。編集許可用途には使わない。
- 実Blender各版、Windows、実ジョブキャンセル、電源断、ディスク不足、人間編集後の復元、検索精度、AI tokens/費用、人間介入数、ABCDの壁時計改善は未測定。コード量・テスト数増加を制作能力向上としない。

## 採否と次

**研究継続・本体導入は保留**。Aに仕様差分を提示する材料として有用だが、製品機能採用や「安全な自律制作完成」の根拠ではない。次はsequenceを含むcheckpoint/引渡しの故障注入、信頼できるexecutor観測の取得方法を比較する。今回のholdoutは以後回帰用とし、新しい未使用シナリオを分ける。

Astra/LLMなしで、固定記録の評価・SQL独立照合・単体テスト・再測定を通常Python/Nodeで実行できる。実運用でAI利用量を削減したという測定はまだない。通常ABCD・Geometry Labには影響を与えていない。

## CIの範囲

本PRの通常CI結果はPR本文に最終HEADとともに記録する。共通CIは変更していないため、新研究ディレクトリの4テスト/benchmark/SQLは自動配線されておらず、**ローカル検証**。既存Python/引き継ぎ/browser CIの成功を研究コードのCI成功として数えない。独立研究CIの配線はAへ別途提案可能だが今回追加していない。
