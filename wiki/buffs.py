"""Buff page: what stacks and who grants it."""
import functools
import re
from wiki.core import (
    DATA, INDEX, Raw, SHOP_ORDER, TEXT, card, esc, fmt, icon, json_files, load, page, t, table,
)
from wiki.mods import param


@functools.cache
def buff_towers():
    """buffIconName or buffLocsName -> towers whose models carry it (the source tower's CanBuffIndicatorModel)."""
    out = {}
    for f in (DATA / "Towers").glob("*/*.json"):
        for name in set(re.findall(r'"buff(?:Icon|Locs)Name": "([^"]+)"', f.read_text(encoding="utf-8"))):
            out.setdefault(name, set()).add(f.parent.name)
    return out


def tower_badge(tid):
    return (f"<a class='badge' href='tower-{tid}.html'><span>башня</span>"
            f"<b>{icon('towers', tid, 18)}{esc(TEXT.get(tid, tid))}</b></a>")


@functools.cache
def buff_icon_owners():
    """Buff icon name -> heroes and powers whose models carry it: {(kind, id)}."""
    out = {}
    files = [("hero", f.parent.name, f) for f in (DATA / "Heroes").glob("*/*.json")] + \
            [("power", f.stem, f) for f in (DATA / "Powers").glob("*.json")]
    for kind, oid, f in files:
        for name in set(re.findall(r'"(?:buff|)(?:Icon|Locs|icon)Name": "([^"]+)"', f.read_text(encoding="utf-8"))):
            out.setdefault(name, set()).add((kind, oid))
    return out


def source_badge(kind, oid):
    """Link badge to a buff source: tower page, hero card or power card."""
    if kind == "tower":
        return tower_badge(oid)
    href, pic = (f"hero-{oid}.html", icon("heroes", oid, 18)) if kind == "hero" else \
                (f"powers.html#{oid}", icon("ui", f"power-{oid}", 18))
    return (f"<a class='badge' href='{href}'><span>{'герой' if kind == 'hero' else 'сила'}</span>"
            f"<b>{pic}{esc(t(oid, fallback=oid))}</b></a>")


def tower_of(icon_name, buff_name=""):
    """Source of a buff: towers, then heroes and powers whose data carry its icon; else a guess from the icon name
    (BuffIconAlchemist3xx); else towers carrying its buff name (last: heroes reuse tower buff names, BiggerRadiusBuff)."""
    found = buff_towers().get(icon_name)
    if found:
        return "".join(tower_badge(tid) for tid in sorted(found, key=lambda x: SHOP_ORDER.index(x) if x in SHOP_ORDER else 99))
    owners = buff_icon_owners().get(icon_name)
    if owners:
        return "".join(source_badge(k, o) for k, o in sorted(owners))
    rest = icon_name.removeprefix("BuffIcon")
    for end in range(len(rest), 3, -1):
        word = rest[:end]
        if word[0].isupper() and (end == len(rest) or not rest[end].islower()) and isinstance(TEXT.get(word), str):
            word_tower = {"Gyrfalcon": "BeastHandler", "Microraptor": "BeastHandler", "Piranha": "BeastHandler",
                          "Sheriff": "Desperado"}.get(word, word)  # pets and the old Desperado id
            if (DATA / "Towers" / word_tower).is_dir():
                return tower_badge(word_tower)
            if (DATA / "Powers" / f"{word}.json").exists():
                return source_badge("power", word)
            if (DATA / "Heroes" / word).is_dir():
                return source_badge("hero", word)
            return f"<span class='badge'><span>источник</span><b>{esc(TEXT[word])}</b></span>"
    return "".join(tower_badge(tid) for tid in sorted(buff_towers().get(buff_name, ())))


def flag(k, v, good=True):
    """Yes/no parameter badge; green when the value is the favourable one."""
    cls = "yes" if bool(v) == good else "no"
    return f"<span class='badge {cls}'><span>{esc(k)}</span><b>{fmt(v)}</b></span>"


def build_buffs():
    rows = []
    for f in json_files("Buffs"):
        d = load(f)
        name = d.get("iconName", "")
        pic = icon("buffs", name, 32, "ic buff-ic") or "<span class='buff-ic'></span>"
        buff = (f"<span class='mod-name' id='buff-{esc(name)}'>{pic}"
                f"<span><span class='id'>{esc(d.get('buffName'))}</span><br><small class='note'>{esc(name)}</small></span></span>")
        stack = "<div class='stackgrid'>" + "".join([flag("stackable", d.get("stackable")), param("maxStackSize", "∞" if (d.get("maxStackSize") or 0) >= 2**31 - 1 else d.get("maxStackSize")),
                          flag("globalRange", d.get("globalRange"))]) + "</div>"
        src = tower_of(name, d.get("buffName", ""))
        rows.append((Raw(src) or "–", Raw(buff), Raw(stack)))
        who = ", ".join(re.sub("<[^>]+>", "", b) for b in re.findall("<b>(.*?)</b>", src))
        entry = [d.get("buffName", ""), "Баффы" + (" · " + who if who else ""), f"buffs.html#buff-{name}", name]
        if not any(e[:2] == entry[:2] for e in INDEX):  # one buff granted by several tiers: first tier only
            INDEX.append(entry)
    rows.sort(key=lambda r: (re.sub("<[^>]+>", "", r[0]), r[1]))  # by visible source name
    body = (card("table", "Все индикаторы баффов",
                 "<p class='note'>stackable показывает, складывается ли бафф с тем же именем от второго источника. "
                 "maxStackSize 0 = лимит не задан. globalRange = действует на всю карту. Источник: башня, в модели которой записана эта иконка. Для остальных (герои и прочее) угадан по имени иконки.</p>"
                 "<input class='filter' type='search' placeholder='Фильтр: башня или бафф' aria-label='Фильтр баффов' "
                 "data-filter='#buffs tbody tr'>"
                 + table(["Источник", "Бафф", "Стакинг"], rows).replace("<table>", "<table id='buffs'>", 1), section="Баффы"))
    page("buffs.html", "Баффы и стакинг",
         "Баффы, которые видно иконкой над башней: откуда бафф, стакается ли и до скольки раз.", body)
