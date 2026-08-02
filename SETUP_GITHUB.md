# GitHub Pages 公開の設定手順

記事HTMLをURLで公開し、Slackからリンクで読めるようにする。所要5分・無料。

> **トークンは誰にも見せないこと。** 以下はすべて自分のブラウザとターミナルで完結する。
> Claudeとの会話にトークンを貼る必要はない。

---

## 1. リポジトリを作る

<https://github.com/new> を開く。

| 項目 | 設定 |
|------|------|
| Repository name | `ai-radar` |
| Description | （任意）AI Radar — 業務転用リサーチ |
| 公開設定 | **Public** ※ GitHub Pages の無料公開に必要 |
| Add a README file | **オフ** |
| Add .gitignore | **なし** |
| Choose a license | **なし** |

READMEや.gitignoreは既にこのフォルダにあるので、GitHub側で作るとpush時に衝突する。必ずオフにする。

「Create repository」を押す。

---

## 2. アクセストークンを作る

<https://github.com/settings/personal-access-tokens/new> を開く。

| 項目 | 設定 |
|------|------|
| Token name | `ai-radar-push` |
| Expiration | 90 days（推奨） |
| Repository access | **Only select repositories** → `ai-radar` を選ぶ |
| Permissions → Repository permissions → **Contents** | **Read and write** |

Contents 以外の権限は触らない。これで万一漏れてもこのリポジトリしか操作できない。

「Generate token」を押し、表示された文字列をコピーする。**この画面を閉じると二度と見られない。**

---

## 3. ターミナルで接続する

ターミナルを開いて、以下を実行する。`USERNAME` と `TOKEN` は自分のものに置き換える。

```bash
cd ~/Desktop/AI_Infomration
git remote add origin https://USERNAME:TOKEN@github.com/USERNAME/ai-radar.git
git push -u origin main
```

`Enumerating objects... done.` のように出れば成功。

うまくいかないとき:

- `remote origin already exists` → `git remote set-url origin https://...` に読み替える
- `Authentication failed` → トークンの Repository access に `ai-radar` が入っているか、Contents が Read and write か確認
- `rejected ... fetch first` → GitHub側でREADME等を作ってしまっている。リポジトリを消して手順1からやり直すのが早い

---

## 4. GitHub Pages を有効化する

リポジトリのページで **Settings** → 左メニューの **Pages**。

| 項目 | 設定 |
|------|------|
| Source | Deploy from a branch |
| Branch | `main` |
| Folder | **`/docs`** |

「Save」を押す。1〜2分で以下のURLで公開される。

```
https://USERNAME.github.io/ai-radar/
```

---

## 5. Claudeに伝える

GitHubのユーザー名を伝える。公開URLを毎朝のSlack投稿に組み込む。

---

## 運用メモ

- 毎朝の自動実行が `git push` まで行うので、以降は何もしなくてよい
- トークンは `.git/config` に平文で保存される（Mac内のみ）。90日で期限が切れたら手順2をやり直す
- 公開したくない号ができたら、`issues/` から消して `python3 scripts/build_html.py` を実行し直せば `docs/` からも消える
- リポジトリを非公開に戻したくなったら Settings → General → 最下部の Danger Zone。ただし無料プランではPagesが止まる
