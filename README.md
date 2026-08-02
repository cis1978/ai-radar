# AI Radar — 業務転用リサーチ

平日の朝、AIの動向から「明日から自分の業務に使えるもの」だけを拾って記事にする。

**公開ページ**: （GitHub Pages 有効化後にURLを記載）

---

## 構成

```
config.md              収集の仕様書。方針を変えたいときはここを書き換える
issues/YYYY-MM-DD.md   各号の原稿（Markdown）
docs/                  公開用HTML。GitHub Pages がこのフォルダを配信する
  index.html           バックナンバー一覧
  YYYY-MM-DD.html      各号の記事ページ
scripts/
  build_html.py        issues/*.md → docs/*.html に変換
  fetch_feeds.py       公式ブログのRSS取得（Mac側で手動実行する用）
```

## 毎朝やっていること

1. `config.md` を読む（方針は毎回ここから取る）
2. 直近2号を読んで話題の重複を避ける
3. 公式ドメインに限定してWeb検索 → 本文を取得して数字と企業名を裏取り
4. 採用基準で足切りして `issues/YYYY-MM-DD.md` を書く
5. `build_html.py` で記事HTMLを生成
6. git commit → push（GitHub Pages が自動で公開）
7. Slack `#ai活用プロジェクト` に見出しと公開URLを投稿

実行は平日 月〜金の朝7時台。土日は動かない。
アプリを閉じている間に時刻が来た場合は、次回起動時に実行される。

## 手で動かすとき

```bash
cd ~/Desktop/AI_Infomration

python3 scripts/build_html.py              # 全号のHTMLを作り直す
python3 scripts/build_html.py 2026-08-03   # 特定の号だけ

python3 scripts/fetch_feeds.py --days 7    # RSSで直近7日の一次情報を集める
```

`build_html.py` も `fetch_feeds.py` も標準ライブラリだけで動く（`pip install` 不要）。

## 収集方針を変えたいとき

`config.md` を直接編集する。Claudeへの指示は要らない。
毎朝の実行時に必ず読み直されるので、翌朝から反映される。
