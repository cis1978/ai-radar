#!/usr/bin/env python3
"""
AI Radar — 一次情報の取得スクリプト

主要AI企業・ツールの公式ブログ/リリースノートのRSSを取得し、
直近N日ぶんの記事を feeds_latest.json に書き出す。

判断はしない。「公式が何を出したか」を取りこぼさないための機械的な部分だけを担う。
記事の取捨選択と転用アイデアはClaudeが担当する。

使い方（shujiさんのMacのターミナルで実行）:
    cd ~/Desktop/AI_Infomration
    python3 scripts/fetch_feeds.py            # 直近3日
    python3 scripts/fetch_feeds.py --days 7   # 直近7日

依存: 標準ライブラリのみ（pip install 不要）

■ 重要な制約
Claudeの実行環境（サンドボックス）はネットワークが許可制で、
anthropic.com / github.com / pypi.org 以外の外部ドメインに到達できない。
そのため **このスクリプトは毎朝の自動実行では使われない**。
自動実行側は、公式ドメインに限定したWeb検索で一次情報を取っている（config.md 参照）。

このスクリプトが役に立つのは以下の場合:
  - shujiさんが自分のMacで手動実行するとき（制約なし。全フィード取れる）
  - 後日、Mac側のcronで定期実行するようにしたくなったとき
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------
# 情報源。追加・削除はこのリストを編集するだけでよい。
# ---------------------------------------------------------------
# 注: anthropic.com はRSSを公開していないため（/rss.xml, /feed.xml など全て404）
#     Anthropicの動向は自動実行側のドメイン限定検索でカバーしている。
FEEDS = [
    ("OpenAI Blog",         "https://openai.com/news/rss.xml"),
    ("Google AI Blog",      "https://blog.google/technology/ai/rss/"),
    ("Google DeepMind",     "https://deepmind.google/blog/rss.xml"),
    ("Microsoft 365 Blog",  "https://www.microsoft.com/en-us/microsoft-365/blog/feed/"),
    ("Slack Changelog",     "https://api.slack.com/changelog/feed"),
    ("Notion Releases",     "https://www.notion.com/releases/rss.xml"),
    ("Hugging Face Blog",   "https://huggingface.co/blog/feed.xml"),
    ("AWS ML Blog",         "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("Simon Willison",      "https://simonwillison.net/atom/everything/"),
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AI-Radar/1.0"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def strip_html(text: str) -> str:
    """タグを落として空白を正規化する。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#\d+;", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(raw: str):
    """RSS(RFC822) と Atom(ISO8601) の両方を受ける。失敗したら None。"""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def text_of(node, *paths):
    """最初に見つかった非空のテキストを返す。"""
    for p in paths:
        found = node.find(p, NS) if p.startswith("atom:") else node.find(p)
        if found is not None:
            if found.text and found.text.strip():
                return found.text.strip()
            # Atom の link は href 属性に入る
            href = found.get("href")
            if href:
                return href.strip()
    return ""


def parse_feed(xml_bytes: bytes, source: str):
    """RSS 2.0 と Atom の両方を扱う。"""
    root = ET.fromstring(xml_bytes)
    entries = []

    # RSS 2.0
    items = root.findall(".//item")
    if items:
        for it in items:
            entries.append({
                "source":  source,
                "title":   strip_html(text_of(it, "title")),
                "url":     text_of(it, "link", "guid"),
                "summary": strip_html(text_of(it, "description"))[:400],
                "raw_date": text_of(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date"),
            })
        return entries

    # Atom
    for it in root.findall("atom:entry", NS):
        link = ""
        for ln in it.findall("atom:link", NS):
            rel = ln.get("rel", "alternate")
            if rel == "alternate":
                link = ln.get("href", "")
                break
        entries.append({
            "source":  source,
            "title":   strip_html(text_of(it, "atom:title")),
            "url":     link or text_of(it, "atom:id"),
            "summary": strip_html(text_of(it, "atom:summary", "atom:content"))[:400],
            "raw_date": text_of(it, "atom:updated", "atom:published"),
        })
    return entries


def fetch(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="何日前まで拾うか（既定3日）")
    ap.add_argument("--out", default=None, help="出力先JSON")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    collected, problems = [], []

    for source, url in FEEDS:
        try:
            entries = parse_feed(fetch(url), source)
        except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, TimeoutError, OSError) as e:
            problems.append(f"{source}: {type(e).__name__} {e}")
            continue

        kept = 0
        for e in entries:
            dt = parse_date(e.pop("raw_date", ""))
            if dt is None or dt < cutoff:
                continue
            e["published"] = dt.isoformat()
            collected.append(e)
            kept += 1
        print(f"  {source:<22} {kept:>3} 件 (全{len(entries)}件中)", file=sys.stderr)

    collected.sort(key=lambda x: x["published"], reverse=True)

    out_path = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "feeds_latest.json"
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "count": len(collected),
        "errors": problems,
        "entries": collected,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(collected)} 件を {out_path} に保存", file=sys.stderr)
    if problems:
        print(f"取得できなかったフィード {len(problems)} 件:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
