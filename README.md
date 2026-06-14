# YouTube Thanks Reader MVP

YouTube配信の Super Chat / Super Sticker / Membership Milestone Chat を時系列で確認し、お礼読み上げに使うための静的Webアプリです。

## 構成

```text
tools/fetch_thanks.py        取得・JSON保存・ページ生成・GitHub push
.github/workflows/pages.yml  GitHub Pages公開
public/assets/app.js         一覧/読み上げモード
public/assets/styles.css     表示スタイル
public/robots.txt            noindex補助
public/thanks/demo123.../    サンプル公開ページ
```

## セットアップ

Python 3.10以上を推奨します。

実配信のチャット取得には `yt-dlp` を使います。

```powershell
python -m pip install yt-dlp
```

## 使い方

サンプルページ生成:

```powershell
python tools\fetch_thanks.py --demo
```

YouTube配信URLから生成:

```powershell
python tools\fetch_thanks.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

生成後、以下のような固有URL用ディレクトリが作成されます。

```text
public/thanks/ランダムID/
```

ローカル確認:

```powershell
python -m http.server 8000 -d public
```

ブラウザで開く:

```text
http://localhost:8000/thanks/ランダムID/
```

## GitHub Pages公開

GitHubリポジトリの Settings > Pages で、Source を `GitHub Actions` に設定してください。

`main` ブランチへpushすると、`.github/workflows/pages.yml` が `public` ディレクトリをGitHub Pagesへ公開します。Actions画面から手動実行もできます。

自動Pushする場合:

```powershell
python tools\fetch_thanks.py "https://www.youtube.com/watch?v=VIDEO_ID" --push
```

`--push` は、現在のフォルダがGitHubリポジトリで、remote設定済みであることを前提に `git add` / `git commit` / `git push` を実行します。

## SEO対策

各ページに以下を設定しています。

```html
<meta name="robots" content="noindex,nofollow">
```

さらに `public/robots.txt` でクロール拒否も指定しています。

## 将来拡張しやすい点

- `data.json` に `read` フラグを追加すると、お礼済みチェックを実装できます。
- `public/thanks/index.json` のような一覧ファイルを追加すると、配信一覧を作れます。
- `streamer_id` を `meta` に追加すると、複数配信者対応に拡張できます。
- `app.js` の `state.items` に対してフィルタを追加すると、検索機能を実装できます。

## 注意

YouTube側のチャットリプレイ形式は変更される可能性があります。MVPでは `yt-dlp` が保存する `live_chat` JSONから、有料チャット系Rendererを抽出する実装です。
