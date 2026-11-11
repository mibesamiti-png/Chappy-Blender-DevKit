# CBDK Development Intelligence Lab — DIL-01

**提案・独立研究・正式採用なし。** 2026-11-11 JST。
「AI自律開発・3Dモデリング支援エンジン」というユーザー決定の長期目標を、GitHub正式方針へ反映するための仕様・ロードマップ・変更箇所案。v0.18〜v0.22を維持し、その先の製品像として整理する。

## 読む順番

1. [長期仕様案](SPEC_PROPOSAL.md): 自律/共同制作、対象単位の操作権、中断/復旧、進捗、高度AI非依存、受け入れ条件。
2. [ロードマップ案](ROADMAP_PROPOSAL.md): 現行計画との関係、段階導入、候補/停止条件。
3. [A向け反映案](INTEGRATION_PROPOSAL.md): 正式ファイルの変更位置・挿入文言・STATE候補・生成HANDOFFの扱い。未適用。
4. [現状調査と技術比較](RESEARCH.md): 最新PR/CI、既存実装、出典、重複回避。
5. [DIL-01実測と限界](RESULTS.md): 状態鮮度の小試作、失敗・未検証・次候補。

## 所有範囲・引き継ぎ

- Task `RESEARCH-DIL-001`、branch `research/development-intelligence-20261111`。
- base `feature/v0.18-shape-diagnostics` @ `8665a3c136ae81efbd28a820e7de50ef6ee59332`。
- 書込は `research/development_intelligence/**` のみ。STATE/HANDOFF/AGENTS/共通開発規則/CI/scripts/catalog/本体/ABCD枝/Geometry #114は変更しない。
- 添付方針は要件として整理した。添付原文・私有モデル・ログ・個人パス・認証情報は公開しない。公開GitHubメタデータと新規人工fixtureのみ。
- 研究は会話中に実行する。終了後の常駐処理・自動学習・スケジュール実行なし。

## 再現（Astra・LLM・ネットワーク不要）

Python3.11+（今回3.12.14）、SQLite JSON関数が必要。Nodeは既存dashboard probeのみ。追加pip依存なし。

```bash
cd research/development_intelligence
python -m unittest discover -s tests -v
python verify_sql.py
mkdir -p runs
python benchmark.py --output runs/new-result.json
python probe_dashboard.py
```

既存結果を上書きしないようbenchmarkは新規出力のみ。`FROZEN.json`の4hashを検査してから実行する。prototypeは `observe(record, expected, now)` の純粋APIで、dictの厳密キーはsource/fixture参照。全時刻は同じ時計系の整数秒、TTLは仮値snapshot300秒/heartbeat30秒。入力revision等は呼出側で信頼性を確保する。常にedit_authorized=false。

## 再開手順

最新dev/main/このDraft/関連PRのHEADとCIを取得→本READMEとRESULTS/反映案を読む→Aの採択状況を確認→未解決候補を1つ選び予算/独立判定/未使用例を事前固定→研究範囲で実験。A承認/反映が済んだと推定しない。既存ABCDとGeometry Labを再編しない。

今回: 仕様案完成、DIL-01ローカル実験完了、本体導入保留。未使用12件の根拠不足の直近観測判定はstatus-only8件/TTL-only7件/提案0件。実環境の品質・速度・負担改善は未実証。次は安全なcheckpoint/所有権移行のシミュレーションと実行観測の信頼境界。
