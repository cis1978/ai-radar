#!/usr/bin/env python3
"""
AI Radar — Slackプレビュー用カード画像を生成する

その日の内容に応じて2種類のどちらかを作る。
  diagram : 構造・関係性が主役の日 → 箱と矢印の概念図（箱は5つまで）
  bar     : 数字が主役の日         → 棒グラフ（棒は5本まで）

出力: docs/img/YYYY-MM-DD.png（1600x900 / dpi=100）

使い方:
    python3 scripts/make_card.py 2026-08-03 diagram \
        --title "Excelスキルの実体はSKILL.md" \
        --subtitle "Claude・Slack・Excel が同じ形式に収束" \
        --nodes "Claude" "Slack" "Excel Copilot" \
        --hub "SKILL.md"

    python3 scripts/make_card.py 2026-08-04 bar \
        --title "Excelの伸びが突出" \
        --subtitle "Copilot エージェント機能 GA後1ヶ月の変化" \
        --labels "利用頻度" "継続率" "満足度" \
        --values 67 50 65 --suffix "%"

依存: matplotlib のみ（Noto Sans CJK JP を使用）
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrow, Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "img"

# 配色（この4色以外は使わない）
BG = "#ffffff"
INK = "#1a1a1a"
SUB = "#6b6b6b"
ACCENT = "#2f6fed"

W, H, DPI = 1600, 900, 100

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc",
]


def pick(paths):
    for p in paths:
        if Path(p).exists():
            return font_manager.FontProperties(fname=p)
    return font_manager.FontProperties()


REG = pick(FONT_CANDIDATES)
BOLD = pick(BOLD_CANDIDATES)


def base_canvas(title, subtitle, date_str):
    """タイトル・サブタイトル・クレジットだけ置いた土台を返す。"""
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.set_facecolor(BG)

    # スマホでは1600px幅が実質350px程度まで縮む（約0.22倍）。
    # 12px相当で読ませるには元が55pt前後必要なので、全体的に大きめに取っている。
    ax.text(90, H - 100, title, fontproperties=BOLD, fontsize=54,
            color=INK, va="top", ha="left")
    if subtitle:
        ax.text(90, H - 182, subtitle, fontproperties=REG, fontsize=36,
                color=SUB, va="top", ha="left")
    ax.text(90, 50, f"AI Radar｜{date_str}", fontproperties=REG, fontsize=26,
            color=SUB, va="center", ha="left")
    return fig, ax


def text_width(s, fontsize):
    """描画幅をざっくり見積もる。全角は約1.0em、半角は約0.56em。"""
    w = 0.0
    for ch in s:
        w += 1.0 if ord(ch) > 0x2E7F else 0.56
    return w * fontsize


def draw_diagram(ax, nodes, hub):
    """左に要素の箱、右にハブ。矢印で収束を表す。箱は最大5つ。"""
    nodes = nodes[:5]
    n = len(nodes)

    node_fs, hub_fs = 44, 56
    pad = 58

    # 最長ラベルに合わせて箱幅をそろえる（はみ出し防止）
    bw = max(300, max(text_width(s, node_fs) for s in nodes) + pad * 2)
    bh = 92
    hub_w = max(320, text_width(hub, hub_fs) + pad * 2)
    hub_h = 130

    # 左の箱・矢印・ハブの全体を横方向で中央に置く
    gap = 210
    total = bw + gap + hub_w
    left_x = (W - total) / 2
    hub_x = left_x + bw + gap

    top, bottom = H - 300, 170
    span = top - bottom
    step = span / max(n, 1)
    ys = [top - step * (i + 0.5) for i in range(n)]
    hub_y = sum(ys) / n

    for y in ys:
        ax.add_patch(Rectangle((left_x, y - bh / 2), bw, bh,
                               facecolor=BG, edgecolor=INK, linewidth=2.2))

    # 矢印の着地点をハブ左辺に分散させる（先端が重なって塊にならないように）
    inner = hub_h * 0.52
    if n > 1:
        targets = [hub_y + inner / 2 - inner * i / (n - 1) for i in range(n)]
    else:
        targets = [hub_y]

    for label, y, ty in zip(nodes, ys, targets):
        ax.text(left_x + bw / 2, y, label, fontproperties=BOLD, fontsize=node_fs,
                color=INK, ha="center", va="center")

        start = left_x + bw + 24
        end = hub_x - 14
        ax.add_patch(FancyArrow(
            start, y, end - start, ty - y,
            width=2.2, head_width=18, head_length=22,
            length_includes_head=True, color=SUB,
        ))

    ax.add_patch(Rectangle((hub_x, hub_y - hub_h / 2), hub_w, hub_h,
                           facecolor=ACCENT, edgecolor="none"))
    ax.text(hub_x + hub_w / 2, hub_y, hub, fontproperties=BOLD, fontsize=hub_fs,
            color=BG, ha="center", va="center")


def draw_map(ax, groups):
    """ダイジェスト号の表紙。「カテゴリ ＋ 該当番号」で中身の地図を示す。

    groups は "カテゴリ名|01-05|補足" の形の文字列リスト（補足は省略可）。
    """
    groups = groups[:4]
    name_fs, note_fs, badge_fs = 54, 36, 32
    # タイトルと補足の行間。グループ間の余白がこれより広くなるよう描画領域を取る
    gap = int(name_fs * 1.35)

    top, bottom = H - 285, 105
    step = (top - bottom) / max(len(groups), 1)

    for i, g in enumerate(groups):
        parts = [p.strip() for p in g.split("|")]
        name = parts[0]
        rng = parts[1] if len(parts) > 1 else ""
        note = parts[2] if len(parts) > 2 else ""
        y = top - step * (i + 0.5)

        # 補足がある行は2段になるので、バッジはタイトル行の高さに合わせる
        badge_y = y + gap / 2 if note else y

        if rng:
            bw = text_width(rng, badge_fs) + 46
            bh = badge_fs + 30
            ax.add_patch(Rectangle((110, badge_y - bh / 2), bw, bh,
                                   facecolor=ACCENT, edgecolor="none"))
            ax.text(110 + bw / 2, badge_y, rng, fontproperties=BOLD,
                    fontsize=badge_fs, color=BG, ha="center", va="center")
            x = 110 + bw + 36
        else:
            x = 110

        if note:
            ax.text(x, y + gap / 2, name, fontproperties=BOLD, fontsize=name_fs,
                    color=INK, ha="left", va="center")
            ax.text(x, y - gap / 2, note, fontproperties=REG, fontsize=note_fs,
                    color=SUB, ha="left", va="center")
        else:
            ax.text(x, y, name, fontproperties=BOLD, fontsize=name_fs,
                    color=INK, ha="left", va="center")


def draw_list(ax, headlines):
    """ダイジェスト号の表紙。その日の見出しを最大5本、番号付きで並べる。"""
    headlines = headlines[:5]
    fs = 44
    top, bottom = H - 310, 140
    step = (top - bottom) / max(len(headlines), 1)

    for i, text in enumerate(headlines):
        y = top - step * (i + 0.5)
        ax.text(110, y, f"{i + 1:02d}", fontproperties=BOLD, fontsize=32,
                color=ACCENT, ha="left", va="center")
        # 収まらない見出しは切って…を付ける（折り返すと行が潰れるため）
        limit = W - 340
        line, w = "", 0.0
        for ch in text:
            cw = fs if ord(ch) > 0x2E7F else fs * 0.56
            if w + cw > limit:
                break
            line += ch
            w += cw
        if len(line) < len(text):
            line = line[:-1] + "…"
        ax.text(230, y, line, fontproperties=BOLD, fontsize=fs,
                color=INK, ha="left", va="center")


def draw_bar(ax, labels, values, suffix):
    """値ラベルを棒の上に大きく置く。目盛りとグリッドは出さない。"""
    labels, values = labels[:5], values[:5]
    n = len(labels)

    # 棒が多いほどラベルが窮屈になるので、本数に応じて文字を落とす
    val_fs = 66 if n <= 3 else 56
    lab_fs = 42 if n <= 3 else 34

    area_l, area_r = 140, W - 140
    baseline = 215
    top = H - 400  # 値ラベルがサブタイトルに当たらない高さに抑える
    slot = (area_r - area_l) / n
    bw = min(200, slot * 0.5)
    vmax = max(values) if values else 1

    ax.plot([area_l - 30, area_r + 30], [baseline, baseline],
            color=SUB, linewidth=1.8)

    for i, (lab, val) in enumerate(zip(labels, values)):
        cx = area_l + slot * (i + 0.5)
        h = (val / vmax) * (top - baseline) * 0.86
        txt = f"{val:,}{suffix}" if val >= 10000 else f"{val}{suffix}"
        ax.add_patch(Rectangle((cx - bw / 2, baseline), bw, h,
                               facecolor=ACCENT, edgecolor="none"))
        ax.text(cx, baseline + h + 30, txt, fontproperties=BOLD,
                fontsize=val_fs, color=INK, ha="center", va="bottom")
        ax.text(cx, baseline - 42, lab, fontproperties=REG, fontsize=lab_fs,
                color=SUB, ha="center", va="top")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", help="YYYY-MM-DD")
    ap.add_argument("kind", choices=["diagram", "bar", "list", "map"])
    ap.add_argument("--title", required=True, help="全角20字以内")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--nodes", nargs="*", default=[], help="diagram用（最大5）")
    ap.add_argument("--hub", default="", help="diagram用の中心ラベル")
    ap.add_argument("--labels", nargs="*", default=[], help="bar用（最大5）")
    ap.add_argument("--values", nargs="*", type=float, default=[], help="bar用")
    ap.add_argument("--suffix", default="%", help="bar用の単位")
    ap.add_argument("--headlines", nargs="*", default=[], help="list用（最大5本の見出し）")
    ap.add_argument("--groups", nargs="*", default=[],
                    help='map用。"カテゴリ名|01-05|補足" の形で最大5つ')
    ap.add_argument("--out", default=None, help="出力先を明示する（項目ごとの図に使う）")
    args = ap.parse_args()

    fig, ax = base_canvas(args.title, args.subtitle, args.date)

    if args.kind == "map":
        if not args.groups:
            ap.error("map には --groups が必要")
        draw_map(ax, args.groups)
    elif args.kind == "list":
        if not args.headlines:
            ap.error("list には --headlines が必要")
        draw_list(ax, args.headlines)
    elif args.kind == "diagram":
        if not args.nodes or not args.hub:
            ap.error("diagram には --nodes と --hub が必要")
        draw_diagram(ax, args.nodes, args.hub)
    else:
        if not args.labels or not args.values:
            ap.error("bar には --labels と --values が必要")
        vals = [int(v) if float(v).is_integer() else v for v in args.values]
        draw_bar(ax, args.labels, vals, args.suffix)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / (args.out if args.out else f"{args.date}.png")
    fig.savefig(out, dpi=DPI, facecolor=BG)
    plt.close(fig)
    print(f"  生成: docs/img/{out.name}  ({args.kind})")


if __name__ == "__main__":
    main()
