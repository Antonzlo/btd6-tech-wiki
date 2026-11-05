"""Maps: the table page and one page per map.

Sources, each optional past the first:
- data/Maps/<difficulty>/<id>.json, Mod Helper export: difficulty, water, co-op split.
- data/KnowledgeLayout/maps.json, KnowledgeDumper map run (Ctrl+Shift+F9): path lengths, obstacle costs, events.
- data/KnowledgeLayout/maps_geo.json, same run: path points, area polygons, line of sight blockers, obstacle areas,
  in sim coordinates (y down, the screen is x -150..150, y -116..116). Drawn as an SVG on the map page.
The dump skips browser-only maps; a map or a file that is missing shows "–" or leaves its card out."""
import re

from wiki.core import DATA, card, esc, fmt, icon, load, page, stats, t, table
from wiki import core

# CoopDivision enum of the game (code, not in the export); only the values the maps use are named
COOP_SPLIT = {0: "общее поле", 1: "горизонтально", 2: "вертикально", 3: "по диагонали", 4: "по диагонали"}
# map and sim behaviours from the dump (model type names); unknown ones show by their type name
BEHAVIOURS = {"ApplyTowerFreezeModel": "замораживает башни", "ShipCaptureControllerModel": "захват корабля"}
# map event parts (trigger and action model types, "Model" cut off); map-specific ones keep their type name
TRIGGERS = {
    "RemoveableSoldTrigger": "препятствие убрано", "AfterRoundTrigger": "после раунда",
    "InteractableClickTrigger": "клик по объекту", "InteractableClickSequenceTrigger": "серия кликов по объекту",
    "StartRoundTrigger": "начало раунда", "SimTimeElapsedTrigger": "по таймеру", "StartMapTrigger": "старт карты",
    "RoundRemoveableStartedTrigger": "раунд появления препятствия", "TowerPlacedTrigger": "башня поставлена",
    "OnProjectileHitTrigger": "попадание снаряда", "BloonsPoppedTrigger": "лопнуты шары",
    "OnMapCreatedTrigger": "карта создана", "OnMapLoadedWithActiveRegenRemovableTrigger": "загрузка с отросшим препятствием",
    "PreBloonSpawnTrigger": "перед появлением шара", "LivesLowerThanTrigger": "жизней меньше порога",
    "RepeatableTrigger": "повторяется", "ReverseModeTrigger": "режим Reverse", "TowerInAreaTrigger": "башня в области",
}
ACTIONS = {
    "DestroyAreaAction": "убирает область", "DestroyAreasAction": "убирает области",
    "CreateAreaAction": "создаёт область", "CreateAreasAction": "создаёт области",
    "TriggerMapActionsAction": "запускает действия карты", "MapEventActiveAction": "включает событие карты",
    "RemovableActiveAction": "включает препятствие", "SellRemoveableAction": "убирает препятствие",
    "EmitProjectileAction": "выпускает снаряд", "ChangeEmitProjectileAction": "меняет снаряд",
    "EnablePathTargetZoneAction": "включает зону пути", "MovingPlatformAction": "двигает платформу",
    "PathActiveAction": "включает или выключает путь", "ToggleSplitterAction": "переключает развилку",
    "ChangeSimTimeElapsedTriggerAction": "меняет таймер", "CycleAreasAction": "переключает области по кругу",
    "CreateTowerAction": "ставит башню", "RotateAreaAction": "вращает область",
}
AREA_NAMES = {"land": "суша", "water": "вода", "track": "трек", "unplaceable": "нельзя ставить", "ice": "лёд",
              "removable": "препятствие", "waterMermonkey": "вода для Mermonkey", "shallowWater": "мелководье"}
LAYERS = [("land", "Суша"), ("water", "Вода"), ("track", "Трек"), ("unplaceable", "Нельзя ставить"),
          ("path", "Пути"), ("los", "Блокеры обзора"), ("rm", "Препятствия")]


def optional(name):
    f = DATA / "KnowledgeLayout" / name
    return load(f) if f.exists() else None


