#!/usr/bin/env python3
"""
AI Radar — Markdown を記事HTMLに変換する

issues/*.md を読み、目次＋折りたたみ形式で docs/*.html を生成する。
docs/index.html にはバックナンバー一覧を作る。

■ 記事の構造（issues/*.md の書き方）
    # 記事見出し
    > **今日の一言**
    > リード文
    ## 1. 項目タイトル
    最初の段落 = 要約（常に表示される）
    2段落目以降 = 詳細（折りたたみの中に入る）
    ## 今日の空振り
    （折りたたまずボックスで表示）

■ 使い方
    python3 scripts/build_html.py            # 全号を変換
    python3 scripts/build_html.py 2026-08-03 # 特定の号だけ

依存: 標準ライブラリのみ（pip install 不要）
"""

import datetime
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUES = ROOT / "issues"
DOCS = ROOT / "docs"
GLOSSARY = ROOT / "glossary.md"

SITE = "https://cis1978.github.io/ai-radar"
WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

CSS = """
:root {
  --ink: #14161a; --sub: #6b7280; --line: #e5e7eb;
  --accent: #2f6fed; --bg: #fff; --box: #f6f8fa; --mark: #fff3b8;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: #f0f2f5; color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans",
               "Noto Sans JP", "Yu Gothic", sans-serif;
  line-height: 1.85; font-size: 17px; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 760px; margin: 0 auto; padding: 0 20px 100px; }
article { background: var(--bg); padding: 52px 52px 64px; margin-top: 28px;
          border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }

.kicker { font-size: 12px; letter-spacing: .18em; color: var(--accent);
          font-weight: 700; margin-bottom: 16px; }
h1 { font-size: 33px; line-height: 1.45; margin: 0 0 18px; font-weight: 800;
     letter-spacing: -.01em; }
.dateline { font-size: 13px; color: var(--sub); padding-bottom: 24px;
            border-bottom: 1px solid var(--line); margin-bottom: 30px; }
.card-img { width: 100%; height: auto; display: block; margin: 0 0 30px;
            border: 1px solid var(--line); border-radius: 4px; }
.lead { font-size: 18px; line-height: 1.9; font-weight: 600; margin: 0 0 34px; }

/* 目次 */
.toc { background: var(--box); border-radius: 8px; padding: 22px 26px;
       margin: 0 0 40px; }
.toc-head { display: flex; align-items: baseline; justify-content: space-between;
            gap: 12px; margin-bottom: 12px; }
.toc-title { font-size: 12px; letter-spacing: .14em; font-weight: 700;
             color: var(--accent); }
.toc-list { margin: 0; padding-left: 0; list-style: none; }
.toc li { margin-bottom: 7px; font-size: 15.5px; line-height: 1.6;
          display: flex; gap: 10px; }
.toc li::before { content: attr(value); color: var(--accent); font-weight: 700;
                  font-size: 12.5px; flex: none; padding-top: 3px;
                  font-variant-numeric: tabular-nums; min-width: 20px; }
.toc-group + .toc-group { margin-top: 18px; }
.toc-g-head { display: flex; align-items: center; gap: 9px; margin-bottom: 9px; }
.toc-g-range { background: var(--accent); color: #fff; font-size: 11.5px;
               font-weight: 700; padding: 2px 9px; border-radius: 999px;
               font-variant-numeric: tabular-nums; }
.toc-g-name { font-size: 13.5px; font-weight: 700; color: var(--ink); }
h3.group { font-size: 13px; letter-spacing: .1em; font-weight: 700;
           color: var(--accent); margin: 44px 0 -8px; }
.item-img { width: 100%; height: auto; display: block; margin: 0 0 20px;
            border: 1px solid var(--line); border-radius: 4px; }
.toc a { color: var(--ink); text-decoration: none; border-bottom: 1px solid transparent; }
.toc a:hover { border-bottom-color: var(--accent); color: var(--accent); }

.btn { font: inherit; font-size: 12.5px; color: var(--sub); background: none;
       border: 1px solid var(--line); border-radius: 999px; padding: 3px 13px;
       cursor: pointer; white-space: nowrap; }
.btn:hover { color: var(--accent); border-color: var(--accent); }
.btn.on { color: #fff; background: var(--accent); border-color: var(--accent); }
.ctrl { display: flex; gap: 8px; flex: none; }
.toc-note { margin: 14px 0 0; font-size: 12.5px; color: var(--sub); }

/* 用語注釈 */
.term { border-bottom: 1px dotted var(--accent); cursor: help; }
.term:focus { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
.term-pop { position: absolute; z-index: 20; max-width: 320px; background: #1f2430;
            color: #fff; font-size: 13.5px; line-height: 1.7; padding: 12px 15px;
            border-radius: 8px; box-shadow: 0 6px 22px rgba(0,0,0,.25); }
.term-pop b { display: block; font-size: 12px; color: #9fc0ff; margin-bottom: 4px; }

/* やさしい説明 */
.easy { display: none; background: #fffbe9; border-radius: 6px; padding: 13px 16px;
        margin: 0 0 14px; font-size: 15.5px; line-height: 1.8; }
.easy-tag { display: block; font-size: 11.5px; letter-spacing: .1em; font-weight: 700;
            color: #9a7b12; margin-bottom: 5px; }
body.easy-on .easy { display: block; }
body.easy-on .term { background: #fffbe9; }

/* 項目 */
.item { border-top: 1px solid var(--line); padding: 28px 0 4px; }
.item h2 { font-size: 21px; line-height: 1.5; margin: 0 0 12px; font-weight: 800;
           letter-spacing: -.01em; scroll-margin-top: 16px; }
.item h2 .num { color: var(--accent); font-size: 12.5px; letter-spacing: .12em;
                display: block; margin-bottom: 8px;
                font-variant-numeric: tabular-nums; }
.sum { margin: 0 0 14px; color: #33373d; }

details { margin: 0 0 20px; }
details > summary { list-style: none; cursor: pointer; display: inline-flex;
  align-items: center; gap: 6px; font-size: 13.5px; color: var(--accent);
  font-weight: 700; padding: 4px 0; user-select: none; }
details > summary::-webkit-details-marker { display: none; }
details > summary::after { content: "▾"; font-size: 11px; transition: transform .15s; }
details[open] > summary::after { transform: rotate(180deg); }
details > summary:hover { text-decoration: underline; }
.detail { padding: 14px 0 4px; border-left: 2px solid var(--line);
          padding-left: 20px; margin-top: 8px; }

p { margin: 0 0 18px; }
.detail p:last-child { margin-bottom: 0; }
strong { font-weight: 700; background: linear-gradient(transparent 62%, var(--mark) 62%); }
a { color: var(--accent); text-decoration: none;
    border-bottom: 1px solid rgba(47,111,237,.3); }
a:hover { border-bottom-color: var(--accent); }
code { background: var(--box); padding: 2px 6px; border-radius: 3px;
       font-size: .88em; font-family: "SF Mono", Menlo, Consolas, monospace; }
pre { background: var(--box); padding: 18px 20px; border-radius: 6px;
      overflow-x: auto; margin: 22px 0; line-height: 1.7; }
pre code { background: none; padding: 0; font-size: 13.5px; white-space: pre; }
blockquote { margin: 22px 0; padding: 2px 0 2px 20px; border-left: 3px solid var(--ink);
             font-size: 17.5px; font-weight: 600; }
blockquote p { margin: 0; }
ul, ol { margin: 0 0 18px; padding-left: 22px; }
li { margin-bottom: 8px; }
table { width: 100%; border-collapse: collapse; margin: 22px 0; font-size: 14.5px; }
th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; }
th { background: var(--box); font-weight: 700; font-size: 12.5px; color: var(--sub); }
td strong { background: none; color: var(--accent); }

.idea { border-left: 3px solid var(--accent); background: #f5f8ff;
        padding: 16px 20px; margin: 20px 0; border-radius: 0 4px 4px 0; }
.idea-title { font-size: 11.5px; letter-spacing: .12em; font-weight: 700;
              color: var(--accent); margin-bottom: 8px; }
.idea p { margin: 0; font-size: 15.5px; }
.source { font-size: 13px; color: var(--sub); margin: 0 0 6px; }
.source a { color: var(--sub); border-bottom-color: var(--line); }
.box { background: var(--box); border-radius: 8px; padding: 22px 26px; margin: 34px 0 0;
       font-size: 15px; }
.box-title { font-size: 11.5px; letter-spacing: .14em; font-weight: 700;
             color: var(--accent); margin-bottom: 10px; }
.box p:last-child { margin-bottom: 0; }

footer { margin-top: 52px; padding-top: 24px; border-top: 1px solid var(--line);
         font-size: 13px; color: var(--sub); }
.nav { margin-top: 22px; font-size: 14px; }

.index-head { padding: 44px 0 6px; }
.index-head h1 { font-size: 27px; }
.index-head p { color: var(--sub); font-size: 15px; }
.card { background: #fff; padding: 22px 26px; border-radius: 4px; margin-bottom: 11px;
        box-shadow: 0 1px 2px rgba(0,0,0,.06); display: block; border: 0; color: inherit; }
.card:hover { box-shadow: 0 2px 10px rgba(0,0,0,.1); }
.card .d { font-size: 12px; color: var(--accent); font-weight: 700;
           letter-spacing: .1em; margin-bottom: 6px; }
.card .t { font-size: 18px; font-weight: 700; line-height: 1.5; }

@media (max-width: 640px) {
  /* スマホでは小さい文字がとくに読みにくいので、補助的な要素ほど底上げする */
  body { font-size: 16.5px; }
  article { padding: 28px 18px 44px; }
  h1 { font-size: 26px; }
  .lead { font-size: 17px; }
  .item h2 { font-size: 20px; }
  .sum { font-size: 16.5px; }
  .easy { font-size: 16px; }
  .toc { padding: 18px 18px; }
  .toc li { font-size: 16px; }
  .toc li::before { font-size: 13.5px; }
  .toc-g-name { font-size: 15px; }
  .toc-g-range { font-size: 12.5px; }
  .toc-title { font-size: 13px; }
  .toc-note { font-size: 13.5px; }
  .btn { font-size: 13.5px; padding: 5px 12px; }
  .ctrl { flex-wrap: wrap; justify-content: flex-end; gap: 6px; }
  .source { font-size: 13.5px; }
  .idea p { font-size: 16px; }
  table { font-size: 14px; }
  th, td { padding: 9px 8px; }
  details > summary { font-size: 15px; padding: 8px 0; }
  .term-pop { font-size: 15px; }
  .wrap { padding: 0 10px 60px; }
  .detail { padding-left: 13px; }
}
"""


