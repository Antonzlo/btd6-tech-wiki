"""Maps page from the Mod Helper export (data/Maps/<difficulty>/<id>.json): water, co-op split, difficulty."""
from wiki.core import DATA, INDEX, card, esc, icon, load, page, t
from wiki import core

# CoopDivision enum of the game (code, not in the export); only the values the maps use are named
COOP_SPLIT = {0: "общее поле", 1: "горизонтально", 2: "вертикально", 3: "по диагонали", 4: "по диагонали"}


def build_maps():
    # one folder per difficulty, in the game's difficulty order
    folders = sorted((p for p in (DATA / "Maps").iterdir() if p.is_dir()), key=lambda p: load(next(p.glob("*.json")))["difficulty"])
    label = {p.name: t(f"MD {p.name}", fallback=p.name)[:1].upper() + t(f"MD {p.name}", fallback=p.name)[1:] for p in folders}
    rows = []
    for folder in folders:
        level = label[folder.name]
        maps = [load(f) for f in sorted(folder.glob("*.json"))]
        for m in sorted((m for m in maps if t(m["id"], fallback="")), key=lambda m: t(m["id"])):  # no name: editor stub
            name = t(m["id"])
            INDEX.append([name, "Карты", f"{core.current_file}#m-{m['id']}", m["id"]])
            tags = [folder.name.lower(), "water" if m["hasWater"] else "dry"] + (["browser"] if m["isBrowserOnly"] else [])
            badge = " <span class='badge'><b>только браузерная версия</b></span>" if m["isBrowserOnly"] else ""
            cells = (f"<div class='ach'>{icon('maps', m['id'], 64, 'ic mapic')}<span><b id='m-{esc(m['id'])}'>{esc(name)}</b>{badge}</span></div>",
                     esc(level), "есть" if m["hasWater"] else "нет",
                     esc(COOP_SPLIT.get(m["coopMapDivisionType"], str(m["coopMapDivisionType"]))))
            rows.append(f"<tr data-tags='{' '.join(tags)}'>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    filters = [("", "Все")] + [(p.name.lower(), label[p.name]) for p in folders] + [("water", "С водой"), ("dry", "Без воды")]
    bar = ("<div class='tagbar' data-target='#maps-t'>" + "".join(
        f"<button type='button' data-tag='{k}'{' class=on' if not k else ''}>{esc(n)}</button>" for k, n in filters) + "</div>")
    head = "".join(f"<th>{h}</th>" for h in ("Карта", "Сложность", "Вода", "Деление в кооперативе"))
    body = (bar + "<input class='filter' type='search' placeholder='Фильтр: название карты' aria-label='Фильтр карт' "
            "data-filter='#maps-t tbody tr'>"
            f"<div class='wrap'><table id='maps-t'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    page("maps.html", "Карты", f"Все {len(rows)} карт: сложность, есть ли вода для водных башен, как поле делится в кооперативе.",
         card("all", "Карты", body, section="Карты"), [("all", "Карты")])