def slug(map_id):
    return re.sub(r"[^A-Za-z0-9]", "", map_id)  # "#ouch": a # in a file name would start the URL fragment


def pts(points):
    return " ".join(f"{x:g},{y:g}" for x, y in points)


def path_d(poly, holes=()):
    return "".join(f"M{pts(p).replace(' ', 'L')}Z" for p in [poly, *holes] if p)


def inside(x, y, poly):
    """Even-odd point in polygon."""
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def unique_paths(geo):
    """Paths with identical points drawn once; the count is how many spawners share the track."""
    out = {}
    for p in geo["paths"]:
        key = tuple(map(tuple, p["points"]))
        if key in out:
            out[key]["n"] += 1
            out[key]["ids"].append(p.get("id", ""))
        else:
            out[key] = {**p, "n": 1, "ids": [p.get("id", "")]}
    return list(out.values())


def length(points):
    return sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(points, points[1:]))


def sold_effects(geo, r):
    """What removing this obstacle does by map events (areas and paths that go or come), as data attributes the
    page applies when the obstacle is clicked away."""
    events = [e for e in geo.get("events") or []
              if any(kind(tr) == "RemoveableSoldTrigger" and tr.get("removableName") == r.get("obj") for tr in e.get("triggers") or [])
              and not (e.get("allTriggersRequired") and len(e.get("triggers") or []) > 1)]  # needs more than the removal
    return effects(geo, events)


def effects(geo, events):
    """Areas that go (off) or come (on) and paths turned on or off by these events, as data attributes."""
    ids = {a.get("name"): a["id"] for a in geo["areas"] if a.get("name")}
    eff = {"off": [], "on": [], "poff": [], "pon": []}
    for e in events:
        for a in e.get("actions") or []:
            k = kind(a)
            names = a.get("areaNames") or ([a["areaName"]] if a.get("areaName") else [])
            if k in ("DestroyAreaAction", "DestroyAreasAction"):
                eff["off"] += [ids[n] for n in names if n in ids]
            elif k in ("CreateAreaAction", "CreateAreasAction"):
                eff["on"] += [ids[n] for n in names if n in ids]
            elif k == "PathActiveAction":
                eff["pon" if a.get("setActiveToo") else "poff"].append(a.get("pathName"))
            elif k == "ToggleSplitterAction":
                eff["pon"] += a.get("pathsToActivate") or []
                eff["poff"] += a.get("pathsToDeactivate") or []
    return "".join(f" data-{k}='{esc(' '.join(map(str, v)))}'" for k, v in eff.items() if v)


def rm_center(geo, r):
    """Where an obstacle is: the middle of its areas. Its own position is where the game puts the "remove" button
    (off by 5 to 130 units on some maps), used only when it has no areas."""
    ids = set(r["areas"])
    pts = [q for a in geo["areas"] if a["id"] in ids for q in a["points"]]
    if not pts:
        return r["x"], r["y"]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return round((min(xs) + max(xs)) / 2, 1), round((min(ys) + max(ys)) / 2, 1)