def esc(s):
    return html.escape(s, quote=False)


def load_glossary():
    """glossary.md を読んで [(表記, 説明)] を返す。長い表記から先にマッチさせる。"""
    if not GLOSSARY.exists():
        return []
    terms = []
    for line in GLOSSARY.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^-\s+(.+?):\s+(.+)$", line.strip())
        if not m:
            continue
        desc = m.group(2).strip()
        for alias in m.group(1).split("|"):
            alias = alias.strip()
            if alias:
                terms.append((alias, desc))
    terms.sort(key=lambda t: len(t[0]), reverse=True)
    return terms


SKIP_TAGS = ("code", "pre", "a", "summary", "h1", "h2", "button")


def annotate(body, terms):
    """本文中の用語に、クリックで説明が開く注釈を付ける。

    タグの内側、code / pre / a / 見出し の中には手を出さない。
    同じ語は最初の1回だけ注釈する（うるさくならないように）。
    """
    if not terms:
        return body

    parts = re.split(r"(<[^>]+>)", body)
    depth = 0
    used = set()
    out = []

    for part in parts:
        if part.startswith("<"):
            tag = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
            name = tag.group(1).lower() if tag else ""
            if name in SKIP_TAGS:
                if part.startswith("</"):
                    depth = max(0, depth - 1)
                elif not part.rstrip().endswith("/>"):
                    depth += 1
            out.append(part)
            continue

        if depth > 0 or not part.strip():
            out.append(part)
            continue

        seg = part
        for alias, desc in terms:
            if alias in used or alias not in seg:
                continue
            idx = seg.find(alias)
            chip = (f'<span class="term" tabindex="0" role="button" '
                    f'data-d="{html.escape(desc, quote=True)}">{alias}</span>')
            seg = seg[:idx] + chip + seg[idx + len(alias):]
            used.add(alias)
        out.append(seg)

    return "".join(out)


