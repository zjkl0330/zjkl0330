#!/usr/bin/env python3
"""根据 snapshot.json 生成 assets/langs.svg 与 assets/contrib.svg。

零依赖，只用标准库。改完数据直接跑：
    python scripts/build-assets.py
"""
import json
import os
import random
import re
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")

# ---------- 语言条 ----------
LANG_COLOR = {
    "TypeScript": "#3178C6", "JavaScript": "#F7DF1E", "Vue": "#41B883",
    "HTML": "#E34F26", "CSS": "#663399", "Python": "#3572A5",
    "Shell": "#89E051", "SCSS": "#C6538C", "Dockerfile": "#384D54",
    "Batchfile": "#C1F12E", "Nix": "#7E7EFF",
}

FONT = "'Segoe UI',Helvetica,Arial,sans-serif"
DIM = "#7C8DB0"
TEXT = "#CBD5E1"
WHITE = "#FFFFFF"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_langs(snap, mode="light"):
    """GitHub 原生风的横向占比条：无卡片、无渐变，条从左边长出来。"""
    rows = snap["languages"]["rows"][:6]
    total = sum(r["bytes"] for r in snap["languages"]["rows"])
    dark = mode == "dark"
    fg = "#E6EDF3" if dark else "#1F2328"
    sub = "#8B949E" if dark else "#6E7781"
    track = "#21262D" if dark else "#EFF2F5"

    W = 900
    RH, y0 = 34, 22
    H = y0 + len(rows) * RH
    BX, BW = 112, 752

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'role="img" aria-label="language breakdown">' % (W, H, W, H),
        "",
        '  <g font-family="%s">' % FONT,
    ]

    for i, r in enumerate(rows):
        y = y0 + i * RH
        pct = r["bytes"] / total * 100
        col = LANG_COLOR.get(r["name"], "#8B949E")
        bw = max(3.0, BW * r["bytes"] / total)
        out += [
            '    <text x="0" y="%.1f" font-size="13.5" fill="%s">%s</text>'
            % (y + 12, fg, esc(r["name"])),
            '    <rect x="%d" y="%.1f" width="%d" height="8" rx="4" fill="%s"/>'
            % (BX, y + 4, BW, track),
            '    <rect x="%d" y="%.1f" width="%.1f" height="8" rx="4" fill="%s"/>'
            % (BX, y + 4, bw, col),
            '    <text x="%d" y="%.1f" text-anchor="end" font-size="12.5" fill="%s">%.2f%%</text>'
            % (W, y + 12, sub, pct),
        ]

    out += ["  </g>", "</svg>"]
    return "\n".join(out) + "\n"


# ---------- 贡献热力图 ----------
LEVEL = ["#1B2B3F", "#12483A", "#1F8A4C", "#33C46A", "#5AF29B"]
SNAKE_LIGHT = ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"]
SNAKE_DARK = ["#21262D", "#0E4429", "#006D32", "#26A641", "#39D353"]


def level_for(n, top):
    if n == 0:
        return 0
    q = [max(1, round(top * f)) for f in (0.12, 0.32, 0.6)]
    if n <= q[0]:
        return 1
    if n <= q[1]:
        return 2
    if n <= q[2]:
        return 3
    return 4


def build_contrib(snap, mode="light", lang="zh"):
    """最近 12 个月的月度柱状图 + 三个数字。热力图交给蛇那张，这里不重复。"""
    days = snap["contributions"]["days"]
    dark = mode == "dark"
    fg = "#E6EDF3" if dark else "#1F2328"
    sub = "#8B949E" if dark else "#6E7781"
    PAL = SNAKE_DARK if dark else SNAKE_LIGHT

    months, order = {}, []
    for d in days:
        k = d["date"][:7]
        if k not in months:
            months[k] = 0
            order.append(k)
        months[k] += d["c"]
    order = order[-12:]
    if len(order) > 2 and len([d for d in days if d["date"][:7] == order[-1]]) < 20:
        order = order[:-1]        # 当月还没过完，不画
    vals = [months[k] for k in order]
    top = max(vals) or 1
    total = sum(d["c"] for d in days)

    W, H = 900, 232
    PL, PB = 10, 176           # 绘图左边界、柱底基线
    CH = 108                    # 最大柱高
    n = len(vals)
    slot = (W - PL * 2) / n
    bw = min(52.0, slot - 14)

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'role="img" aria-label="monthly contributions">' % (W, H, W, H),
        "",
        '  <g font-family="%s">' % FONT,
        '    <line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1"/>'
        % (PL, PB + 1, W - PL, PB + 1, "#30363D" if dark else "#D8DEE4"),
    ]

    # 三个数字
    stats = [
        ("%s" % format(total, ","), "次贡献" if lang == "zh" else "contributions"),
        ("%d" % snap["contributions"]["longestStreak"],
         "最长连续（天）" if lang == "zh" else "longest streak"),
        ("%d" % snap["contributions"]["currentStreak"],
         "当前连续（天）" if lang == "zh" else "current streak"),
    ]
    for i, (num, lab) in enumerate(stats):
        x = PL + i * 210
        out += [
            '    <text x="%d" y="46" font-size="27" font-weight="700" fill="%s">%s</text>'
            % (x, fg, num),
            '    <text x="%d" y="66" font-size="11.5" fill="%s">%s</text>' % (x, sub, lab),
        ]

    # 柱子
    for i, (k, v) in enumerate(zip(order, vals)):
        h = 2.0 if v == 0 else max(4.0, (v / top) ** 0.42 * CH)
        x = round(PL + slot * i + (slot - bw) / 2, 1)
        lv = 4 if v >= top * 0.5 else 3
        out += [
            '    <rect x="%s" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
            % (x, PB - h, bw, h, PAL[lv]),
            '    <text x="%.1f" y="%d" text-anchor="middle" font-size="11" fill="%s">%s</text>'
            % (x + bw / 2, PB + 20, sub, str(int(k[5:7])) + "月" if lang == "zh" else
               ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                "Nov", "Dec"][int(k[5:7]) - 1]),
        ]

    out += ["  </g>", "</svg>"]
    return "\n".join(out) + "\n"


