#!/usr/bin/env python3
"""
AI Radar — Markdown を記事HTMLに変換する

issues/*.md を読み、NewsPicks風のレイアウトで docs/*.html を生成する。
docs/index.html にはバックナンバー一覧を作る。

使い方:
    python3 scripts/build_html.py            # 全号を変換
    python3 scripts/build_html.py 2026-08-03 # 特定の号だけ

依存: 標準ライブラリのみ（pip install 不要）
ネットワークも不要なので、どの環境でも動く。
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "issues"
DOCS = ROOT / "docs"

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

CSS = """
:root {
  --ink: #14161a;
  --sub: #6b7280;
  --line: #e5e7eb;
  --accent: #0b5cff;
  --bg: #ffffff;
  --box: #f6f8fa;
  --mark: #fff3b8;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f0f2f5;
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans",
               "Noto Sans JP", "Yu Gothic", sans-serif;
  line-height: 1.9;
  font-size: 17px;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 720px; margin: 0 auto; padding: 0 20px 100px; }
article { background: var(--bg); padding: 56px 56px 72px; margin-top: 32px;
          border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }

.kicker { font-size: 12px; letter-spacing: .18em; color: var(--accent);
          font-weight: 700; margin-bottom: 18px; }
h1 { font-size: 34px; line-height: 1.45; margin: 0 0 20px;
     letter-spacing: -.01em; font-weight: 800; }
.dateline { font-size: 13px; color: var(--sub); padding-bottom: 28px;
            border-bottom: 1px solid var(--line); margin-bottom: 36px; }
.lead { font-size: 18.5px; line-height: 1.95; font-weight: 600;
        margin: 0 0 36px; }

h2 { font-size: 23px; line-height: 1.5; margin: 60px 0 22px;
     padding-top: 4px; font-weight: 800; letter-spacing: -.01em; }
h2 .num { display: block; font-size: 12px; color: var(--accent);
          letter-spacing: .16em; margin-bottom: 10px; font-weight: 700; }

p { margin: 0 0 22px; }
strong { font-weight: 700; background: linear-gradient(transparent 62%, var(--mark) 62%); }
a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(11,92,255,.28); }
a:hover { border-bottom-color: var(--accent); }
code { background: var(--box); padding: 2px 6px; border-radius: 3px;
       font-size: .88em; font-family: "SF Mono", Menlo, Consolas, monospace; }

blockquote { margin: 32px 0; padding: 4px 0 4px 24px;
             border-left: 3px solid var(--ink); font-size: 19px;
             line-height: 1.85; font-weight: 600; }
blockquote p { margin: 0; }

.box { background: var(--box); border-radius: 6px; padding: 26px 30px;
       margin: 36px 0; font-size: 15.5px; line-height: 1.85; }
.box .box-title { font-size: 12px; letter-spacing: .14em; font-weight: 700;
                  color: var(--accent); margin-bottom: 14px; }
.box ol, .box ul { margin: 0; padding-left: 20px; }
.box li { margin-bottom: 8px; }
.box p:last-child { margin-bottom: 0; }

.idea { border-left: 3px solid var(--accent); background: #f5f8ff;
        padding: 20px 24px; margin: 28px 0; border-radius: 0 4px 4px 0; }
.idea .idea-title { font-size: 12px; letter-spacing: .12em; font-weight: 700;
                    color: var(--accent); margin-bottom: 10px; }
.idea p { margin: 0; font-size: 16px; }

ul, ol { margin: 0 0 22px; padding-left: 22px; }
li { margin-bottom: 10px; }

table { width: 100%; border-collapse: collapse; margin: 30px 0; font-size: 15px; }
th, td { padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; }
th { background: var(--box); font-weight: 700; font-size: 13px; color: var(--sub); }
td strong { background: none; color: var(--accent); }

hr { border: 0; border-top: 1px solid var(--line); margin: 48px 0; }

.source { font-size: 13px; color: var(--sub); margin: -6px 0 0; }
.source a { color: var(--sub); border-bottom-color: var(--line); }

footer { margin-top: 64px; padding-top: 28px; border-top: 1px solid var(--line);
         font-size: 13px; color: var(--sub); }
