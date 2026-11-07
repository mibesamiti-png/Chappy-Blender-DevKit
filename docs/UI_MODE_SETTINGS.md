# UI-001 / BUILD-001 — 表示条件と設定範囲の宣言

2026-11-08 JST。固定5自作機能・6レシピの開発用プレビューが対象。
未知operator/任意Python/RNA型の指定や、ライセンス/正式採用の自動承認は行わない。

## セクション表示条件

`catalog/ui_layouts.json`のセクションに`visible_in`を省略可能で追加。
値は`always`（既定）、`object`、`edit_mesh`だけ。Python式や自由なmode名は拒否する。
表示条件が所属機能の必要モードと矛盾して操作を到達不能にする場合も生成前に拒否する。
表示だけを切り替え、登録する機能/依存/active object/モード/メッシュは変更しない。

既存カタログは省略時の従来表示を保つ。下は編集セクション内の例で、他の許可済み
機能も従来どおりカタログ内に全件保持する必要がある。

```json
{
  "id": "edit",
  "title": "Edit Mode",
  "visible_in": "edit_mesh",
  "controls": [
    {"feature_id": "edit_selection", "label": "Selection Counts"},
    {"feature_id": "vertex_nudge", "label": "Nudge Vertices",
     "parameters": {"offset": {"default": [0, 0, 0.125], "min": -1, "max": 1}}}
  ]
}
```

全セクションが隠れるmodeでは説明を表示する。未対応modeの空表示は模擬contextでも確認し、
実Sculpt GUI操作の証拠とはしない。既存の助言UI/実行時監査の境界は維持する。

## 共通の設定検証

従来の`offset: [X,Y,Z]`を維持し、`default/min/max`形式も受け付ける。
型float-vector・要素数3・上限±10はコード側の契約。宣言で型/サイズ/上限を変更できない。
範囲を狭める場合は有限の数値・順序・ゼロを含む範囲を必須とし、初期値は宣言範囲内の
非ゼロベクトルでなければならない。bool/NaN/範囲拡大/未知キー/範囲外初期値は拒否。

生成時は不正な初期値を黙って補正せずZIP作成前に失敗する。実行中のScene入力は
Blender標準RNAにより宣言範囲へ制限される。直接operatorを呼ぶ際の固定±10契約は変更しない。

## 生成前レビューと生成物の記録

```text
python -m cbdk addon-plan --recipe recipes/modular_all.json --with-ui --output reports/latest/ui_plan.json
```

新オプションで表示条件/設定計画を静的JSONへ追加する。ZIP生成・Blender実行は行わず、
`runtime_verified=false`/`approved=false`を維持する。省略時の旧出力形式は変えない。
生成ZIPのCBDK_BUILD_INFO.jsonにもui_optionsを保存し、実機smokeで読み込んだ計画と照合する。
記録はレビュー用で、source真正性やライセンスの証明ではない。

表示名/ラベルがテンプレート置換語を含むと生成失敗になる既存不具合も修正。
元テンプレートだけを一回の置換で処理し、挿入された文字列を再置換しない。
回帰テストは失敗を再現後、AST上で表示名/ラベルが文字列として保たれることを確認した。
通常の追加UI例は修正前後でZIPがbyte-identicalで、ローカルBlender検証結果を維持した。

## 検証状態と限界

ローカルPython830件成功。Blender4.3.2でObject/Editのセクション切り替え、範囲±1の
入力制限、既存operator動作と登録解除を確認。これは対象3版の代替ではない。
今回の対象CIは未実行。最新の実測はSTATEと本書の追補を参照。
汎用UI全体・実Windows GUI/Undo・実データ/権利・正式Extensionは未確認で、全体partialを維持。