def inline(text):
    text = esc(text)
    stash = []

    def keep(m):
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{stash[int(m.group(1))]}</code>", text)


def row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def render(lines):
    """本文ブロックをHTMLにする。見出し(#, ##)は含まれない前提。"""
    out, i, in_list = [], 0, None

    def close():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    while i < len(lines):
        s = lines[i].strip()

        if s.startswith("```"):
            close()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre><code>{esc(chr(10).join(buf))}</code></pre>")
            continue

        if s.startswith(">"):
            close()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                t = lines[i].strip().lstrip(">").strip()
                if t:
                    buf.append(t)
                i += 1
            if buf:
                out.append("<blockquote><p>" + "<br>".join(inline(b) for b in buf) + "</p></blockquote>")
            continue

        if re.fullmatch(r"-{3,}|\*{3,}", s):
            close()
            i += 1
            continue

        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            close()
            head = row(lines[i])
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(row(lines[i]))
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tr = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>")
            continue

        if s in ("**転用アイデア**", "**転用アイデア**：", "**転用アイデア**:"):
            close()
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("出典", "---", "|", "#")):
                buf.append(lines[i].strip())
                i += 1
            out.append('<div class="idea"><div class="idea-title">転用アイデア</div>'
                       f'<p>{inline(" ".join(buf))}</p></div>')
            continue

        if s.startswith("出典:") or s.startswith("出典："):
            close()
            out.append(f'<p class="source">{inline(s)}</p>')
            i += 1
            continue

        m = re.match(r"^[-*]\s+(.+)$", s)
        if m:
            if in_list != "ul":
                close()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        m = re.match(r"^\d+\.\s+(.+)$", s)
        if m:
            if in_list != "ol":
                close()
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue

        if not s:
            close()
            i += 1
            continue

        close()
        out.append(f"<p>{inline(s)}</p>")
        i += 1

    close()
    return "\n".join(out)