def map_svg(geo, marks=()):
    """The map at load (sandbox, Easy) in sim coordinates: areas by type, paths, blockers, obstacles."""
    owned = {}  # area id -> obstacle index: those areas go away with the obstacle
    for i, r in enumerate(geo["removables"]):
        for a in r["areas"]:
            owned[a] = i
    groups = {i: [] for i in range(len(geo["removables"]))}
    base = []
    # the first area is the full-screen base (land, water or unplaceable); ground in game order on top of it (islands,
    # lakes), then track, then no-placing zones, so none of them hides under a bigger ground polygon
    rank = {"track": 1, "unplaceable": 2, "removable": 2}
    for a in geo["areas"][:1] + sorted(geo["areas"][1:], key=lambda a: rank.get(a["type"], 0)):
        if len(a["points"]) < 3:
            continue
        kind = {"shallowWater": "water", "waterMermonkey": "water", "ice": "land", "removable": "unplaceable"}.get(a["type"], a["type"])
        cls = f"a {kind}" + (" blk" if a["blocker"] else "") + (" dis" if a["disabled"] else "")
        tip = AREA_NAMES.get(a["type"], a["type"]) + (", блокирует обзор" if a["blocker"] else "") + (", выключена" if a["disabled"] else "")
        el = f"<path class='{cls}' data-a='{a['id']}' d='{path_d(a['points'], a['holes'])}'><title>{esc(tip)}</title></path>"
        (groups[owned[a["id"]]] if a["id"] in owned else base).append(el)
    los = []
    for x, y, r in geo["blockers"]:
        el = f"<circle class='los' cx='{x:g}' cy='{y:g}' r='{r:g}'/>"
        mine = [i for i, rm in enumerate(geo["removables"])
                if any(inside(x, y, a["points"]) for a in geo["areas"] if a["id"] in rm["areas"])]
        (groups[mine[0]] if mine else los).append(el)
    paths = []
    for n, p in enumerate(unique_paths(geo), 1):
        if len(p["points"]) < 2:
            continue
        (x, y) = p["points"][0]
        tip = (" / ".join(i for i in p["ids"] if i) or f"путь {n}") + (", скрыт" if p["hidden"] else "") \
            + ("" if p["active"] else ", выключен в начале")
        cls = "path" + (" hid" if p["hidden"] else "") + ("" if p["active"] else " idle")
        paths.append(f"<g class='{cls}' data-p='{esc(' '.join(i for i in p['ids'] if i))}'><title>{esc(tip)}</title>"
                     f"<polyline points='{pts(p['points'])}'/><circle cx='{x:g}' cy='{y:g}' r='3'/></g>")
    rms = "".join(
        f"<g class='rm' data-rm='{i}'{sold_effects(geo, r)} tabindex='0' role='button'><title>{esc(f'препятствие {i + 1}: {fmt(r['cost'])} $, нажмите, чтобы убрать')}</title>"
        f"{''.join(groups[i])}<circle class='rm-dot' cx='{rm_center(geo, r)[0]:g}' cy='{rm_center(geo, r)[1]:g}' r='3.5'/></g>"
        for i, r in enumerate(geo["removables"]) if r["cost"])
    toggles = "".join(f"<label><input type='checkbox' data-layer='{k}' checked> {esc(n)}</label>" for k, n in LAYERS)
    return ("<div class='mapview'><div class='map-tools'>" + toggles
            + "<button type='button' class='map-full'>На весь экран</button>"
            + ("<button type='button' class='rm-all'>Убрать все препятствия</button>" if rms else "")
            + "<span class='map-xy' aria-live='off'></span></div>"
            "<svg class='mapsvg' viewBox='-150 -116 300 232' role='img' aria-label='Схема карты'>"
            # clipped to the game screen: wider full-screen boxes would show the off-screen parts
            "<clipPath id='screen'><rect x='-150' y='-116' width='300' height='232'/></clipPath><g clip-path='url(#screen)'>"
            f"<g class='L-base'>{''.join(base)}</g><g class='L-los'>{''.join(los)}</g><g class='L-rm'>{rms}</g>"
            f"<g class='L-path'>{''.join(paths)}</g>"
            + "".join(f"<g class='ev' data-ev='{i}'>{m}</g>" for i, m in enumerate(marks) if m)
            + "</g></svg></div>")


def kind(model):
    return model.get("$type", "").split(",")[0].split(".")[-1].removesuffix("Model")


def obstacle_no(geo):
    """Obstacle object name -> its number on the page (obstacles with a price, in dump order)."""
    return {r.get("obj"): i for i, r in enumerate((r for r in geo["removables"] if r["cost"]), 1)}


