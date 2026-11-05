# CBDK Blender 実機テスト環境（v0.8）

## Windows PCで実行

1. GitHubの `Chappy-Blender-DevKit` から最新版のZIPを取得して解凍する（または配布するv0.8 ZIPを使用）。
2. [Blender公式](https://www.blender.org/download/) のBlenderとPython 3.11以上がインストールされていることを確認。
3. フォルダ直下の **`run_blender_tests_windows.bat` をダブルクリック**。
4. 自動で Python単体テスト → Blender実機テスト → 証拠のSHA-256照合を実施。
5. 結果: `reports/latest/parts_evidence.json`。ログ: `reports/latest/blender_parts.log` と `reports/latest/python_unit_tests.log`。

Blenderは環境変数 `CBDK_BLENDER_EXE`、PATH、標準インストール場所から自動検索します。Blenderが見つからない場合、以下のコマンドでフルパスを指定できます。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows_run_blender_tests.ps1 -BlenderPath "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

既存の.blendや設定は開かず、Blenderを別プロセスで `--background --factory-startup` 起動。テスト用のメッシュだけ作って削除します。ソフトの自動インストールや情報の外部送信は行いません。

## ChatGPTから扱えるクラウド上の実機環境

`.github/workflows/blender-smoke.yml` により、GitHub Actions のUbuntuランナーでBlender 4.5.15 LTSを公式配布元からダウンロードし、公式SHA-256と照合してからテストします。

- Pull Requestで関係するコードが変わると自動実行。
- GitHub → Actions → **CBDK Blender 4.5 LTS runtime smoke** → **Run workflow** から手動実行も可能。
- 結果のJSONとログを **Artifacts** に保存（14日間）。
- ダウンロードはテスト実行時のみ（容量約360MiB）。
- 元アドオンのソースコードやユーザーの.blendをGitHubに渡す必要はありません。

GitHub経由でテストを実行・結果を確認できますが、**ChatGPTがあなたのPCを遠隔操作するわけではありません**。

## 実行結果の意味

| 部品 | 確認する内容 |
|---|---|
| BLCTX-001 | メッシュの取得、編集モード指定違反の拒否 |
| BLCTX-002 | 選択中のメッシュ抽出、結果のタプル |
| BME-001 | Objectモード拒否、Editモードの選択頂点3/辺3/面1 |

検証対象はCBDKが自作した3つのヘルパーだけ。外部アドオンは実行しません。Smoke成功は正式な部品採用や配布許可、全Blender版での互換を保証しません。

## エラー時

Windowsの `reports/latest/blender_parts.log` と `parts_evidence.json` を共有してください。Pythonテスト失敗時は `python_unit_tests.log` も必要です。

クラウドの場合はGitHub Actionsの失敗したRun URLとArtifactsの結果を調べます。

## v0.8.1: Windows Pythonテストの誤検知とBlender複数版テスト

Windows PowerShell 5.1では、正常に成功した `unittest -v` の出力でも、標準エラー出力を `$ErrorActionPreference = 'Stop'` と組み合わせると、終了コードを確認する前に停止する場合があります。v0.8.1では `Start-Process -RedirectStandardOutput/-RedirectStandardError` に変更し、**プロセス終了コード**で成功・失敗を判定します。Pythonテストログには両方の出力が残ります。

**通常のダブルクリック：** 標準インストール先で見つけたBlenderを全バージョン順番に検証します。Blender 4.4.3 と5.2.1が存在すれば、双方を別々にチェックします。Python単体テストは最初の1回だけで、証拠JSONとスモークログは各バージョンの別ファイルです。

**特定の1バージョンのみ：** BAT起動引数に `-BlenderPath "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"` を与えます（インストール先に合わせて変更）。またはPowerShellから `scripts/windows_run_blender_tests.ps1 -BlenderPath "C:\...\blender.exe"`。

**Windows PowerShell自身の回帰テスト：** `scripts/windows_run_blender_tests.ps1 -UnitOnly` はBlenderを必要とせず、PowerShell5.1上で Python の verbose テストを起動します。GitHub Actions `windows-launcher.yml` でも自動検査します。

**クラウド実機テスト：** GitHub Actions `blender-smoke.yml` は公式配布アーカイブをSHA-256で照合し、Blender 4.4.3・4.5.15・5.2.1を個別に実行します。Linuxの結果はWindowsの実機成功と同一ではありません。

### Python実行環境の選び方

Windows版はテスト済みのPython 3.11、3.12、3.13を優先します。単純な `py -3` はPython 3.15など未検証版を勝手に選んでしまう場合があるため、`python.exe` の対応バージョンを確認してから、なければ `py -3.13` / `py -3.12` / `py -3.11` を順に試します。


## v0.9: 複数バージョンの結果一覧

Windowsで複数のBlenderをテストすると、`reports/latest/parts_matrix.json` と `parts_matrix.md` が自動作成されます。過去に作成したテスト結果をまとめ直したい場合は以下を使ってください。

```bash
python -m cbdk part-matrix --evidence-dir reports/latest
```

古いコードの証拠、欠けたテスト項目、破損したJSONは検証済みとして数えず、`rejected_evidence` に理由を記録します。古い証拠がある場合はコマンドが非0の終了コードを返しますが、Windowsスモークテストの成功/失敗と混同しません。結果は未署名のローカルJSONなので、真正性が保証された認証記録ではありません。
