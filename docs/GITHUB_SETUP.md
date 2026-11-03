# GitHubに公開する場合の安全な手順

**推奨: まず非公開（private）リポジトリを作る。** これは独立したCBDKプロジェクト。GBS/Chappy Playerとは混ぜない。

1. GitHubで `Chappy-Blender-DevKit` という空のprivateリポジトリを新規作成する（README等はGitHub側で作らなくてもよい）。
2. 「GitHub登録用ZIP」を展開し、直下で実行する。

```bash
git init
git add .
git commit -m "Initial CBDK v0.1 static scanner"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/Chappy-Blender-DevKit.git
git push -u origin main
```

3. 自作アドオンの原本はローカルの `input_sources_private/` に置く。`.gitignore` で除外してあるため、公開しない。原本を明示的にコミットする前に個人情報と再配布条件を確認する。
4. `python -m cbdk scan input_sources_private --output reports/latest` で再解析できる。

**注意:** `git add -f input_sources_private/...` でGitへ強制追加しない。`reports/initial_scan/` と `reports/latest/` もGitから除外している。

この開発成果物はGitHubには未アップロード。GitHubでの新規リポジトリ作成は現在の接続操作から行えないため、ここではローカル成果物を納品する。
