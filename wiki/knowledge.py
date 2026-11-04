"""Monkey Knowledge and powers pages, plus the knowledge card on tower pages."""
import collections
import functools
import re
from wiki.core import (
    DATA, Raw, card, esc, flatten, fmt, game_text, group, icon, json_files, kv_table, load, page, stats, t,
    table, webp_uri,
)
from wiki.mods import mod_table


LAYOUT_DIR = DATA / "KnowledgeLayout"


def load_game_layout():
    """Positions dumped from the in-game Monkey Knowledge screen (btd6-knowledge-dumper), by set."""
    path = LAYOUT_DIR / "layout.json"
    if not path.exists():
        return {}
    out = {}
    for e in load(path):
        out.setdefault(e["set"], []).append(e)
    return out


def icon_uri(kid):
    return webp_uri(LAYOUT_DIR / "icons" / f"{kid}.webp")


def kicon(kid, size, cls="ic"):
    """Knowledge icon drawn from the page's shared symbol (each image is embedded once per page)."""
    if not icon_uri(kid):
        return ""
    return (f"<svg class='{cls}' width='{size}' height='{size}' viewBox='0 0 1 1' aria-hidden='true'>"
            f"<use href='#k-{esc(kid)}'/></svg>")


def knowledge_symbols(ids):
    defs = "".join(f"<symbol id='k-{esc(k)}' viewBox='0 0 1 1'><image href='{icon_uri(k)}' width='1' height='1'/></symbol>"
                   for k in sorted(ids) if icon_uri(k))
    return f"<svg width='0' height='0' style='position:absolute' aria-hidden='true'><defs>{defs}</defs></svg>"


def knowledge_game_graph(entries, nodes, get_ancestors=None):
    """The tree exactly as the game lays it out: icon buttons, stem/arrow/elbow pieces, tier bands."""
    S, pad_l, pad = 0.5, 70, 16
    boxes = [e["rect"] for e in entries] + [a["rect"] for e in entries for a in e["arrows"]]
    minx = min(r[0] - r[2] / 2 for r in boxes)
    maxx = max(r[0] + r[2] / 2 for r in boxes)
    maxy = max(r[1] + r[3] / 2 for r in boxes)
    miny = min(r[1] - r[3] / 2 for r in boxes)
    X = lambda v: pad_l + (v - minx) * S
    Y = lambda v: pad + (maxy - v) * S
    width, height = pad_l + (maxx - minx) * S + pad, (maxy - miny) * S + pad * 2

    bands = []
    for i, tier in enumerate(sorted({e["tier"] for e in entries})):
        rs = [e["rect"] for e in entries if e["tier"] == tier]
        top = Y(max(r[1] + r[3] / 2 for r in rs)) - 10
        bottom = Y(min(r[1] - r[3] / 2 for r in rs)) + 10
        bands.append(f"<rect class='band{i % 2}' x='0' y='{top:.0f}' width='{width:.0f}' height='{bottom - top:.0f}' rx='12'/>"
                     f"<text class='bandlbl' x='12' y='{top + 22:.0f}'>{tier} очк.</text>")

    pieces = []
    for e in entries:
        for a in e["arrows"]:
            cx, cy, w, h = X(a["rect"][0]), Y(a["rect"][1]), abs(a["w"]) * S, abs(a["h"]) * S
            tf = f"translate({cx:.1f},{cy:.1f}) rotate({-a['rot']:.0f}) scale({a.get('sx', 1):.0f},{a.get('sy', 1):.0f})"
            sprite = a.get("sprite") or ""
            if "Arrow" in sprite:  # head, points down in its own space
                shape = f"<path d='M{-w / 2:.1f},{-h / 2:.1f} L{w / 2:.1f},{-h / 2:.1f} L0,{h / 2:.1f} Z'/>"
            elif "Elbow" in sprite:  # corner joint where a horizontal and vertical stem meet
                shape = f"<rect x='{-w / 2:.1f}' y='{-h / 2:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{min(w, h) / 3:.1f}'/>"
            else:  # stem
                shape = f"<rect x='{-w / 2:.1f}' y='{-h / 2:.1f}' width='{w:.1f}' height='{h:.1f}' rx='2'/>"
            pieces.append(f"<g class='piece' transform='{tf}'>{shape}</g>")

    btns = []
    for e in entries:
        kid, d = e["id"], nodes.get(e["id"], {})
        cx, cy, size = X(e["rect"][0]), Y(e["rect"][1]), e["rect"][2] * S
        reqs = " ".join(p for p in d.get("prerequisiteIds") or [] if p in nodes)
        uri = icon_uri(kid)
        cost = d.get("monkeyMoneyCost")
        anc = get_ancestors(kid) if get_ancestors else set()
        branch_pts = len(anc) + 1
        branch_mm = sum(nodes[a].get("monkeyMoneyCost") or 0 for a in anc) + (d.get("monkeyMoneyCost") or 0)
        anc_attrs = f" data-anc-pts='{branch_pts}' data-anc-mm='{fmt(branch_mm)}'"
        btns.append(
            f"<a href='#{esc(kid)}' class='kn' data-id='{esc(kid)}' data-req='{esc(reqs)}' "
            f"data-name='{esc(t(kid, fallback=kid))}' data-cost='{fmt(cost)}' data-desc='{esc(t(kid + 'Description', kid + ' Description'))}'"
            f"{anc_attrs}>"
            f"<circle class='ring' cx='{cx:.1f}' cy='{cy:.1f}' r='{size / 2 - 2:.1f}'/>"
            + (f"<use href='#k-{esc(kid)}' x='{cx - size / 2:.1f}' y='{cy - size / 2:.1f}' width='{size:.1f}' height='{size:.1f}'/>" if uri else
               f"<text class='nm' x='{cx:.1f}' y='{cy:.1f}' text-anchor='middle'>{esc(t(kid, fallback=kid))[:10]}</text>")
            + (f"<text class='cost' x='{cx:.1f}' y='{cy + size / 2 + 2:.1f}' text-anchor='middle'>{fmt(cost)}</text>" if cost else "")
            + "</a>")
    return (f"<div class='wrap kgraph kgame'><svg viewBox='0 0 {width:.0f} {height:.0f}' width='{width:.0f}' role='img' "
            f"aria-label='Дерево знаний как в игре'>" + "".join(bands) + "".join(pieces) + "".join(btns)
            + "</svg><div class='ktip' hidden></div></div>")


