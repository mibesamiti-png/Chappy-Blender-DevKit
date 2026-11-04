# Chappy Blender DevKit Agent Skill v1.0 — 導入・利用ガイド

## できること

CBDKを使ったBlenderアドオン開発の手順を、Codex/ChatGPT向けに共通化する「スキル」です。アドオンそのものやAIモデルを変更する機能ではありません。手順の漏れ・重複実装・未検証の成功報告を防ぎます。

- 開発前の既存部品検索と重複レビュー
- ASTのみを使った安全側のコード解析・依存関係チェック
- `bpy` / `bmesh` のモード・context・選択状態の注意点
- Python単体テストとBlender実機テストの区別
- GitHub Actionsの成功/失敗とログ・証拠JSONの確認
- 原本・出典・権利確認、非公開ファイルの保護
- GitHub Pull Requestと進捗表の更新

## Codexのリポジトリ用スキル（おすすめ）

1. `mibesamiti-png/Chappy-Blender-DevKit` の最新版を開く。
2. リポジトリ内 `.agents/skills/chappy-blender-devkit/SKILL.md` が存在することを確認。
3. Codexに「`$chappy-blender-devkit` を使って、このBlenderアドオンの開発を進めて」と頼む。自然な依頼でも、説明に合えばスキルが自動選択されることがあります。
4. Codexのスキル一覧に表示されなければCodexを再起動して確認する。

`AGENTS.md` は引き続き有効。スキルはその内容を置き換えず、使う順序をまとめるものです。

## ZIPの生成

リポジトリルートで、Python 3.11以降を使います。

```bash
python scripts/package_skill.py
```

生成するファイル：

- `dist/CBDK_Skill_v1.0.0.zip`: スタンドアロンのスキル。中身のルートは `chappy-blender-devkit/SKILL.md`。
- `dist/CBDK_Skill_Plugin_v1.0.0.zip`: `plugin.json` と `skills/chappy-blender-devkit/SKILL.md` を持つスキル専用プラグイン形式。

GitHub Actionsの **CBDK Agent Skill package** でも両方を生成し、成果物（Artifacts）として保存します。

## ChatGPTで使う場合

スキルに対応したChatGPTの環境なら、サイドバーの「プラグイン」→「スキル」から、作成・アップロード機能の有無を確認してください。利用できる場合はスタンドアロンスキルのZIPをアップロードして、内容の審査/スキャン結果を確認します。

プラグイン形式のZIPは、ChatGPT/Codex向けプラグインとして配布・導入するときのパッケージです。**このZIPを作っただけではChatGPTアカウントにインストールされません。** プラグインのローカルマーケットプレイスや配布には別の操作が必要です。利用可能な導入方法はプラン/製品/管理者設定によって異なります。

ChatGPTでスキル機能が見当たらない場合でも、接続済みのGitHubリポジトリを指定して「`AGENTS.md`と`SKILL.md`に沿って開発して」と依頼する代替が可能です。ただしこれは**インストール済みスキルの自動発動とは異なります**。

## 安全性と検証状況

このスキルには実行コードを含めません。実行可能なのは既存CBDKリポジトリ内の明示的なCLI・CIワークフローで、実行には環境とアクセス権が必要です。

- スキルのメタデータ・リンク・パッケージは自動テストで確認。
- スキルがChatGPT/Codexで自動発動するかは、実際のインストール環境で確認する必要があります。
- Blender 4.5 LTSで成功した既存の3部品のスモークテストを、他のコードや全バージョンの品質保証と混同しません。
- `input_sources_private/`、`reports/latest/`、`reports/ci/` にあるユーザーの原本や解析結果はZIPに入れません。