def parse(md):
    """記事を「見出し / リード / 項目リスト / 末尾ボックス」に分解する。"""
    lines = md.split("\n")
    title, lead_lines, lead_text = "", [], ""
    items, tail, groups = [], [], []
    cur = None
    i = 0

    while i < len(lines):
        s = lines[i].strip()

        # コードブロック内は素通しする（中の ## を見出しと誤認しないため）
        if s.startswith("```"):
            block = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            if i < len(lines):
                block.append(lines[i])
                i += 1
            if cur is not None:
                cur["lines"].extend(block)
            continue

        if s.startswith("# ") and not title:
            title = s[2:].strip()
            i += 1
            continue

        if s.startswith("> ") and cur is None and not items:
            while i < len(lines) and lines[i].strip().startswith(">"):
                t = lines[i].strip().lstrip(">").strip()
                if t and "今日の一言" not in t:
                    lead_lines.append(t)
                i += 1
            lead_text = " ".join(lead_lines)
            continue

        # グループ見出し（### カテゴリ名）
        if s.startswith("### "):
            groups.append({"name": s[4:].strip(), "start": len(items) + 1})
            cur = None
            i += 1
            continue

        if s.startswith("## "):
            head = s[3:].strip()
            if "空振り" in head:
                cur = None
                i += 1
                tail = []
                while i < len(lines) and not lines[i].strip().startswith("## "):
                    tail.append(lines[i])
                    i += 1
                continue
            m = re.match(r"^(\d+)\.\s*(.+)$", head)
            cur = {"title": m.group(2) if m else head, "lines": []}
            items.append(cur)
            i += 1
            continue

        if cur is not None:
            cur["lines"].append(lines[i])
        i += 1

    # 各グループの終端番号を確定する
    for n, g in enumerate(groups):
        g["end"] = groups[n + 1]["start"] - 1 if n + 1 < len(groups) else len(items)

    return title, lead_lines, lead_text, items, tail, groups


def split_item(lines):
    """項目本文を「要約 / やさしい説明 / 詳細」に分ける。

    最初の段落 = 要約（常に表示）
    `やさしく:` で始まる行 = 非エンジニア向けの言い換え（トグルで表示）
    それ以降 = 詳細（折りたたみの中）
    """
    easy = ""
    rest = []
    for ln in lines:
        m = re.match(r"^\s*やさしく[:：]\s*(.+)$", ln)
        if m and not easy:
            easy = m.group(1).strip()
        else:
            rest.append(ln)

    i = 0
    while i < len(rest) and not rest[i].strip():
        i += 1
    summary = []
    while i < len(rest) and rest[i].strip():
        summary.append(rest[i].strip())
        i += 1
    return " ".join(summary), easy, rest[i:]


def headline(h1, raw, date_str):
    """H1 をそのまま記事タイトルにする。

    ダイジェスト号は H1 を「AI Radar 8月2日」のような中立な見出しにする。
    15件を束ねる主張を大見出しに置くと、全項目がその根拠に見えてしまうため。
    """
    if h1 and len(h1.strip()) >= 4:
        return h1.strip()
    for line in raw.split("\n"):
        s = line.strip()
        if s.startswith("## ") and "空振り" not in s:
            sec = re.sub(r"^##\s*\d+\.\s*", "", s).replace("## ", "").strip()
            if sec:
                return sec
    return f"{date_str} の号"


