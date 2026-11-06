# CBDK GLB Visual Inspector

GLBを「推測で見たつもり」にせず、**構造JSON + Blender実レンダリング画像**を解析根拠にするための開発機能。

## 目的

Blenderアドオンが生成した形状や参考3DデータをChatGPT/Codexへ渡す際、GLBのファイル名や会話文だけで形状を推測すると取り違えが起きる。

この機能は3段階で確認する。

1. `glb-inspect`: BlenderなしでGLB 2.0のコンテナ/JSONチャンクだけを静的解析。
2. `glb-quick-preview`: Blenderが使えない時の任意fallback。trimesh + matplotlibで7方向画像と部品単独画像を生成。
3. `glb-preview`: 信頼済みBlenderを `--background --factory-startup` で起動し、実際にGLBを読み込んで**7方向PNG + 各部品単独サムネイル + scene metadata**を生成。

## 1. 静的構造解析

```bash
python -m cbdk glb-inspect model.glb --output reports/latest/glb_structure.json
```

主な出力:

- scene / node / mesh / materialの個数
- node名、mesh名、親子参照
- root node
- node→mesh名の対応
- primitive数
- POSITION / index accessorの要素数
- POSITION accessorにmin/maxがある場合はローカルbounds
- asset generator
- GLB chunk構成

安全上、静的解析では次を行わない。

- BIN chunkの形状データ読み込み
- 外部URIの読み込み
- 埋め込み画像のデコード
- Blender/Pythonコードの実行
- GLBを信頼済みアドオンとして扱うこと

壊れたnode/mesh参照やnode graphの循環は安全側に拒否する。

## 2. BlenderなしQuick Preview（fallback）

Blenderを起動できない環境では、任意依存を導入すると低精度fallbackを利用できる。

```bash
pip install -e ".[glb-quick]"
python -m cbdk glb-quick-preview model.glb \
  --output reports/latest/glb_quick_preview
```

生成物は7方向PNG、最大32個の部品単独サムネイル、`quick_scene_metadata.json`。

- GLB node transformは反映する。
- マテリアルは読み飛ばし、形状確認用の中立グレーで描画する。
- 外部URI参照のあるGLBはtrimeshへ渡す前に拒否する。
- 頂点50万 / 面25万を上限として、巨大モデルを安全側に拒否する。
- Matplotlib 3D描画はBlenderより低精度。**Blender実レンダリングの代替証拠ではなくfallback**として扱う。

## 3. Blender多方向プレビュー

```bash
python -m cbdk glb-preview model.glb \
  --blender "/path/to/blender" \
  --output reports/latest/glb_preview
```

生成物:

- `structure.json`: 上記の静的解析
- `scene_metadata.json`: Blenderが実際にimportしたMesh名、親、頂点/辺/面数、元マテリアル名、transform、寸法、全体bounds
- `front.png / back.png`
- `right.png / left.png`
- `top.png / bottom.png`
- `iso.png`
- `objects/000.png ...`: Mesh Objectを1個ずつ単独表示した斜視サムネイル（最大32個）

レンダリングはユーザーの作業中.blendを開かず、factory-startupの別プロセスで実行する。元GLBや.blendを保存・変更しない。

### 構造確認用Clay表示

Blender版は構造確認を優先して **Workbenchを第一候補** にし、利用できない環境だけEeVee系へfallbackする。CIは最低解像度256pxで動作確認し、実利用時は指定解像度で生成する。

GLB内のマテリアルが透明・発光・極端に暗い場合でも形を読みやすくするため、画像は**中立色のClayマテリアルへ一時置換してレンダリング**する。元のマテリアル名は `scene_metadata.json` に保存する。

これは「見た目の再現」ではなく「形状・部品構成の確認」を目的とする。

## AIでの利用ルール

GLBの形状について回答する場合は、可能なら次の優先順位を使う。

1. Blenderで生成した各部品の単独サムネイル
2. 7方向のBlender実レンダリングPNG
3. ユーザーが直接撮ったBlenderスクリーンショット
4. Blender `scene_metadata.json`
5. Quick Preview画像/metadata（Blenderが使えない場合）
6. `structure.json`

**画像生成AIによる再構成画像を、GLBそのものの正確な表示と扱わない。**

画像生成は説明図・設計案には使えるが、元3Dデータの形状確認はこのInspectorの実レンダリングを優先する。

## CI

Blender CIでは毎回テスト用Cube + SphereをGLB出力し、そのGLBを再度このInspectorへ渡す。

検査項目:

- 静的解析で2個以上のnode/meshを認識
- node/mesh参照が壊れていない
- Blender import後のMesh Objectが2個
- object名が保持される
- 7方向PNGが実際に生成される
- 2個の部品単独サムネイルが生成される
- metadata JSONとBlender返却payloadが一致する

Blender 4.4.3 / 4.5.15 / 5.2.1での実CI結果を確認するまでは、実機検証済みとは記録しない。

## 制約

- GLBはBlender固有Modifier、Edit Mode選択、アドオンPropertyなどを完全には保持しない。
- 部品単独サムネイルは最大32 Mesh Object。超過分はmetadataでtruncatedとして記録する。
- hidden/internal geometry、アニメーション途中の状態、Geometry Nodesの生成意図までは自動理解できない。
- 実レンダリングが成功しても、元アドオンの操作感や機構の物理的可動性を自動証明するものではない。


## 4. Reference / Candidate 形状比較（v0.18）

Blender previewで生成した2つの `scene_metadata.json` を比較する。

```bash
python -m cbdk glb-compare reference/scene_metadata.json candidate/scene_metadata.json \
  --profile shape --output reports/latest/glb_compare.json
```

`shape` はworld-spaceの全体bounds・各部品bounds・配置を主に比較し、トポロジー差は情報として残す。名前が一致しない部品は寸法と位置の近さでfallback matchingする。`strict` は名前fallbackや頂点/辺/面数の差も失敗にする。

GLBファイルから一括で行う場合:

```bash
python -m cbdk glb-regression reference.glb candidate.glb \
  --blender "/path/to/blender" \
  --output reports/latest/glb_regression
```

出力にはreference/candidateそれぞれの構造JSON・7方向画像・部品単独画像・scene metadataと、`comparison.json` が含まれる。初期比較は外接bounds中心なので、同じboundsで輪郭や穴だけが違うケースは見逃しうる。画像証拠を併用し、完全一致判定として扱わない。


### v0.18 初期比較の検証結果

PR #23でPython 343件を3.11/3.12/3.13、Windows PowerShell 3.11/3.13、Blender 4.4.3/4.5.15/5.2.1で成功。synthetic GLBのworld-space bounds生成と同一metadata自己比較を3つのBlender版で確認した。これはboundsベース比較の実行経路を証明するが、異なる輪郭に対する完全な視覚一致検出までは証明しない。


## 5. シルエット指紋（v0.18）

Blender版previewは、通常のPNGとは別に実メッシュを32x32へ正射影したbinary silhouette signatureを`scene_metadata.json`へ保存する。全体7方向と部品別4方向を比較できるため、world boundsが同じでも輪郭が異なるケースを検出しやすくなる。

`glb-compare` / `glb-regression` の既定IoU下限は0.90。必要に応じ `--silhouette-iou-min 0.95` のように厳しくできる。32x32より小さい穴・細線・内部形状は完全には捉えないため、シルエット一致を完全な形状同一性とは扱わない。