.nav { margin: 28px 0 0; font-size: 14px; }

/* 一覧ページ */
.index-head { padding: 48px 0 8px; }
.index-head h1 { font-size: 28px; }
.index-head p { color: var(--sub); font-size: 15px; }
.card { background: #fff; padding: 24px 28px; border-radius: 4px;
        margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,.06);
        display: block; border: 0; color: inherit; }
.card:hover { box-shadow: 0 2px 10px rgba(0,0,0,.1); }
.card .d { font-size: 12px; color: var(--accent); font-weight: 700;
           letter-spacing: .1em; margin-bottom: 8px; }
.card .t { font-size: 18px; font-weight: 700; line-height: 1.5; }

@media (max-width: 640px) {
  body { font-size: 16px; }
  article { padding: 32px 22px 48px; }
  h1 { font-size: 26px; }
  h2 { font-size: 20px; margin-top: 44px; }
  .wrap { padding: 0 10px 60px; }
}
"""


def esc(s):
    return html.escape(s, quote=False)


def inline(text):
    """インライン記法を変換する。エスケープしてから記号を戻す。"""
    text = esc(text)
    # コードは先に退避（中の記号を変換させない）
    stash = []

    def keep(m):
        stash.append(m.group(1))
        return f"\x00{len(stash)-1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{stash[int(m.group(1))]}</code>", text)
    return text


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(md, date_str):
    """issueのMarkdownをHTML本文に変換する。"""
    lines = md.split("\n")
    out, i = [], 0
    section_no = 0
    title = ""
    in_list = None

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        # 見出し（H1はタイトルとして抜き、本文には出さない）
        if stripped.startswith("# "):
            close_list()
            title = stripped[2:].strip()
            i += 1
            continue

        # 「今日の空振り」→ ボックス（通常の見出し処理より先に判定する）
        if stripped.startswith("## 今日の空振り") or stripped == "**今日の空振り**":
            close_list()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith(("#", "---", "*次号")):
                if lines[i].strip():
                    buf.append(lines[i].strip())
                i += 1
            body = inline(" ".join(buf))
            out.append(f'<div class="box"><div class="box-title">今日の空振り</div><p>{body}</p></div>')
            continue

        if stripped.startswith("## "):
            close_list()
            head = stripped[3:].strip()
            m = re.match(r"^(\d+)\.\s*(.+)$", head)
            if m:
                section_no = int(m.group(1))
                out.append(f'<h2><span class="num">{section_no:02d}</span>{inline(m.group(2))}</h2>')
            else:
                out.append(f"<h2>{inline(head)}</h2>")
            i += 1
            continue

        # 引用（「今日の一言」ブロックはリードとして扱う）
        if stripped.startswith(">"):
            close_list()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                t = lines[i].strip().lstrip(">").strip()
                if t and not t.startswith("**今日の一言**"):
                    buf.append(t)
                i += 1
            if buf:
                body = "<br>".join(inline(b) for b in buf)
                out.append(f'<p class="lead">{body}</p>')
            continue

        # 水平線
        if re.fullmatch(r"-{3,}|\*{3,}", stripped):
            close_list()
            out.append("<hr>")
            i += 1
            continue

        # 表
        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            close_list()
            header = split_row(lines[i])
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c).replace('<br>', '<br>')}</th>" for c in header)
            trs = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
            continue

        # 転用アイデア（次行以降が本文）
        if stripped in ("**転用アイデア**", "**転用アイデア**："):
            close_list()
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", "出典", "---", "|")):
                buf.append(lines[i].strip())
                i += 1
            body = inline(" ".join(buf))
            out.append(f'<div class="idea"><div class="idea-title">転用アイデア</div><p>{body}</p></div>')
            continue

        # 出典行
        if stripped.startswith("出典:") or stripped.startswith("出典："):
            close_list()
            out.append(f'<p class="source">{inline(stripped)}</p>')
            i += 1
            continue

        # リスト
        m = re.match(r"^[-*]\s+(.+)$", stripped)
        if m:
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.+)$", stripped)
        if m:
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        # 空行
        if not stripped:
            close_list()
            i += 1
            continue

        # 斜体だけの行（脚注扱い）
        if re.fullmatch(r"\*[^*].*\*", stripped):
            close_list()
            out.append(f'<p class="source">{inline(stripped[1:-1])}</p>')
            i += 1
            continue

        # 通常段落
        close_list()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_list()
    return title, "\n".join(out)


def headline(h1, raw, date_str):
    """記事の見出しを決める。

    1. H1 が「AI Radar — 日付」以外の中身を持つならそれを使う
    2. なければ最初の ## セクション見出しを流用する（そこが最重要ネタなので）
    3. それも無ければ日付
    """
    if h1:
        t = re.sub(r"AI Radar", "", h1)
        t = re.sub(r"[—\-–]\s*\d{4}-\d{2}-\d{2}", "", t)
        t = re.sub(r"（[^）]*）", "", t).strip(" 　—-–|｜")
        if len(t) >= 4:
            return t

    for line in raw.split("\n"):
        s = line.strip()
        if s.startswith("## ") and "空振り" not in s:
            sec = re.sub(r"^##\s*\d+\.\s*", "", s).replace("## ", "").strip()
            if sec:
                return sec
    return f"{date_str} の号"


def page(title, date_str, body, prev_link, next_link):
    y, mth, d = date_str.split("-")
    import datetime
    wd = WEEKDAY_JA[datetime.date(int(y), int(mth), int(d)).weekday()]
    nav = []
    if prev_link:
        nav.append(f'<a href="{prev_link}">← 前の号</a>')
    nav.append('<a href="index.html">バックナンバー</a>')
    if next_link:
        nav.append(f'<a href="{next_link}">次の号 →</a>')
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}｜AI Radar {date_str}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<article>
  <div class="kicker">AI RADAR — 業務転用リサーチ</div>
  <h1>{esc(title)}</h1>
  <div class="dateline">{y}年{int(mth)}月{int(d)}日（{wd}）</div>
{body}
  <footer>
    判断軸は「明日から自分の業務に転用できるか」の一点。<br>
    収集方針は <code>config.md</code> に定義。書き換えれば翌朝から反映されます。
    <div class="nav">{' ・ '.join(nav)}</div>
  </footer>
</article>
</div>
</body>
</html>"""