def ogp(title, date_str, desc):
    desc = re.sub(r"\s+", " ", re.sub(r"[*_`]", "", desc)).strip()[:160]
    tags = [
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="AI Radar — 業務転用リサーチ">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{SITE}/{date_str}.html">',
        f'<meta name="description" content="{esc(desc)}">',
    ]
    if (DOCS / "img" / f"{date_str}.png").exists():
        img = f"{SITE}/img/{date_str}.png"
        tags += [
            f'<meta property="og:image" content="{img}">',
            '<meta property="og:image:width" content="1600">',
            '<meta property="og:image:height" content="900">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{img}">',
        ]
    else:
        tags.append('<meta name="twitter:card" content="summary">')
    return "\n".join(tags)


def plain(s):
    """目次用に装飾記号を落とす。"""
    return esc(re.sub(r"[`*]", "", s))


def build_toc(items, groups):
    """目次。グループがあればカテゴリごとに区切って番号範囲を見せる。"""
    def li(n, it):
        return f'      <li value="{n}"><a href="#i{n}">{plain(it["title"])}</a></li>'

    if not groups:
        rows = "\n".join(li(n, it) for n, it in enumerate(items, 1))
        return f'    <ol class="toc-list">\n{rows}\n    </ol>'

    out = []
    for g in groups:
        s, e = g["start"], g["end"]
        if s > e:
            continue
        rng = f"{s:02d}" if s == e else f"{s:02d}–{e:02d}"
        rows = "\n".join(li(n, items[n - 1]) for n in range(s, e + 1))
        out.append(
            f'    <div class="toc-group">\n'
            f'      <div class="toc-g-head"><span class="toc-g-range">{rng}</span>'
            f'<span class="toc-g-name">{esc(g["name"])}</span></div>\n'
            f'      <ol class="toc-list">\n{rows}\n      </ol>\n'
            f"    </div>"
        )
    return "\n".join(out)


def build_body(items, tail, date_str, groups):
    """目次と本文を返す。用語注釈は本文だけに掛ける（目次に点線が並ぶと読みにくい）。"""
    nav = [
        '<nav class="toc">',
        '  <div class="toc-head">',
        f'    <span class="toc-title">目次 — {len(items)}件</span>',
        '    <span class="ctrl">',
        '      <button class="btn" id="easy-mode" type="button">やさしく表示</button>',
        '      <button class="btn" id="toggle-all" type="button">すべて開く</button>',
        "    </span>",
        "  </div>",
        build_toc(items, groups),
        '  <p class="toc-note">用語の点線をタップすると説明が出ます。</p>',
        "</nav>",
    ]

    blocks = []
    starts = {g["start"]: g["name"] for g in groups}

    for n, it in enumerate(items, 1):
        if n in starts:
            blocks.append(f'<h3 class="group">{esc(starts[n])}</h3>')
        summary, easy, detail_lines = split_item(it["lines"])
        detail = render(detail_lines).strip()
        blocks.append('<section class="item">')
        blocks.append(f'  <h2 id="i{n}"><span class="num">{n:02d}</span>{inline(it["title"])}</h2>')
        if summary:
            blocks.append(f'  <p class="sum">{inline(summary)}</p>')
        if easy:
            blocks.append(f'  <p class="easy"><span class="easy-tag">かんたんに言うと</span>{inline(easy)}</p>')
        if detail:
            fig = DOCS / "img" / f"{date_str}-{n:02d}.png"
            fig_html = (f'<img class="item-img" src="img/{fig.name}" alt="" '
                        f'width="1600" height="900">') if fig.exists() else ""
            blocks.append("  <details>")
            blocks.append("    <summary>詳しく読む</summary>")
            blocks.append(f'    <div class="detail">{fig_html}{detail}</div>')
            blocks.append("  </details>")
        blocks.append("</section>")

    tail_html = render(tail).strip()
    if tail_html:
        blocks.append(f'<div class="box"><div class="box-title">今日の空振り</div>{tail_html}</div>')

    return "\n".join(nav), "\n".join(blocks)


