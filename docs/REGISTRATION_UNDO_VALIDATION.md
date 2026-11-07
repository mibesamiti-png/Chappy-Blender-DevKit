# NEXT-003 / NEXT-002 登録とUndo/Redo検証

2026-11-07、実装コード `c80f2a0a174a37074c283641ce288a378261e92d`。正式v0.17.0、PR #25ドラフトを維持。最新判定はSTATE。

## 登録整合性

`python -m cbdk.registration_audit` は既存6レシピを破棄する一時ZIPへ実生成し、カタログ/依存閉包、実機smokeのKNOWN一覧、CIの明示レシピループを照合する。`build-addon` 自体も出力作成前に同梱PythonのASTで相対importの閉包・静的export、明示OPERATOR_CLASS、重複ID/クラス名を検査する。欠落・構文エラー・脱出・不一致で失敗し、そのZIPを作らない。原本は変更/実行しない。

静的に明示したexportに限定し、動的exportや実行時登録の完全な証明ではない。実際の登録/操作/解除は既存の6レシピ×Blender3版CIで検証する。部品の正式採用/ライセンス承認は別で、approved=falseとpreview-onlyを維持。CLIは機能/レシピ数・安全フラグだけ出力する。

## Native Undo/Redo

通常背景プローブに加え、明示的な`bpy.ops.ed.undo_push`で基準と編集後の履歴を作る制御ケースを分離する。単一頂点1操作、複数頂点2連続操作でNative Undo→Redoを段階ごとに実行し、座標・辺/面接続・頂点/辺/面選択を完全比較する。RNA/BMeshは毎回取り直す。ゼロoffset取消の無変更も確認する。

schema2は通常背景結果をトップレベルに保ち、制御条件をprepared_stack_casesへ保存する。旧schema1読取互換を維持。重複JSONキー、不正な操作数/状態、GUI成功などの虚偽を拒否する。明示push成功は、通常の自動Undo履歴・GUI Ctrl+Z/Ctrl+Shift+Z・ユーザープロジェクトの検証ではない。

## 今回の検証

- ローカルPython3.12.14: 767件成功（追加15件）。
- ローカルBlender4.3.2: 通常背景Undo不能/Redo未試行。明示履歴2ケースはNative Undo/Redo成功。対象版の代替証拠ではない。
- 対象CI: Python [42368028025](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028025)、Windows [42368028009](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028009)、Blender [42368028022](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028022)、Kit [42368028048](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028048)、Handoff [42368028021](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028021)、Chromium [42368028016](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368028016)。初回の履歴。最新結果は下記を優先。

NEXT-003は下記の対象CI成功で受け入れ完了。NEXT-002はGUI未検証を残し継続。NEXT-008/009は私有データの使用/実行許可と実体・因果の検証が残る。現行UI-001の自動化残作業を整理してから将来計画へ移行する。

## 追加検査の負荷と互換性（ローカル観測）

Python3.12.14、6レシピ一括生成×5回を交互に測定。新AST検査ありの中央値0.1082秒、検査関数だけを一時的に無処理にした対照0.0342秒。最大Python割当ピーク1,213,341 / 486,220 bytes（tracemalloc、プロセスRSSではない）。6レシピ合計で約0.074秒の検査負荷があり、速度改善とは主張しない。両条件・全反復で各ZIPのSHA-256は一致した。自作小規模プレビューだけのローカル観測で、巨大/未知コードの性能保証ではない。安全検査は製品・CIで常に有効にし、対照の無処理化は計測プロセス内だけ。

初回a987c44のWindows CI42368028009では短縮パスを未正規化で渡す2テストが失敗。c80f2a0で監査/直接ビルド入口のroot.resolve()と別表記の回帰2件を追加した。初回Blender CI42368028022は4.4.3成功、後続pushにより4.5.15/5.2.1がcancelledで、3版成功とは扱わない。最新c80f2a0のCIを完了判定に使う。

## 確認済みの最終結果

実装コードc80f2a0a174a37074c283641ce288a378261e92dのBlender4.4.3/4.5.15/5.2.1・Kit/Handoff/Chromium成功。テストだけUTF-8指定を修正したb5d32734d4a74e6acd7ff896baeb3aa3088e661aのPython767件×3版・Windows2版成功。両SHA間の変更はtests/test_registration_audit.pyだけで実装は同一。対象6系統の結果は[Python](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368307965)、[Windows](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368305584)、[Blender](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190461)、[Kit](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190510)、[Handoff](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190490)、[Chromium](https://github.com/mibesamiti-png/Chappy-Blender-DevKit/actions/runs/42368190614)。

全3版の構造化Undoレポートで、通常背景Undo=unavailable/Redo=not_attempted、明示履歴の単一/連続2ケースはそれぞれUndo/Redo=passed、exact_topology_verified=true、cancelled_edit_unchanged=trueを確認。NEXT-003完了、NEXT-002はWindows GUI確認待ちを残し継続。23タスク中18完了/4継続/1保留、要件43件の26実装済/13一部/3未実装/1保留は維持。