def index_page(entries):
    cards = "\n".join(
        f'<a class="card" href="{fn}"><div class="d">{dt}</div>'
        f'<div class="t">{esc(ti)}</div></a>'
        for dt, ti, fn in entries
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Radar — 業務転用リサーチ</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="index-head">
    <div class="kicker">AI RADAR</div>
    <h1>業務転用リサーチ</h1>
    <p>平日の朝、AIの動向から「明日から自分の業務に使えるもの」だけを拾う。</p>
  </div>
  {cards}
</div>
</body>
</html>"""


def main():
    DOCS.mkdir(exist_ok=True)
    targets = sorted(ISSUES.glob("*.md"))
    if len(sys.argv) > 1:
        targets = [ISSUES / f"{sys.argv[1]}.md"]

    all_issues = sorted(p.stem for p in ISSUES.glob("*.md"))
    entries = []

    for path in sorted(ISSUES.glob("*.md")):
        date_str = path.stem
        raw = path.read_text(encoding="utf-8")
        h1, body = convert(raw, date_str)
        title = headline(h1, raw, date_str)
        entries.append((date_str, title, f"{date_str}.html"))

        if path in targets:
            idx = all_issues.index(date_str)
            prev_link = f"{all_issues[idx-1]}.html" if idx > 0 else None
            next_link = f"{all_issues[idx+1]}.html" if idx < len(all_issues) - 1 else None
            (DOCS / f"{date_str}.html").write_text(
                page(title, date_str, body, prev_link, next_link), encoding="utf-8"
            )
            print(f"  生成: docs/{date_str}.html  「{title}」")

    entries.reverse()
    (DOCS / "index.html").write_text(index_page(entries), encoding="utf-8")
    print(f"  生成: docs/index.html（{len(entries)}号）")


if __name__ == "__main__":
    main()