def trigger_text(tr, obstacles):
    k = kind(tr)
    if k == "AfterRoundTrigger":
        return f"каждые {tr['everyNthRound']} раундов" if tr.get("everyNthRound") else f"после окончания раунда {tr['round']}"
    if k == "StartRoundTrigger" and tr.get("round"):
        return f"в начале раунда {tr['round']}"
    if k == "RemoveableSoldTrigger":
        n = obstacles.get(tr.get("removableName"))
        return f"убрано препятствие {n}" if n else "убрано препятствие"
    if k == "PreBloonSpawnTrigger":
        return "появляется MOAB" if tr.get("bloonTag") == "Moabs" else f"появляется шар с тегом {tr.get('bloonTag')}"
    if k == "TowerPlacedTrigger":
        return f"поставлен {t(tr.get('towerId'), fallback=tr.get('towerId'))} {'-'.join(map(str, tr.get('tiers') or []))}".strip()
    if k == "LivesLowerThanTrigger":
        return f"жизней меньше {fmt(round(tr['percent'] * 100))}%" if tr.get("usePercent") else f"жизней меньше {tr.get('lives')}"
    if k == "SimTimeElapsedTrigger":
        return f"каждые {fmt(tr.get('time'))} сек."
    return TRIGGERS.get(k, k)


def action_text(a, obstacles):
    k = kind(a)
    if k == "PathActiveAction":
        return f"{'включает' if a.get('setActiveToo') else 'выключает'} путь {a.get('pathName')}"
    if k == "ToggleSplitterAction":
        on, off = a.get("pathsToActivate") or [], a.get("pathsToDeactivate") or []
        parts = ([f"включает пути {', '.join(on)}"] if on else []) + ([f"выключает пути {', '.join(off)}"] if off else [])
        return "; ".join(parts) or "переключает развилку"
    return ACTIONS.get(k, k)


def scene_points(geo, name):
    """Click targets of a scene object as map circles (x, y, r): map y is -world z. Entries are collider bounds
    [x, y, z, size x, size z] (older dumps: positions [x, y, z]); a point at 0, 0 is an empty container, skipped."""
    out = []
    for e in (geo.get("interactables") or {}).get(name) or []:
        x, z = e[0], e[2]
        r = max(e[3:5] or [0]) / 2 or 6
        if (x, z) != (0, 0) and (x, -z, r) not in out:
            out.append((x, -z, min(max(r, 4), 40)))
    return out