def build_knowledge():
    body, toc = [], []
    GAME_LAYOUT = load_game_layout()
    for cat in sorted(p for p in (DATA / "Knowledge").iterdir() if p.is_dir()):
        nodes = {f.stem: load(f) for f in cat.glob("*.json")}

        def get_ancestors(kid):
            res = set()
            stack = list(nodes[kid].get("prerequisiteIds") or [])
            while stack:
                curr = stack.pop()
                if curr not in res and curr in nodes:
                    res.add(curr)
                    stack.extend(nodes[curr].get("prerequisiteIds") or [])
            return res

        cards = []
        for f in sorted(cat.glob("*.json"), key=lambda f: load(f).get("idx", 0)):
            d = nodes[f.stem]
            name = t(f.stem, fallback=f.stem)
            prereq = " ".join(f"<a class='badge' href='#{esc(p)}'><span>требует</span><b>"
                              f"{kicon(p, 18)}{esc(t(p, fallback=p))}</b></a>"
                              for p in d.get("prerequisiteIds") or [])
            anc = get_ancestors(f.stem)
            branch_pts = len(anc) + 1
            branch_mm = sum(nodes[a].get("monkeyMoneyCost") or 0 for a in anc) + (d.get("monkeyMoneyCost") or 0)
            inner = ("<div class='split'><div><div class='hero-row'>"
                     + kicon(f.stem, 84, "ic kicon")
                     + "<div>" + game_text(t(f"{f.stem}Description", f"{f.stem} Description"))
                     + stats([("Monkey Money", Raw(icon("ui", "mm", 22) + fmt(d.get("monkeyMoneyCost")))),
                              ("вложено в ветку", Raw(icon("ui", "knowledge", 22) + fmt(d.get("investmentRequired")))),
                              ("всего в ветке", Raw(icon("ui", "knowledge", 22) + str(branch_pts))),
                              ("сумма MM ветки", Raw(icon("ui", "mm", 22) + fmt(branch_mm)))])
                     + (f"<div class='chips'>{prereq}</div>" if prereq else "")
                     + "</div></div></div><div>" + mod_table((d.get("mod") or {}).get("mutatorMods") or []) + "</div></div>")
            cards.append(card(f.stem, name, inner, en_id=f.stem, section=f"Знания · {cat.name}"))
        body.append(f"<h2 id='{esc(cat.name)}' style='margin-top:32px'>{esc(t(cat.name, fallback=cat.name))}</h2>"
                    + (knowledge_game_graph(GAME_LAYOUT[cat.name], nodes, get_ancestors) if cat.name in GAME_LAYOUT else "<p class='note'>Нет раскладки: запустите KnowledgeDumper (F6).</p>")
                    + "".join(cards))
        toc.append((cat.name, t(cat.name, fallback=cat.name)))
    knav = "<nav class='knav'>" + "".join(
        f"<a href='#{esc(a)}'>{esc(n)}</a>" for a, n in toc) + "</nav>"
    page("knowledge.html", t("Monkey Knowledge", fallback="Monkey Knowledge"),
         "Деревья знаний как в игре. Наведите на знание, чтобы подсветить цепочку, нажмите, чтобы открыть "
         "его карточку. Число в углу знания это цена в Monkey Money.",
         knav + knowledge_symbols({p.stem for p in (DATA / "Knowledge").rglob("*.json")}) + "".join(body), toc)