def page(title, date_str, lead_lines, items, tail, prev_link, next_link, desc, groups):
    y, mth, d = map(int, date_str.split("-"))
    wd = WEEKDAY_JA[datetime.date(y, mth, d).weekday()]

    nav = []
    if prev_link:
        nav.append(f'<a href="{prev_link}">← 前の号</a>')
    nav.append('<a href="index.html">バックナンバー</a>')
    if next_link:
        nav.append(f'<a href="{next_link}">次の号 →</a>')

    img = ""
    if (DOCS / "img" / f"{date_str}.png").exists():
        img = f'  <img class="card-img" src="img/{date_str}.png" alt="" width="1600" height="900">'

    lead = ""
    if lead_lines:
        lead = '  <p class="lead">' + "<br>".join(inline(x) for x in lead_lines) + "</p>"

    nav_html, body_html = build_body(items, tail, date_str, groups)
    body_html = annotate(body_html, load_glossary())

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}｜AI Radar {date_str}</title>
{ogp(title, date_str, desc)}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<article>
  <div class="kicker">AI RADAR — 業務転用リサーチ</div>
  <h1>{esc(title)}</h1>
  <div class="dateline">{y}年{mth}月{d}日（{wd}）</div>
{img}
{lead}
{nav_html}
{body_html}
  <footer>
    判断軸は「明日から自分の業務に転用できるか」の一点。<br>
    収集方針は <code>config.md</code> に定義。書き換えれば翌朝から反映されます。
    <div class="nav">{' ・ '.join(nav)}</div>
  </footer>
</article>
</div>
<script>
(function () {{
  var all = document.getElementById('toggle-all');
  if (all) all.addEventListener('click', function () {{
    var open = all.textContent.indexOf('開く') >= 0;
    document.querySelectorAll('details').forEach(function (d) {{ d.open = open; }});
    all.textContent = open ? 'すべて閉じる' : 'すべて開く';
  }});

  var easy = document.getElementById('easy-mode');
  if (easy) {{
    if (localStorage.getItem('ai-radar-easy') === '1') {{
      document.body.classList.add('easy-on');
      easy.classList.add('on');
    }}
    easy.addEventListener('click', function () {{
      var on = document.body.classList.toggle('easy-on');
      easy.classList.toggle('on', on);
      try {{ localStorage.setItem('ai-radar-easy', on ? '1' : '0'); }} catch (e) {{}}
    }});
  }}

  document.querySelectorAll('.toc a').forEach(function (a) {{
    a.addEventListener('click', function () {{
      var sec = document.querySelector(a.getAttribute('href'));
      if (!sec) return;
      var d = sec.parentElement.querySelector('details');
      if (d) d.open = true;
    }});
  }});

  var pop = null;
  function close() {{ if (pop) {{ pop.remove(); pop = null; }} }}
  function show(el) {{
    close();
    pop = document.createElement('div');
    pop.className = 'term-pop';
    pop.innerHTML = '<b>' + el.textContent + '</b>' + el.getAttribute('data-d');
    document.body.appendChild(pop);
    var r = el.getBoundingClientRect();
    var w = Math.min(320, window.innerWidth - 24);
    pop.style.width = w + 'px';
    var left = Math.min(r.left + window.scrollX, window.innerWidth - w - 12);
    pop.style.left = Math.max(12, left) + 'px';
    pop.style.top = (r.bottom + window.scrollY + 8) + 'px';
  }}
  document.querySelectorAll('.term').forEach(function (el) {{
    el.addEventListener('click', function (e) {{ e.stopPropagation(); show(el); }});
    el.addEventListener('keydown', function (e) {{
      if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); show(el); }}
    }});
  }});
  document.addEventListener('click', close);
  window.addEventListener('scroll', close, {{ passive: true }});
}})();
</script>
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
    only = sys.argv[1] if len(sys.argv) > 1 else None
    all_dates = sorted(p.stem for p in ISSUES.glob("*.md"))
    entries = []

    for path in sorted(ISSUES.glob("*.md")):
        date_str = path.stem
        raw = path.read_text(encoding="utf-8")
        h1, lead_lines, lead_text, items, tail, groups = parse(raw)
        title = headline(h1, raw, date_str)
        entries.append((date_str, title, f"{date_str}.html"))

        if only and only != date_str:
            continue

        idx = all_dates.index(date_str)
        prev_link = f"{all_dates[idx - 1]}.html" if idx > 0 else None
        next_link = f"{all_dates[idx + 1]}.html" if idx < len(all_dates) - 1 else None

        (DOCS / f"{date_str}.html").write_text(
            page(title, date_str, lead_lines, items, tail,
                 prev_link, next_link, lead_text, groups),
            encoding="utf-8",
        )
        print(f"  生成: docs/{date_str}.html  {len(items):>2}件  「{title}」")

    entries.reverse()
    (DOCS / "index.html").write_text(index_page(entries), encoding="utf-8")
    print(f"  生成: docs/index.html（{len(entries)}号）")


if __name__ == "__main__":
    main()
