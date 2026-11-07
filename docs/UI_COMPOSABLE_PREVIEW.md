# UI-001 / BUILD-001 — モード単位のコントロール構成と安全な解除

2026-11-08 JST。チームCの専用ブランチ `work/v018-ui-builder` の実装レビュー。
従来の5自作機能・6レシピを増やさず、UIカタログのコントロールに
`visible_in`（省略時`always`、またはその機能の固定実行モード）を追加する。

## 例：同じセクションにObjectとEditの操作を配置

```json
{
  "id": "quick",
  "title": "Quick tools",
  "controls": [
    {"feature_id": "object_selection", "label": "Selected Meshes", "visible_in": "object"},
    {"feature_id": "vertex_nudge", "label": "Nudge Vertices", "visible_in": "edit_mesh",
     "parameters": {"offset": {"default": [0, 0, 0.125], "min": -1, "max": 1}}}
  ]
}
```

これは**全5機能を配置したカタログの一部**を抜き出した例。実カタログでは
従来どおり全機能を一度ずつ記述し、固定allowlistにないoperator、任意Python、
実行式、`visible_in`の未知値・機能と反対のモードは拒否する。
セクション`visible_in`も従来のガードを維持する。

生成計画`ui_options.control_visibility`は、レシピで選んだセクション/操作の
表示順に一致する。対象モードでセクション内に表示可能な操作がなければ、
空の枠・タイトルを生成しない。登録対象のOperatorそのものは変えず、実行時
`poll`/executeの検査が最終的に実行可否を決める。従来のセクションレイアウト、
XYZ範囲と旧UIプラン形式は維持する。

## 失敗時復旧

生成アドオンの`unregister()`は、一つのクラス解除失敗でも残りのクラスと
**自分で登録した**Sceneプロパティの解除を継続。解除に成功した項目だけ
所有リストから外し、失敗項目は再試行用に保持する。失敗を正常扱いせず
`RuntimeError`と元例外で通知する。`register()`中に失敗し、rollbackも
失敗した場合は最初の登録失敗を主例外として維持する。

## 検証範囲

`tests/test_ui_composition.py`でモード混在・不正キー拒否・生成ZIPメタデータ・
意図した解除失敗の再試行を検証。既存のUIおよび生成器テストも引き続き実行する。
GitHub Actionsの実測結果が出るまで、Blender対象3版/Windows GUIの合格は主張しない。
未知Pythonコードの実行、実ユーザーアドオンの登録、実Extension生成、正式
ライセンス承認、mainマージ、直接インストールは引き続き行わない。
