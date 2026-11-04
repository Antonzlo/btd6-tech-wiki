"""Inline SVG line charts."""
from wiki.core import esc, fmt


def line_chart(ys, xticks, aria, ylabel=fmt, tip=lambda x, y: f"{x}: {fmt(y)}"):
    """One-series line chart; x is 1..len(ys), each point has a hover tooltip (tip(x, y))."""
    w, h, pad, left = 640, 220, 36, 54
    top = max(ys) or 1
    x = lambda i: left + (w - left - pad) * i / (len(ys) - 1)
    y = lambda v: h - pad - (h - 2 * pad) * v / top
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ys))
    ticks = "".join(f"<text x='{x(n - 1):.1f}' y='{h - pad + 16}' text-anchor='middle'>{n}</text>" for n in xticks)
    yt = "".join(f"<text x='{left - 6}' y='{y(v) + 4:.1f}' text-anchor='end'>{ylabel(v)}</text>" for v in (0, top / 2, top))
    grid = "".join(f"<line class='pgrid' x1='{left}' y1='{y(v):.1f}' x2='{w - pad}' y2='{y(v):.1f}'/>" for v in (top / 2, top))
    step = (w - left - pad) / (len(ys) - 1)  # hover targets wider than the line
    hits = "".join(f"<rect class='phit' x='{x(i) - step / 2:.1f}' y='{pad}' width='{step:.1f}' height='{h - 2 * pad}'>"
                   f"<title>{tip(i + 1, v)}</title></rect>" for i, v in enumerate(ys))
    return (f"<div class='wrap'><svg class='pchart' viewBox='0 0 {w} {h}' width='{w}' role='img' aria-label='{esc(aria)}'>"
            f"{grid}<line class='paxis' x1='{left}' y1='{h - pad}' x2='{w - pad}' y2='{h - pad}'/>"
            f"<polyline class='pline' points='{pts}'/>{ticks}{yt}{hits}</svg></div>")


def dual_line_chart(ys1, ys2, xticks, aria, ylabel1=fmt, ylabel2=fmt,
                    tip=lambda x, y1, y2: f"{x}: {fmt(y1)} · {fmt(y2)}",
                    legend=("За раунд (слева)", "Всего с 1-го раунда (справа)"), ys3=None,
                    legend3="Множитель дохода, %"):
    """Line chart with dual Y axes (left for ys1, right for ys2) and an optional unlabeled third series ys3
    of fractions drawn against max(1, its peak) at full height, values in the tooltips; x is 1..len(ys1)."""
    w, h, pad, left, right = 640, 230, 36, 54, 54
    top1 = max(ys1) or 1
    top2 = max(ys2) or 1
    x = lambda i: left + (w - left - right) * i / (len(ys1) - 1)
    y1 = lambda v: h - pad - (h - 2 * pad) * v / top1
    y2 = lambda v: h - pad - (h - 2 * pad) * v / top2
    pts1 = " ".join(f"{x(i):.1f},{y1(v):.1f}" for i, v in enumerate(ys1))
    pts2 = " ".join(f"{x(i):.1f},{y2(v):.1f}" for i, v in enumerate(ys2))
    top3 = max(1, *ys3) if ys3 else 1
    pts3 = " ".join(f"{x(i):.1f},{h - pad - (h - 2 * pad) * v / top3:.1f}" for i, v in enumerate(ys3)) if ys3 else ""
    pct = lambda i: f" · множитель {ys3[i] * 100:g}%" if ys3 else ""
    ticks = "".join(f"<text x='{x(n - 1):.1f}' y='{h - pad + 16}' text-anchor='middle'>{n}</text>" for n in xticks)
    yt1 = "".join(f"<text class='yt1' x='{left - 6}' y='{y1(v) + 4:.1f}' text-anchor='end'>{ylabel1(v)}</text>"
                  for v in (0, top1 / 2, top1))
    yt2 = "".join(f"<text class='yt2' x='{w - right + 6}' y='{y2(v) + 4:.1f}' text-anchor='start'>{ylabel2(v)}</text>"
                  for v in (0, top2 / 2, top2))
    grid = "".join(f"<line class='pgrid' x1='{left}' y1='{y1(v):.1f}' x2='{w - right}' y2='{y1(v):.1f}'/>"
                   for v in (top1 / 2, top1))
    step = (w - left - right) / (len(ys1) - 1)
    hits = "".join(f"<rect class='phit' x='{x(i) - step / 2:.1f}' y='{pad}' width='{step:.1f}' height='{h - 2 * pad}'>"
                   f"<title>{tip(i + 1, ys1[i], ys2[i])}{pct(i)}</title></rect>" for i in range(len(ys1)))
    leg = (f"<div class='chart-legend'><span class='leg-s1'>● {esc(legend[0])}</span> "
           f"<span class='leg-s2'>● {esc(legend[1])}</span>"
           + (f" <span class='leg-s3'>● {esc(legend3)}</span>" if ys3 else "") + "</div>")
    return (f"<div class='wrap'>{leg}<svg class='pchart' viewBox='0 0 {w} {h}' width='{w}' role='img' aria-label='{esc(aria)}'>"
            f"{grid}<line class='paxis' x1='{left}' y1='{h - pad}' x2='{w - right}' y2='{h - pad}'/>"
            + (f"<polyline class='pline pline3' points='{pts3}'/>" if ys3 else "")
            + f"<polyline class='pline pline2' points='{pts2}'/>"
            f"<polyline class='pline' points='{pts1}'/>"
            f"{ticks}{yt1}{yt2}{hits}</svg></div>")