def build_powers():
    labels = {"cost": "цена, MM", "quantity": "за покупку", "startCount": "в начале"}
    groups = {"powers": [], "pro": []}
    for f in json_files("Powers"):
        d = load(f)
        name = t(f.stem, fallback=f.stem)
        fl = flatten(d)
        nums = [(k, v) for k, v in fl.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        pic = icon("ui", f"power-{f.stem}", 84, "ic kicon")
        inner = ((f"<div class='hero-row'>{pic}<div>" if pic else "<div><div>")
                 + game_text(t(f"{f.stem} Description", f"{f.stem}Description"))
                 + stats([(labels[k], Raw(icon("ui", "mm", 22) + fmt(d[k])) if k == "cost" else d[k]) for k in labels if k in d])
                 + f"<details><summary>Все числовые параметры ({len(nums)})</summary>{kv_table(nums)}</details></div></div>")
        groups["pro" if "Pro" in f.stem else "powers"].append(card(f.stem, name, inner, en_id=f.stem, section="Силы"))
    page("powers.html", "Силы",
         "Силы и Powers Pro: урон, длительность, радиус, перезарядка.",
         group("powers", "Силы", groups["powers"]) + group("pro", "Powers Pro", groups["pro"]),
         [("powers", "Силы"), ("pro", "Powers Pro")])


@functools.cache
def knowledge_mods():
    """{knowledge id: its mutator mods}, for every knowledge in the dump."""
    return {f.stem: (load(f).get("mod") or {}).get("mutatorMods") or [] for f in (DATA / "Knowledge").rglob("*.json")}


def tower_knowledge(tid, folder, up_code):
    """Knowledge that changes a tower, all from the dump: {id: [tier codes where it starts]}, "000" = from placement.
    Sources: a tower model names the knowledge in a "mod" field; a knowledge names the tower (tower, baseTowerID,
    towerBaseId, comma lists) or one of its upgrades (upgradeName)."""
    known = knowledge_mods()
    seen = collections.defaultdict(set)
    for f in folder.glob(f"{tid}*.json"):
        code = "000" if f.stem == tid else f.stem.split("-", 1)[1]
        for k in re.findall(r'"mod":\s*"([^"]+)"', f.read_text(encoding="utf-8")):
            if k in known:
                seen[k].add(code)
    for k, mods in known.items():
        for m in mods:
            if tid in ",".join(str(m.get(f, "")) for f in ("tower", "baseTowerID", "towerBaseId")).split(","):
                seen[k].add("000")
            if m.get("upgradeName") in up_code:
                seen[k].add(up_code[m["upgradeName"]])
    out = {}
    for k, codes in seen.items():
        tiers = [c for c in codes if c.isdigit()]
        first = [c for c in tiers if not any(d != c and all(x <= y for x, y in zip(d, c)) for d in tiers)]
        out[k] = sorted(first) or sorted(codes)
    return out


@functools.cache
def common_knowledge():
    """Knowledge found on every tower (sell price, XP, ability cooldowns): listed once instead of in each table."""
    sets = [set(tower_knowledge(f.name, f, {})) for f in (DATA / "Towers").iterdir() if f.is_dir()]
    return set.intersection(*sets)


def knowledge_card(found):
    """Table linking to knowledge.html, ordered by the tier each knowledge starts working from."""
    common = common_knowledge()
    rows = []
    for k, codes in sorted(((k, c) for k, c in found.items() if k not in common), key=lambda kv: (kv[1][0] != "000", kv[1], t(kv[0], fallback=kv[0]))):
        when = "сразу" if codes == ["000"] else ", ".join("-".join(c) if c.isdigit() else c for c in codes[:4]) + (" …" if len(codes) > 4 else "")
        rows.append((Raw(f"<a class='mod-name' href='knowledge.html#{esc(k)}'>{kicon(k, 32)}{esc(t(k, fallback=k))}</a>"),
                     Raw(game_text(t(f"{k}Description", f"{k} Description"))), when))
    shared = " ".join(f"<a class='badge' href='knowledge.html#{esc(k)}'><b>{kicon(k, 18)}{esc(t(k, fallback=k))}</b></a>"
                      for k in sorted(common, key=lambda k: t(k, fallback=k)))
    return (knowledge_symbols(set(found)) + (table(["Знание", "Что даёт", "Действует с"], rows) if rows else "")
            + (f"<p class='note'>И общие для всех башен:</p><div class='chips'>{shared}</div>" if shared else "")
            + "<p class='note'>Из данных игры: знание записано в модели башни, или башня либо её улучшение указаны в самом знании. "
              "«Действует с» это первые тиры, в модели которых оно есть.</p>")
