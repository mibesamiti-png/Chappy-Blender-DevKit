# UI-001 / BUILD-001 — 判定理由とプロパティ登録失敗の検証

2026-11-08 JST。コードeac7453b3e052267c45a83fa7c47180882d02419でPython823件×3.11/3.12/3.13、Windows3.11/3.13、Blender4.4.3/4.5.15/5.2.1とKit/Handoff/Chromium/Skillの全7系統成功。[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411841)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411842)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411863)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412044)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412165)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388411889)、[Skill](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42388412036)。

## 実装と検証された範囲

- 固定5自作機能のパネルでactive mesh/モードの理由を表示。頂点移動では既存edit helperと構造/offsetの判定を共有し、選択なし/ゼロ値/共有データ/shape keys等で実行を止める。
- XYZ入力と実行ボタンの有効状態を分離し、適切なモードではゼロ値を修正できる。
- UIはMesh.total_vert_selを読むだけでBMeshを取り込まず、頂点/座標の走査・コピーをしない。これは助言であり、RNAが古ければexecuteが実選択を再検査して拒否する。元の数値・トポロジー・資源上限監査は維持。
- StringPropertyとFloatVectorPropertyの各factoryへ制御された失敗を注入。前者は割当前、後者は最初のScene property割当後の失敗で、いずれも所有プロパティ/登録クラスの後片付けと再登録に成功。自然発生OOMや任意の障害を再現したとは言わない。
- 各対象Blender版で既存6レシピ+追加UI例を検証。旧のクラス登録失敗/二重登録/foreign Scene property保存のテストも保持。ログはtee/grepで同じJSONが二重表示されるため、別試行として数えない。
- Pythonの新規3テストは、BMeshなしの助言・構造ガードの共通拒否・古いRNAが実編集を許可しないことを検証。全体823件成功。

## ローカル負荷観測

Blender4.3.2の自作grid、9頂点と5,041頂点で助言関数を各7回×100呼出測定。中央値は各0.01314ms/0.01240ms、最大Python割当7,680/6,912bytes（tracemalloc）。プロセスRSS/native全割当ではなく、速度改善や任意大規模メッシュの保証ではない。UI表示そのものの実GUIフレーム速度でもない。

## 未確認と再開点

実Windows GUI/ショートカット、任意実プロジェクト、クラッシュ/任意障害時の完全な原子性、権利/ライセンス/正式Extensionは未確認。プレビューの助言を実行承認やソース正式採用に昇格しない。

23タスク18完了/4継続/1保留、43要件26実装済/15一部/1未実装/1保留を維持。新規完了IDなし、UI-001/BUILD-001全体partial。次は現行UI宣言のセクション表示条件/共通設定スキーマの残りを、固定自作機能・未知コード拒否の範囲で整理して実装する。実Extension等の残りも自動化とowner待ちを分ける。

現行自動化完了ゲートは未達のため次期計画は承認済み・未有効。移行開始承認の再取得は不要だが、mainマージ/正式公開/未承認採用/私有データ/直接インストールの保留解除は別承認。後続の文書コミットを新しいコード実測とは扱わない。
