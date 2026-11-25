# NEXT-008/009 — 双方向の調査順と設定候補の不確実性

2026-11-07。正本はSTATE。現行タスク内の改善で、GLB-020測定MVPの上限やアルゴリズムは変えない。

## 実装範囲

既存`glb-visual-property-review --markdown`のJSON/Markdownへ`debug_focus`を追加した。参照・生成の各側で既に測定された黄/赤面数を別々に保持し、表面差分→赤面割合→黄赤合計割合の順に調査対象を整理する。分母は三角形数であり面積/確率/信頼度ではない。並び替えはFractionの有理数比較、表示だけ小数7桁。側と匿名IDを必ず併記する。

生成側に候補がなくても参照側だけの差分を表示する。同じ匿名IDを同じ部品とみなさず、既存の一意なsuggested対応だけを未確認peerとして引き継ぐ。境界辺数が同じという観測だけでは差分にしない。対応が曖昧な境界はunpaired observationとして残し、穴の位置を断定しない。差分なし一覧も無欠陥保証ではなく、次の実験で再確認する観測の控えである。

AST側では、importされたbpyプロパティconstructorの別名に別の代入/定義/削除/importがある場合、またはクラス内で隠されている場合は、宣言根拠として採用しない。条件付き代入や後の代入も安全側に除外するため見逃しはあり得る。動的束縛の完全解析ではない。

## 設定候補と実験の統合レビュー

既存の測定元SHA結合レビューを作った後、次のCLIで私有JSON/Markdownを作る。

```text
python -m cbdk.glb_experiment_triage --visual-review <GLB-020 review.json> --linked-review <bound AST/experiment review.json> --output reports/latest/experiment_triage.json
```

原本のAST再実行・Blender起動・次の試行起動・設定値適用は行わない。既存の検証済み集計/結合レビューを再検証し、測定元SHAと対象の観測数を照合する。旧結合レビュー形式は変更しない。

同名候補の宣言が複数あれば`multiple_static_declarations`と宣言数を示す。参照数や構文上の形状経路は候補名全体の集計なので、それだけで宣言を選ばない。宣言1件でも実行時の実体/登録/効果は未証明。候補なしも原因不存在ではない。

距離変化は全体の双方向サンプル最大、面数変化は生成側socketの分類面数で、どちらも直前の検証済み試行との差。特定部品の局所距離や採用済み最良値との差に読み替えない。失敗/未完了prefixはその状態のまま表示し、因果・実行完了・最適値・完全一致を認定しない。

出力は新しいignored `reports/latest/*.json`と`.md`だけ。衝突・脱出・不正な安全フラグ・偽の候補選択/変化量を拒否する。候補名/クラス名を含むのでGitHub/Notion/公開CI artifactへ送らない。stdoutは件数とfalseの因果フラグのみ。保存済み要約は元GLBやソースの真正性を認証しない。

## ローカル測定と限界

- Python3.12.14：関連検査成功。全体最終件数/CIはSTATEの今回節目を参照。
- Blender4.3.2：新しい自作GLBの4試行適応実験と模擬timeoutの失敗実験を生成し、既存verifierで完了/未完了/失敗の双方向socket focusと2宣言の曖昧さを確認。対象3版の代替証拠ではない。
- 既知のconstructor別名shadowing負例4件：旧の名前だけのconstructor判定4件、変更後のinventory0件。通常の別名と無関係な関数内変数は保持。任意アドオンのprecision/recallではない。
- 実GLB集計を使う統合レビュー構築7回：中央値0.00449秒、最大Python割当28,130bytes（tracemalloc、RSSではない）。速度最適化とは主張しない。
- 参照側だけの差分、等しい開放境界、異なる部品ID対応、面数で正規化した調査順は制御されたPythonケースで確認。任意の細穴・内部空洞・実ユーザー・面積精度は未検証。

NEXT-008/009全体は継続。NEXT-002 GUI、実データ使用/実行、ライセンス/正式採用、現行UI-001/Extensions準備は未完了。将来計画は承認済みだが現行の自動化残作業があるため未有効。

## 対象CI確認済み

コードb17fa4d5803a9d89eb104b318423ac27883c7dfbでPython787件×3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1とKit/Handoff/Chromiumの全6CI成功。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909052)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909091)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909099)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909006)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909079)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42374909009)。全Blender版で双方向socket focus、複数宣言未選択、完了/未完了/模擬失敗、測定元不一致拒否と原本SHA不変を確認。

今回20件を追加し、787件の回帰を各環境で確認。既存ソース/原本/私有データは自動採用せず、私有triageはreports/latestに限定したため公開CI artifactへ含めない。コード後の文書コミットを新しいコード実測と扱わない。


## R17 — 実用的な一箇所の確認レビュー

正式割当 `docs/R17_ABCD_START.md` の B NEXT-008/009・GLB-021/022。
基点 `22dcb04b70f2e4ae0dc3c4780bab266db0a7fb70` はR16統合・R17節目同期・独立7CIとIssue #125 revision 2のR17 normalを確認済み。

既存CLIとv1 JSON形式は変更せず、非公開Markdownを改善する。従来は調査順、候補名と宣言数、試行の変化量が別々に並び、具体的な宣言位置、進捗判定、未検証枠、停止理由を確認するために元の結合レビューを開く必要があった。

- 調査順の側/部品ID、黄赤面数と分母、境界辺、暫定対応を併記。生成側候補に限定し、参照側の同名IDに設定を転用しない。
- 候補の匿名宣言位置、複数宣言/単一未確認宣言、候補名全体の静的参照・形状経路件数、名称による合成操作対応と次の人手確認を同じ部品欄に表示する。宣言や値は選ばない。
- 合成試行の実測集計値、直前との差、既存の最良値に対する進捗採用/棄却と理由、目標内外を区別。未完了/失敗、未検証枠、処理対象、観測履歴の停止理由、目標内候補の有無を明示する。
- 失敗時は既存の固定診断アクションを再利用し、未完了時は終了証拠の確認を促す。再試行は入力/条件/出力先と別の実データ利用許可を確認して人が判断する。

利用コマンドは上記と同じ。既存の保存済みtriage JSONも同じrendererで検証・表示できる。既存の新規ファイル限定、2MiB上限、stdoutの匿名件数、入力照合、安全フラグを維持。公開用匿名triage（R14/R15/R16）へこの私有宣言情報を渡さない。

テストは既存の自作合成fixtureを利用し、完了した採用/棄却/目標内の混合試行、単一/複数宣言、0/1試行の失敗/未完了prefix、既存の矛盾拒否と私有出力を検証する。R17専用の新規実データや研究APIは不要。既存Blender 3版CIは従来の合成反復・GLB接続の実測として別に確認する。私有GLB/実アドオンの登録実体・形状因果・設定値最適性・全域一致・Windows GUI・権利は別の人間/実環境ブロッカーであり、ここでは完了としない。