def event_marks(e, geo):
    """SVG shapes for one event: where it is triggered (yellow), what appears (green), goes (red) or moves (blue)."""
    areas = {a.get("name"): a for a in geo["areas"] if a.get("name")}
    rms = {r.get(k): r for r in geo["removables"] for k in ("model", "obj") if r.get(k)}
    paths = {p.get("id"): p for p in geo["paths"] if p.get("id")}
    out = []

    def area(name, cls):
        a = areas.get(name)
        if a and len(a["points"]) > 2:
            out.append(f"<path class='{cls}' d='{path_d(a['points'], a['holes'])}'/>")

    def removable(name, cls):
        r = rms.get(name)
        if r:
            for aid in r["areas"]:
                area(next((n for n, a in areas.items() if a["id"] == aid), None), cls)
            x, y = rm_center(geo, r)
            if (x, y) != (0, 0):
                out.append(f"<circle class='{cls} pin' cx='{x:g}' cy='{y:g}' r='6'/>")

    def path(pid, cls):
        q = paths.get(pid)
        if q and len(q["points"]) > 1:
            out.append(f"<polyline class='{cls}' points='{pts(q['points'])}'/>")

    def pin(x, y, r=6):
        out.append(f"<circle class='hl-at pin' cx='{x:g}' cy='{y:g}' r='{r:g}'/>")

    for tr in e.get("triggers") or []:
        k = kind(tr)
        if k == "RemoveableSoldTrigger":
            removable(tr.get("removableName"), "hl-at")
        if tr.get("interactableName"):
            for x, y, r in scene_points(geo, tr["interactableName"]):
                pin(x, y, r)
        if tr.get("interactableClickSequenceName"):
            # targets in click order (a target clicked twice shows both numbers)
            spots = {}
            for n, box in enumerate((geo.get("interactables") or {}).get(tr["interactableClickSequenceName"]) or [], 1):
                if (box[0], box[2]) == (0, 0):
                    continue
                x, y = box[0], -box[2]
                # the same target clicked again reads a hair off (collider moved): within 4 units it is one spot
                key = next((k for k in spots if abs(k[0] - x) < 4 and abs(k[1] - y) < 4), (x, y))
                spots.setdefault(key, [min(max(max(box[3:5] or [0]) / 2 or 6, 4), 40), []])[1].append(n)
            for (x, y), (r, ns) in spots.items():
                pin(x, y, r)
                out.append(f"<text class='pin-n' x='{x:g}' y='{y:g}'>{','.join(map(str, ns))}</text>")
        if k == "OnProjectileHitTrigger":
            pin(tr.get("collisionMarkerX", 0), tr.get("collisionMarkerY", 0), tr.get("collisionRadius") or 6)
        if k == "BloonsPoppedTrigger" and tr.get("position"):
            pin(tr["position"]["x"], tr["position"]["y"])
        if k == "TowerInAreaTrigger" and (tr.get("areaModel") or {}).get("polygon"):
            ptl = [(q["x"], q["y"]) for q in tr["areaModel"]["polygon"].get("points") or []]
            if len(ptl) > 2:
                out.append(f"<path class='hl-at' d='{path_d(ptl)}'/>")
    for a in e.get("actions") or []:
        k = kind(a)
        names = a.get("areaNames") or ([a["areaName"]] if a.get("areaName") else [])
        if k in ("CreateAreaAction", "CreateAreasAction"):
            for n in names: area(n, "hl-on")
        elif k in ("DestroyAreaAction", "DestroyAreasAction"):
            for n in names: area(n, "hl-off")
        elif k in ("MovingPlatformAction", "CycleAreasAction", "RotateAreaAction"):
            for n in names: area(n, "hl-move")
        elif k == "RemovableActiveAction":
            removable(a.get("removeableName"), "hl-on" if a.get("setActiveToo") else "hl-off")
        elif k == "SellRemoveableAction":
            removable(a.get("removeableName"), "hl-off")
        elif k == "PathActiveAction":
            path(a.get("pathName"), "hl-on" if a.get("setActiveToo") else "hl-off")
        elif k == "ToggleSplitterAction":
            for pid in a.get("pathsToActivate") or []: path(pid, "hl-on")
            for pid in a.get("pathsToDeactivate") or []: path(pid, "hl-off")
        elif k == "EnablePathTargetZoneAction" and a.get("position"):
            out.append(f"<circle class='hl-on' cx='{a['position']['x']:g}' cy='{a['position']['y']:g}' r='{a.get('range') or 6:g}'/>")
    return "".join(out)


def event_rows(geo, summary):
    """(condition, actions, one time) per map event; from the full dump, else from the type names."""
    rows = {}
    if geo and geo.get("events") is not None:
        obstacles = obstacle_no(geo)
        out = []
        for e in geo["events"]:
            acts = [action_text(a, obstacles) for a in e.get("actions") or []]
            if not acts:
                continue  # "obstacle removed > nothing": every obstacle has one
            joiner = " и " if e.get("allTriggersRequired") else " или "
            cond = joiner.join(trigger_text(tr, obstacles) for tr in e.get("triggers") or []) or "всегда"
            out.append((cond, ", ".join(acts), "да" if e.get("oneTimeEvent") else "нет", event_marks(e, geo), effects(geo, [e])))
        return out
    else:
        for e in (summary or {}).get("events", []):
            trig, _, acts = e.partition(" > ")
            if acts:
                key = (" + ".join(TRIGGERS.get(x, x) for x in trig.split("+") if x),
                       ", ".join(ACTIONS.get(x, x) for x in acts.split("+") if x), "–")
                rows[key] = rows.get(key, 0) + 1
    return [(c, a + (f" ×{n}" if n > 1 else ""), o, "", "") for (c, a, o), n in sorted(rows.items())]


