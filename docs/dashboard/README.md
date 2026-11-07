# CBDK 開発ライブボード（ブラウザ版）

**入口:** [index.html](index.html) — 1ファイルHTML。Blender、Python、Node、GitHubトークンなどのインストール不要。Chromium/Edge/Chrome/Firefox等のブラウザで、ファイルをダウンロードして開くだけで動く想定。外部スクリプト・依存パッケージなし。

## GitHubとの接続

**読み取り専用**で、public `mibesamiti-png/Chappy-Blender-DevKit` にアクセスする。

- `docs/project/STATE.json` — 現在の要件などの状態台帳。実装率は `(実装済 + 部分実装×0.5) / 全要件` という**推定指標**。リリース完成率ではない。
- `docs/PARALLEL_ROLLING_QUEUE.md` — 最新ラウンド・B/C/D担当と次の作業（Markdown見出しを簡易解析）。取得元は `feature/v0.18-shape-diagnostics`。
- `GET /repos/.../pulls?state=all&sort=updated&direction=desc&per_page=100` — A/B/C/Dの該当ラウンドPRと、実測 `merged_at` による直近24時間のAコード統合件数/直近3区間の中央値。
- `GET /repos/.../actions/runs?per_page=100` — **PR head SHAまたはA統合後merge SHAと workflow name/event を厳密照合**。B/C/Dは5系統、Aは7系統の独立した成功が揃って初めて「完了」。古いSHAの緑やトリガーされなかったKit/Skillは成功扱いしない。APIに実行情報が残っていない場合は「未確認」。

表示する統合件数/間隔は、PRタイトルに `Team A` と `integration` があるものを数えた**観測指標**であり、コード品質や開発者の生産性を示すものではない。GitHub APIは未認証で通常60回/時のため、自動更新は**5分間隔**（毎回API3リクエスト＋raw Markdown1件）。手動更新は可能だが頻回実行はAPI制限に注意。429/403等は画面上に表示して古い成功数を更新しない。

## 画面の見方

- チーム欄の上には `R8 BCD完了 2/3（B・D）` のような**実測完了カウント**が表示される。B/C/Dがすべて完了したらAの統合フェーズと判定（Aの自動統合作業が開始するわけではない）。
- 通知音をONにすると「♫ 試聴」が表示される。試聴はユーザーが押したときだけ鳴り、**実際の完了通知の回数には含まない**。
- 公開Raw Markdownの読み込みができない場合は、GitHub Contents APIに読み取りだけでフォールバックする。追加リクエストが必要となり、API残量が減る可能性がある。
- ダッシュボードはGitHubのファイル閲覧ページ内では動作しない。HTMLを保存してEdge/Chromeで開く。

## 通知音（完了時に一度）

- デフォルトOFF。ブラウザで「♪ 通知音」をクリックすると、Web Audioをユーザー操作で解放してONにする。
- 初回読み込み時にすでに完了していたイベントは**鳴らさず既知として登録**。次の更新で新しく5/7系統成功が揃ったA/B/C/Dごとに短い音を一回鳴らす。
- 完了イベントは `ラウンド + 担当（A/B/C/D）` をキーにし、同じラウンドの完了ではPR HEADが後から更新されても手動再読み込み/自動更新/再起動後に繰り返し鳴らさない。ただし、CI判定は常に最新PR HEAD（Aは統合SHA）で再確認する。`localStorage` が無効な環境では保存が継続しない場合がある。
- **画面が開かれている間だけ**のポーリングであり、閉じたブラウザでも通知が届く仕組みではない。バックグラウンドタブのタイマー/音声再生はブラウザの省電力制約に左右される。音はセッションごとに改めてON操作が必要。

## ブラウザでの開き方

1. この `index.html` を GitHub から保存して、WindowsのEdge/Chrome等で開く。GitHubのファイル閲覧ページ自体ではJavaScriptは実行されない。
2. 自動更新は初期ON。手動更新は「↻ 手動更新」。
3. 完了通知が欲しい場合だけ「♪ 通知音 OFF」をクリックしてON。初回の過去完了は鳴らない。
4. アクセス不可/レート制限時はエラー表示。ローカルブラウザ環境から公開GitHub APIと `raw.githubusercontent.com` へアクセスできる必要がある。

**GitHub Pages公開は別途選択/設定が必要。** リポジトリの Settings → Pages で開発ブランチの `/docs` を公開元にすれば `/dashboard/` に配置できるが、他の `docs` も公開されるため自動変更せず、利用者が確認してから設定する。ブラウザ画面はv0.18開発ブランチで管理され、`main`・正式リリース・リポジトリ Pages設定は変更しない。

## 安全境界・改善余地

- 認証トークン、GitHubの書き込み権限、カメラ/マイク、任意ソース実行なし。GitHubの取得データはDOMの `textContent` で描画（HTMLとして評価しない）。publicリポジトリの情報だけ表示する。
- 100件より古いPRやworkflow run、GitHub APIで未検出のCIは「未確認」となる場合がある。推測で完了にしない。正式v0.17.0、実Windows GUI、ユーザー所有GLB、外部Addon、ライセンス・Extensions公開は別ゲート。
- 将来候補：専用の読み取り専用 `docs/project/TEAM_STATUS.json` をGitHub Actionsで公開生成して、古いCIが直近100件から押し出されても誤判定しないようにする。ただし署名・status検証ルール設計と共通CIが必要なので今回は未実装。

**A運用:** 改良はA専用ブランチとドラフトPRからv0.18開発ブランチへ統合。B/C/Dの作業範囲やSTATE/HANDOFF/Notionは変更しない。
