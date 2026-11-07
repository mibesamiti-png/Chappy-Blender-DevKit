# EXT/UI集中実装の検証記録（2026-11-08 JST）

機能実装8d28b69を含む統合HEAD 63bddb9dcd47ca985995f000efb06b14f056a2cfでPython820件×3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1とKit/Handoff/Chromium/Skillの全7系統成功。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761850)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761797)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761748)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761811)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761787)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761776)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42385761778)。

- EXT-001: 必須項目の未入力/構造不正とowner/license/承認待ちを分離。ZIPの部品ID/同梱helper閉包も照合。実ZIPはpreviewのまま。
- 公式validatorはコードを実行しないデータ専用の合成3例だけで検証。例示SPDXはCBDKや部品へのライセンス決定ではない。実Extensionの生成/公式検証/登録/配布は未完了。
- UI-001/BUILD-001: row/column・枠・型/値域付きXYZ初期値、重複登録/foreign Scene property衝突の拒否、部分登録の後片付けと再登録を実機確認。既存6レシピと追加の一時コピーした自作UI例を検証。任意operatorや私有コードは未採用。
- 描画: 各版の実Blenderレンダリング13枚を4方向の参照/比較に並べ、SHA/サイズ目録を保存。frontのPNGが異なることも確認。実Chromium4枚も成功。画像生成AIは不使用。私有モデルはCIへ含めない。
- ローカル補助証拠: Blender4.3.2とPython3.12.14。preflight7回中央値0.002712秒、最大Python割当1,144,822bytes、15同梱ファイル。tracemallocでRSSではなく、性能改善の主張はしない。

## 同時更新とCI履歴

機能実装後に同じブランチへスキルv1.1.0の更新6ae6545が加わり、旧Blender実行がconcurrencyで取消。6ae6545ではスキル文書の参照不足でPython/Windows失敗、7437c52では包装CIの旧v1.0.0固定値で失敗。文書/包装CIは同時更新側の7437c52/63bddb9で修正済み。すべてを取り込み、最新63bddb9で7系統を確認した。取消/失敗した旧実行を成功と記録しない。文書だけの後続コミットにコード実測を帰属させない。

## 到達点と再開点

23タスクは18完了/4継続/1保留、43要件は26実装済/15一部/1未実装/1保留を維持。今回新規完了IDなし。EXT-001/UI-001/BUILD-001の自動化を拡充したが、実Windows GUI/Undo・権利/ライセンス・実ユーザーGLB/設定因果・正式Extensionは未確認。

次は現行UIの操作不可理由表示と、選択状態を含む安全なガード、プロパティ登録失敗時の復旧など残る自動化を優先。汎用UI/Extensionsの未実装と人間待ちをさらに整理する。現行自動化完了ゲートはfalseで次世代計画は承認済み・未有効。開始承認の再取得は不要だが、mainマージ/正式公開/未承認採用/私有データ利用/直接インストールの保留解除は別承認。