def path_roles(geo):
    """Path id -> who enters it, from the spawner's splitters (forward; "also in Reverse" when the reverse one has it)."""
    tags = {"Moabs": "только MOAB", "Boss": "только боссы", "Bad": "только BAD"}
    roles, reverse = {}, set()
    sp = geo.get("spawner") or {}
    for side in ("forwardSplitter", "reverseSplitter"):
        s = sp.get(side)
        if not s:
            continue
        k, paths = kind(s), s.get("paths") or []
        pairs = {pp.get("path"): pp.get("tag") for pp in s.get("pathTagPairs") or []}
        found = {}
        for i, pid in enumerate(paths + [x for x in pairs if x not in paths]):
            if k == "MoabOnlySplitter":
                who = "только MOAB" if (s.get("moabOnlyPath") or [])[i:i + 1] == [True] else "шары кроме MOAB"
            elif k == "BloonTagOnlySplitter" and ((s.get("tagOnlyPath") or [])[i:i + 1] or [""])[0]:
                who = tags.get(s["tagOnlyPath"][i], f"только тег {s['tagOnlyPath'][i]}")
            elif pairs.get(pid):
                who = tags.get(pairs[pid], f"только тег {pairs[pid]}")
            elif k in ("AlternateRoundSplitter", "AlternateRoundMultiPathSplitter"):
                who = "вход, чередуется по раундам"
            elif k == "ToggleSplitter":
                who = "вход, переключаемая развилка"
            else:
                who = "вход"
            found[pid] = who
        if s.get("overriddenBossPath"):
            found[s["overriddenBossPath"]] = "только боссы"
        if side == "forwardSplitter":
            roles.update(found)
        else:
            reverse.update(found)
            for pid, who in found.items():
                roles.setdefault(pid, "вход в режиме Reverse" if who == "вход" else f"{who} в режиме Reverse")
    return {pid: [who + (", также в режиме Reverse" if pid in reverse and "Reverse" not in who else "")]
            for pid, who in roles.items()}


def path_opens(geo):
    """Path id -> conditions that turn it on or off."""
    out = {}
    obstacles = obstacle_no(geo)
    for e in geo.get("events") or []:
        joiner = " и " if e.get("allTriggersRequired") else " или "
        cond = joiner.join(trigger_text(tr, obstacles) for tr in e.get("triggers") or []) or "всегда"
        for a in e.get("actions") or []:
            k = kind(a)
            if k == "PathActiveAction":
                out.setdefault(a.get("pathName"), []).append(("включается: " if a.get("setActiveToo") else "выключается: ") + cond)
            elif k == "ToggleSplitterAction":
                for pid in a.get("pathsToActivate") or []:
                    out.setdefault(pid, []).append("включается: " + cond)
                for pid in a.get("pathsToDeactivate") or []:
                    out.setdefault(pid, []).append("выключается: " + cond)
    return out