# ---------- 贡献贪吃蛇 ----------
SNAKE_T = 92.5        # 一轮（秒），对齐 Platane/snk


def build_snake(snap, mode="light"):
    """GitHub 原生贡献图 + 慢速随机蛇 + 底部进度条。

    全部用 CSS @keyframes（和 Platane/snk 同架构），不用 SMIL：
    371 个 <animate> 会让浏览器每帧重算整张图，这是上一版卡顿的原因。
    """
    days = snap["contributions"]["days"]
    dark = mode == "dark"
    PAL = (["#21262D", "#0E4429", "#006D32", "#26A641", "#39D353"] if dark else
           ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"])
    empty = PAL[0]
    # 蛇用中性墨色而不是绿色：热力图本身全是绿色系，绿色蛇在密集区会糊成一片。
    # 取 GitHub 正文色（浅色 #1B1F23 / 深色 #E6EDF3），和界面文字同色，最像原生控件。
    snake_col = "#E6EDF3" if dark else "#1B1F23"
    muted = "#8B949E" if dark else "#6E7781"
    edge = "rgba(240,246,252,.05)" if dark else "rgba(27,31,35,.05)"
    # 进度条空段的底色：比热力图空格深一档，否则在页面背景上看不见整条进度
    bar_empty = "#30363D" if dark else "#D8DEE4"

    cols, rows = 53, 7
    cell, step = 12, 16
    x0, y0 = 20, 26
    GW = cols * step - 4
    W = x0 + GW + 20
    bar_y = y0 + rows * step - 4 + 14
    H = bar_y + 12 + 14

    def val(c, r):
        i = c * rows + r
        return days[i]["c"] if i < len(days) else 0

    top = max(d["c"] for d in days) or 1

    # ---------- 路径：每步只走相邻格（蛇才不会散开）----------
    # 有没走过的邻居就走它（略偏向右）；全走过时朝最近的空格子靠，避免乱转
    rng = random.Random(sum(d["c"] for d in days) * 101 + len(days))
    allc = [(c, r) for c in range(cols) for r in range(rows)]
    cur = (0, rng.randrange(rows))
    path = [cur]
    seen = {cur}
    rest = [q for q in allc if q != cur]
    while rest:
        c, r = cur
        cand = [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)]
        cand = [q for q in cand if 0 <= q[0] < cols and 0 <= q[1] < rows]
        free = [q for q in cand if q not in seen]
        if free:
            wts = [2.6 if q[0] > c else 1.0 for q in free]
            nxt = rng.choices(free, weights=wts)[0]
        else:
            nxt = min(cand, key=lambda q: min(abs(q[0] - t[0]) + abs(q[1] - t[1]) for t in rest))
        path.append(nxt)
        if nxt in seen:
            pass
        else:
            seen.add(nxt)
            rest.remove(nxt)
        cur = nxt

    n = len(path) - 1
    first = {}
    for i, q in enumerate(path):
        first.setdefault(q, i)

    def pct(i):
        return round(i / n * 100, 3)

    # ---------- CSS ----------
    css = [
        ":root{--e:%s;--c1:%s;--c2:%s;--c3:%s;--c4:%s;--s:%s;--m:%s;--be:%s;--edge:%s}" % (
            empty, PAL[1], PAL[2], PAL[3], PAL[4], snake_col, muted, bar_empty, edge),
        ".c,.s,.u{animation-duration:%gs;animation-timing-function:linear;"
        "animation-iteration-count:infinite}" % SNAKE_T,
        ".c{fill:var(--e);stroke:var(--edge);stroke-width:.6px;width:12px;height:12px}",
        ".c.c1{fill:var(--c1)}.c.c2{fill:var(--c2)}.c.c3{fill:var(--c3)}.c.c4{fill:var(--c4)}",
    ]

    rects = []
    for c, r in allc:
        i = c * rows + r
        x, y = x0 + c * step, y0 + r * step
        v = val(c, r)
        if v > 0:
            lv = level_for(v, top)
            k = "k%d" % i
            t0 = pct(first[(c, r)])
            t1 = min(round(t0 + 0.03, 3), 99.99)
            css.append(".c.%s{fill:var(--c%d);animation-name:%s}" % (k, lv, k))
            css.append("@keyframes %s{%s%%{fill:var(--c%d)}%s%%,100%%{fill:var(--e)}}"
                       % (k, t0, lv, t1))
            rects.append('  <rect class="c %s" x="%d" y="%d"/>' % (k, x, y))
        else:
            rects.append('  <rect class="c" x="%d" y="%d"/>' % (x, y))

    # ---------- 蛇：4 节，尺寸依次收小，相位差一步 ----------
    css.append(".s{fill:var(--s)}")
    SIZES = [(14.4, 4.5), (12.3, 4.1), (10.8, 3.6), (9.9, 3.3)]
    for k in range(4):
        frames = []
        for i in range(n + 1):
            q = path[max(0, i - k)]
            frames.append("%s%%{transform:translate(%dpx,%dpx)}"
                          % (pct(i), x0 + q[0] * step + cell // 2,
                             y0 + q[1] * step + cell // 2))
        css.append(".s.s%d{animation-name:sk%d}" % (k, k))
        css.append("@keyframes sk%d{%s}" % (k, "".join(frames)))
    snakes = []
    for k, (sz, rx) in enumerate(SIZES):
        snakes.append('  <rect class="s s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                      'rx="%.1f" ry="%.1f"/>' % (k, -sz / 2, -sz / 2, sz, sz, rx, rx))

    # ---------- 底部：每日贡献条，连续同色合并成实心长条（不逐格画，否则像条形码）----------
    BH = 12
    bw = GW / len(allc)

    def cell_col(q):
        v = val(*q)
        return "var(--be)" if v == 0 else "var(--c%d)" % level_for(v, top)

    segs = []
    idx = 0
    while idx < len(allc):
        col = cell_col(allc[idx])
        j = idx
        while j + 1 < len(allc) and cell_col(allc[j + 1]) == col:
            j += 1
        segs.append((idx, j + 1, col))
        idx = j + 1

    bars = ['  <g class="u">']
    for a, b, col in segs:
        bars.append('    <rect x="%.2f" y="%d" width="%.2f" height="%d" rx="1" fill="%s"/>'
                    % (x0 + a * bw, bar_y, (b - a) * bw, BH, col))
    bars.append("  </g>")
    css.append(".u{clip-path:inset(0 %.0fpx 0 0);animation-name:rv}" % GW)
    css.append("@keyframes rv{0%%{clip-path:inset(0 %.0fpx 0 0)}100%%{clip-path:inset(0 0 0 0)}}" % GW)

    # ---------- 月份 / 星期标签 ----------
    labels = []
    seen_m, last_wk = set(), -9
    for i, d in enumerate(days):
        dt = datetime.date.fromisoformat(d["date"])
        wk = i // rows
        if dt.day <= 7 and dt.month not in seen_m and wk - last_wk >= 3:
            seen_m.add(dt.month)
            last_wk = wk
            labels.append('  <text x="%d" y="%d" font-family="%s" font-size="11" fill="var(--m)">%d月</text>'
                          % (x0 + wk * step, y0 - 10, FONT, dt.month))
    for row_i, lbl in ((1, "一"), (3, "三"), (5, "五")):
        labels.append('  <text x="%d" y="%d" text-anchor="end" font-family="%s" font-size="10" '
                      'fill="var(--m)">%s</text>'
                      % (x0 - 8, y0 + row_i * step + cell // 2 + 3.5, FONT, lbl))

    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
        'role="img" aria-label="contribution snake">' % (W, H, W, H),
        "  <style>" + "".join(css) + "</style>",
    ] + labels + rects + bars + snakes + ["</svg>"]
    return "\n".join(out) + "\n"


def main():
    with open(os.path.join(HERE, "snapshot.json"), encoding="utf-8") as f:
        snap = json.load(f)
    jobs = [
        ("langs.svg", lambda x, m: build_langs(x, m), "light"),
        ("langs-dark.svg", lambda x, m: build_langs(x, m), "dark"),
        ("contrib.svg", lambda x, m: build_contrib(x, m, "zh"), "light"),
        ("contrib-dark.svg", lambda x, m: build_contrib(x, m, "zh"), "dark"),
        ("contrib-en.svg", lambda x, m: build_contrib(x, m, "en"), "light"),
        ("contrib-en-dark.svg", lambda x, m: build_contrib(x, m, "en"), "dark"),
        ("snake.svg", build_snake, "light"),
        ("snake-dark.svg", build_snake, "dark"),
    ]
    for name, fn, lang in jobs:
        with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
            f.write(fn(snap, lang))
        print("wrote assets/" + name)


if __name__ == "__main__":
    main()
