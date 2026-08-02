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

    ax.text(90, H - 110, title, fontproperties=BOLD, fontsize=44,
            color=INK, va="top", ha="left")
    if subtitle:
        ax.text(90, H - 180, subtitle, fontproperties=REG, fontsize=30,
                color=SUB, va="top", ha="left")
    ax.text(90, 52, f"AI Radar｜{date_str}", fontproperties=REG, fontsize=22,
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

    node_fs, hub_fs = 34, 46
    pad = 56

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


def draw_bar(ax, labels, values, suffix):
    """値ラベルを棒の上に大きく置く。目盛りとグリッドは出さない。"""
    labels, values = labels[:5], values[:5]
    n = len(labels)

    area_l, area_r = 150, W - 150
    baseline = 190
    top = H - 390  # 値ラベルがサブタイトルに当たらない高さに抑える
    slot = (area_r - area_l) / n
    bw = min(180, slot * 0.5)
    vmax = max(values) if values else 1

    ax.plot([area_l - 30, area_r + 30], [baseline, baseline],
            color=SUB, linewidth=1.6)

    for i, (lab, val) in enumerate(zip(labels, values)):
        cx = area_l + slot * (i + 0.5)
        h = (val / vmax) * (top - baseline) * 0.86
        ax.add_patch(Rectangle((cx - bw / 2, baseline), bw, h,
                               facecolor=ACCENT, edgecolor="none"))
        ax.text(cx, baseline + h + 34, f"{val}{suffix}", fontproperties=BOLD,
                fontsize=52, color=INK, ha="center", va="bottom")
        ax.text(cx, baseline - 40, lab, fontproperties=REG, fontsize=32,
                color=SUB, ha="center", va="top")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", help="YYYY-MM-DD")
    ap.add_argument("kind", choices=["diagram", "bar"])
    ap.add_argument("--title", required=True, help="全角20字以内")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--nodes", nargs="*", default=[], help="diagram用（最大5）")
    ap.add_argument("--hub", default="", help="diagram用の中心ラベル")
    ap.add_argument("--labels", nargs="*", default=[], help="bar用（最大5）")
    ap.add_argument("--values", nargs="*", type=float, default=[], help="bar用")
    ap.add_argument("--suffix", default="%", help="bar用の単位")
    args = ap.parse_args()

    fig, ax = base_canvas(args.title, args.subtitle, args.date)

    if args.kind == "diagram":
        if not args.nodes or not args.hub:
            ap.error("diagram には --nodes と --hub が必要")
        draw_diagram(ax, args.nodes, args.hub)
    else:
        if not args.labels or not args.values:
            ap.error("bar には --labels と --values が必要")
        vals = [int(v) if float(v).is_integer() else v for v in args.values]
        draw_bar(ax, args.labels, vals, args.suffix)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.date}.png"
    fig.savefig(out, dpi=DPI, facecolor=BG)
    plt.close(fig)
    print(f"  生成: docs/img/{args.date}.png  ({args.kind})")


if __name__ == "__main__":
    main()
