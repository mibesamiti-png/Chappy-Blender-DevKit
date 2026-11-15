# DIL-02 — Minimal-Sufficient Decision Gate / 事前登録

2026-11-11 JST。独立研究の提案ゲート。**CBDK本体への導入・AI実行制御・操作権認証ではない。**

## 候補比較と選択

|候補|価値/証拠|負担・競合|選定|
|---|---|---|---|
|① checkpointと旧writer遮断|高価値、ただし実runner故障注入環境未整備|高|次サイクル|
|② 指示・裁量・終了条件|ユーザーの新たな直接課題、人工ケースで反証可能|小・独立|今回|
|③ 軽量検索|潜在価値高、検索goldが必要|中・#113参照|次候補|
|④ ABCD待機/CI重複|現実に重複dispatch履歴あり|#109が既に計測器実装|#109を再利用|

これは効果の実測点数ではなく、証拠・実装費用・独立性による定性的比較。

## 事前目的・評価基準・予算

目的: (a) 人間のアイデアを採用確定と誤認しない、(b) 必要条件/予算を守り、必要十分な最小工数案を選ぶ、(c) 同じgoal revisionで受入済みなら無限改善しない。正式な採否・人間の評価を置換しない。

比較: 開発12例 + 未使用12例の人工例。事前に手作業でgoldを決め、最新案追従 `idea_first`、品質数値最大化 `quality_max`、提案ゲート `decision_gate` を同じ24例で比較。**baselineはわざと単純化した架空方式であり、CBDK現行版や実LLMの比較ではない。** Goldは同一研究者が作成しており、第三者blind評価ではない。

合格: 未使用12例の正解一致 >=10、両baselineそれぞれより3件以上多い、予算/必須ゲート違反0、最新受入済みへの不要追加作業0。失敗時は不採用。未使用評価後の修正0回。

予算: Python標準ライブラリ、人工24件・12 unittest・holdout1回・評価最大60秒。元DIL-01の凍結済みコードやfixtureを変更しない。両fixture・実装・benchmark・testのSHA256を初回holdout前に`FREEZE.json`へ固定する。合格後の追加機能開発はしない。

## 入出力と信頼境界

- `mode=idea`: 技術案は仮説。候補比較で優遇しない。`mode=adopt`: 明示採用だが、必須制約/予算を超えたら`escalate`（代案へ自動すり替えしない）。`mode=continue`: 最小十分案を評価。
- `goal_revision`が最新で受入検査合格、かつ`evidence_fresh`なら`stop`。証拠だけ古い場合は`verify`。仕様変更はrevision更新を必要とする。
- `fits_goal`, `gates_passed`, `effort`, `complexity` は外部からの宣言値。必須ゲートを通過した案から工数、複雑さ、IDの順に最小化。申告`quality`が高いだけの案は追わない。
- 入力された判定値・見積もりが**正しいこと自体は検証しない**。自然言語の意図判定、実データチェック、AIの指示遵守、実runner生存/編集権限は未実装。返却は提案のみで、自動的に操作をしない。

## 再現

Python 3.11+、外部パッケージ/ネットワーク/Astra不要。研究directoryで以下を実行:

```bash
python -m unittest -v test_decision_gate
python benchmark.py --output runs/dil02-new.json
```

出力先は新規ファイルを指定すること（上書きしない）。benchmarkは`FREEZE.json`でコード・fixture変更を先に拒否する。Windowsの作業では出力ディレクトリを事前作成すること。

参考資料（実験効果の証明ではない）:
- https://www.anthropic.com/research/building-effective-agents
- https://developers.openai.com/blog/eval-skills