def map_page(m, file, name, level, summary, geo):
    rows = []
    if geo:
        roles, opens = path_roles(geo), path_opens(geo)
        for n, p in enumerate(unique_paths(geo), 1):
            ids = [i for i in p["ids"] if i] or [str(n)]
            state = "скрыт, " if p["hidden"] else ""
            state += "активен" if p["active"] else "выключен"
            who = sorted({w for i in ids for w in roles.get(i, [])})
            when = sorted({w for i in ids for w in opens.get(i, [])})
            rows.append(["<code>" + "<br>".join(esc(i) for i in ids) + "</code>", round(length(p["points"])), esc(state),
                         esc("; ".join(who)) or "–", esc("; ".join(when)) or "–"])
    elif summary:
        rows = [[n, round(x), "активен", "–", "–"] for n, x in enumerate(summary["paths"], 1)]
    events = event_rows(geo, summary)
    obstacles = (geo or {}).get("removables") or (summary or {}).get("removables") or []
    obstacles = [r for r in obstacles if r.get("cost")]  # cost 0: click-to-confirm, not an obstacle
    notes = [BEHAVIOURS.get(b, b) for b in (summary or {}).get("behaviours", [])]
    if summary and summary.get("speed", 1) != 1:
        notes.append(f"скорость шаров ×{fmt(summary['speed'])}")
    if summary and summary.get("regenRemovables"):
        notes.append("препятствия отрастают")
    facts = [("сложность", level), ("вода", "есть" if m["hasWater"] else "нет"),
             ("деление в кооперативе", COOP_SPLIT.get(m["coopMapDivisionType"], str(m["coopMapDivisionType"]))),
             ("путей", len(rows) if rows else None), ("препятствий", len(obstacles) if summary or geo else None)]
    body = card("about", name, "<div class='hero-row'>" + icon("maps", m["id"], 120, "ic portrait") + "<div>" + stats(facts)
                + (f"<p class='note'>{esc(', '.join(notes))}</p>" if notes else "") + "</div></div>", en_id=m["id"], section="Карты")
    toc = [("about", name)]
    if geo:
        body += card("view", "Схема", map_svg(geo, [ev[3] for ev in events])
                     + "<p class='note'>Карта в момент загрузки (песочница, лёгкая сложность), по координатам игры. "
                     "Наведите на область, чтобы увидеть её тип; нажмите на препятствие, чтобы убрать его вместе с его "
                     "областями. Пунктир: путь выключен в начале и включается механикой карты. Фиолетовая точечная линия: скрытый путь, в игре он не отмечен на треке. Движущиеся части "
                     "показаны там, где они были при загрузке.</p>", section=name)
        toc.append(("view", "Схема"))
    if rows:
        body += card("paths", "Пути", table(["Путь", "Длина", "В начале", "Кто заходит", "Когда меняется"], rows)
                     + "<p class='note'>Путь назван так, как в файлах игры. Длина в единицах игры. «Кто заходит»: "
                     "какие шары точка появления отправляет на путь; остальные пути продолжают входные. Одинаковые "
                     "пути с нескольких точек появления показаны одной строкой.</p>", section=name)
        toc.append(("paths", "Пути"))
    if obstacles:
        body += card("obstacles", "Препятствия", table(["Препятствие", "Цена"], [[i, f"{fmt(r['cost'])} $"] for i, r in enumerate(obstacles, 1)])
                     + f"<p class='note'>Всего: {fmt(sum(r['cost'] for r in obstacles))} $, цены на лёгкой сложности.</p>", section=name)
        toc.append(("obstacles", "Препятствия"))
    if events:
        trs = "".join(
            f"<tr{f' class=ev-row data-ev={i}{fx} tabindex=0' if mk else ''}><td>{esc(c)}</td><td>{esc(a)}</td><td>{esc(o)}</td>"
            f"<td>{'<span class=ev-show>на схеме</span>' if mk else '–'}</td></tr>" for i, (c, a, o, mk, fx) in enumerate(events))
        body += card("events", "Механики",
                     "<div class='wrap'><table class='evs'><thead><tr><th>Когда</th><th>Что происходит</th><th>Один раз</th>"
                     f"<th>Где</th></tr></thead><tbody>{trs}</tbody></table></div>"
                     + "<p class='note'>События карты из её модели: условие и действия. Наведите на строку или нажмите "
                     "на неё, чтобы увидеть на схеме: жёлтым где срабатывает (клик, препятствие), зелёным что "
                     "появляется или включается, красным что исчезает или выключается, синим что двигается. Нажатие "
                     "применяет событие к схеме: показан результат; повторное нажатие возвращает как было.</p>", section=name)
        toc.append(("events", "Механики"))
    if not summary and not geo:
        body += "<p class='note'>Для этой карты нет дампа путей и препятствий: дампер пропускает карты только для браузерной версии.</p>"
    core.current_file = file
    page(file, name, f"{esc(level)}. Схема, пути, препятствия и механики карты.", body, toc)


def mechanics(d):
    """Table cells for path length, obstacles and map mechanics from one maps.json entry ({} when not dumped)."""
    if not d:
        return "–", "–", "–"
    paths = sorted(d.get("paths", []))
    length_cell = "–"
    if paths:
        lo, hi = round(paths[0]), round(paths[-1])
        length_cell = fmt(lo) if lo == hi else f"{fmt(lo)}–{fmt(hi)}"
        if len(paths) > 1:
            length_cell += f" ({len(paths)} пут.)"
    costs = [r["cost"] for r in d.get("removables", []) if r.get("cost")]  # cost 0: click-to-confirm, not an obstacle
    obstacles = f"{fmt(sum(costs))} $ ({len(costs)} шт.)" if costs else "нет"
    notes = [BEHAVIOURS.get(b, b) for b in d.get("behaviours", [])]
    if d.get("speed", 1) != 1:
        notes.append(f"шарики ×{fmt(d['speed'])}")
    if d.get("regenRemovables"):
        notes.append("препятствия отрастают")
    if any("Interactable" in e for e in d.get("events", [])):
        notes.append("интерактивные объекты")
    return length_cell, obstacles, esc(", ".join(notes)) or "–"


