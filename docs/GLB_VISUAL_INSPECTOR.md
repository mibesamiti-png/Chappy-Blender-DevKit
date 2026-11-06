# CBDK GLB Visual Inspector

GLBを「推測で見たつもり」にせず、**構造JSON + Blender実レンダリング画像**を解析根拠にするための開発機能。

## 目的

Blenderアドオンが生成した形状や参考3DデータをChatGPT/Codexへ渡す際、GLBのファイル名や会話文だけで形状を推測すると取り違えが起きる。

この機能は次の2段階で確認する。

1. `glb-inspect`: BlenderなしでGLB 2.0のコンテナ/JSONチャンクだけを静的解析。
2. `glb-preview`: 信頼済みBlenderを `--background --factory-startup` で起動し、実際にGLBを読み込んで4方向PNGとシーンmetadataを生成。

## 1. 静的構造解析

```bash
python -m cbdk glb-inspect model.glb --output reports/latest/glb_structure.json
```

主な出力:

- scene / node / mesh / materialの個数
- node名、mesh名、親子参照
- primitive数
- POSITION / index accessorの要素数
- asset generator
- GLB chunk構成

安全上、静的解析では次を行わない。

- 外部URIの読み込み
- 埋め込み画像のデコード
- Blender/Pythonコードの実行
- GLBを信頼済みアドオンとして扱うこと

## 2. Blender多方向プレビュー

```bash
python -m cbdk glb-preview model.glb \
  --blender "/path/to/blender" \
  --output reports/latest/glb_preview
```

生成物:

- `structure.json`: 上記の静的解析
- `scene_metadata.json`: Blenderが実際にimportしたMesh名、頂点/辺/面数、transform、寸法、全体bounds
- `front.png`
- `right.png`
- `top.png`
- `iso.png`

レンダリングはユーザーの作業中.blendを開かず、factory-startupの別プロセスで実行する。元GLBや.blendを保存・変更しない。

## AIでの利用ルール

GLBの形状について回答する場合は、可能なら次の優先順位を使う。

1. Blender実レンダリングPNG
2. `scene_metadata.json`
3. `structure.json`
4. ユーザーのスクリーンショット/説明

**画像生成AIによる再構成画像を、GLBそのものの正確な表示と扱わない。**

画像生成は説明図・設計案には使えるが、元3Dデータの形状確認はこのInspectorの実レンダリングを優先する。

## CI

Blender CIでは毎回テスト用Cube + SphereをGLB出力し、そのGLBを再度このInspectorへ渡す。

検査項目:

- 静的解析で2個以上のnode/meshを認識
- Blender import後のMesh Objectが2個
- object名が保持される
- front/right/top/isoの4枚が実際に生成される
- metadata JSONが生成される

Blender 4.4.3 / 4.5.15 / 5.2.1での実CI結果を確認するまでは、実機検証済みとは記録しない。

## 制約

- GLBはBlender固有Modifier、Edit Mode選択、アドオンPropertyなどを完全には保持しない。
- 4方向画像は形状確認用で、内部構造が隠れる場合がある。その場合は追加ビュー/分解ビューを将来拡張する。
- マテリアルや透過設定によっては形状が見づらいことがある。
- 実レンダリングが成功しても、元アドオンの操作感や機構の物理的可動性を自動証明するものではない。
