# CBDK v0.10 — サンプルアドオン自動組み立て

## 目的と現在の範囲

既存のCBDK自作ヘルパー3件（BLCTX-001/002・BME-001）を、安全な固定レシピに従ってZIPにまとめ、**自分のPCでのみ試す開発プレビュー用のBlenderアドオン**を作る。

作成するのは `CBDK Mesh Inspector Preview`（3D View > Sidebar > CBDK）。Object Modeで選択メッシュ数、Edit Mesh Modeで選択頂点・辺・面の数を表示する。元の選択状態、モード、トポロジーには手を加えない。ただし画面に最後の検査文字列を表示するため、シーン内の一時的な文字列プロパティだけは更新する。

## 生成する

リポジトリルートからPython 3.11〜3.13で実行。

```bash
python -m cbdk build-addon \
  --recipe recipes/mesh_inspector.json \
  --preview-unapproved \
  --output dist/CBDK_Mesh_Inspector_Preview.zip
```

- `--preview-unapproved` を**明示しない限り生成を拒否**。現在のCBDK部品は `approved=false` / `license_review=pending` であり、配布許可・正式採用の根拠がない。
- 実行スクリプトや外部アドオンを引数で受け付けない。許可済み部品ID・許可済みソースと固定テンプレートのみパッケージ化。
- ZIPには `cbdk_mesh_inspector_preview/` フォルダが1つ入り、`__init__.py`、`helpers/context.py`、`helpers/edit_mesh.py`、出典ハッシュ入り `CBDK_BUILD_INFO.json` などを含む。
- 同じ名前のファイルは上書きしないので、新版を生成するときは保存先の名前を変更するか以前の出力を手動で管理する。
- **Blender Extensions（新しい形式）ではなく、レガシー形式の開発プレビュー**。正式な配布用Extensionはライセンス・部品採用の確認後に別途実装する。

## 自分のBlenderで利用

Blender 4.4.3以降で、編集 > プリファレンス > アドオンから「ディスクからインストール」／「Install Legacy Add-on」を選び、上記ZIPを選択して有効化する。3DビューのNパネル（サイドバー）に「CBDK」タブが出る。選択メッシュ数または編集メッシュの選択V/E/Fを確認できる。

既存の公開アドオンや日常使用の .blend はこのサンプルでは変更しない。ただし開発プレビューなので、大切な作業シーンでいきなりテストするのは避ける。

## クラウド自動検査

`.github/workflows/blender-smoke.yml` は公式Blender 4.4.3、4.5.15、5.2.1をSHA-256で確認し、プレビューZIPを生成した後、`scripts/blender_generated_addon_smoke.py` で一時フォルダからロードする。

検査内容：
1. ZIPの構造とプレビュー用メタ情報
2. アドオンの有効化とPanelの登録
3. Object Modeでメッシュ1個の数え上げ（ライトは無視）
4. Edit Modeで三角メッシュの選択V=3/E=3/F=1、モードが変化しないこと
5. アクティブメッシュなしの拒否
6. アドオン無効化後のPanel/Sceneプロパティ消去

テストは仮想のBlenderユーザー環境で動き、本人のPCのUIを自動操作するものではない。ZIPを手動でインストールした場合の見た目、他アドオンとの競合、性能は別途確認が必要。

## 安全上の境界

元の外部アドオンはコピー・実行しない。既存の `catalog/authored_parts.json` の正式採用状態も変更しない。出力される開発用ZIPは、正式公開・一般配布に用いない。