def build_maps():
    dump, geo = optional("maps.json"), optional("maps_geo.json") or {}
    # one folder per difficulty, in the game's difficulty order
    folders = sorted((p for p in (DATA / "Maps").iterdir() if p.is_dir()), key=lambda p: load(next(p.glob("*.json")))["difficulty"])
    label = {p.name: t(f"MD {p.name}", fallback=p.name)[:1].upper() + t(f"MD {p.name}", fallback=p.name)[1:] for p in folders}
    rows, pages = [], []
    for folder in folders:
        level = label[folder.name]
        maps = [load(f) for f in sorted(folder.glob("*.json"))]
        for m in sorted((m for m in maps if t(m["id"], fallback="")), key=lambda m: t(m["id"])):  # no name: editor stub
            name, file = t(m["id"]), f"map-{slug(m['id'])}.html"
            pages.append((m, file, name, level))
            tags = [folder.name.lower(), "water" if m["hasWater"] else "dry"] + (["browser"] if m["isBrowserOnly"] else [])
            badge = " <span class='badge'><b>только браузерная версия</b></span>" if m["isBrowserOnly"] else ""
            cells = (f"<a class='ach' href='{file}'>{icon('maps', m['id'], 64, 'ic mapic')}<span><b id='m-{esc(m['id'])}'>{esc(name)}</b>{badge}</span></a>",
                     esc(level), "есть" if m["hasWater"] else "нет",
                     esc(COOP_SPLIT.get(m["coopMapDivisionType"], str(m["coopMapDivisionType"]))))
            if dump is not None:
                cells += mechanics(dump.get(m["id"], {}))
            rows.append(f"<tr data-tags='{' '.join(tags)}'>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    files = [p[1] for p in pages]
    assert len(files) == len(set(files)), "two map ids give the same page name"
    for m, file, name, level in pages:
        map_page(m, file, name, level, (dump or {}).get(m["id"]), geo.get(m["id"]))
    core.current_file = "maps.html"
    filters = [("", "Все")] + [(p.name.lower(), label[p.name]) for p in folders] + [("water", "С водой"), ("dry", "Без воды")]
    bar = ("<div class='tagbar' data-target='#maps-t'>" + "".join(
        f"<button type='button' data-tag='{k}'{' class=on' if not k else ''}>{esc(n)}</button>" for k, n in filters) + "</div>")
    heads = ("Карта", "Сложность", "Вода", "Деление в кооперативе")
    if dump is not None:
        heads += ("Длина пути", "Препятствия", "Особенности")
    head = "".join(f"<th>{h}</th>" for h in heads)
    note = ("<p class='note'>Длина пути в единицах игры, сумма отрезков каждого активного пути; у карт с несколькими "
            "путями показан самый короткий и самый длинный. Препятствия: сколько стоит убрать все, по модели карты "
            "в песочнице на лёгкой сложности.</p>") if dump is not None else ""
    body = (bar + "<input class='filter' type='search' placeholder='Фильтр: название карты' aria-label='Фильтр карт' "
            "data-filter='#maps-t tbody tr'>"
            f"<div class='wrap'><table id='maps-t'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>" + note)
    lead = f"Все {len(rows)} карт: сложность, есть ли вода для водных башен, как поле делится в кооперативе."
    if dump is not None:
        lead += " " + "Длина пути, цена препятствий и механики карты."
    page("maps.html", "Карты", lead, card("all", "Карты", body, section="Карты"), [("all", "Карты")])
