"""Buff page: what stacks and who grants it."""
import functools
import json
import re
from wiki import core
from wiki.core import (
    DATA, INDEX, Raw, SHOP_ORDER, TEXT, card, esc, flatten, fmt, icon, json_files, label, load, page,
    short_type, t, table,
)
from wiki.mods import param


@functools.cache
def buff_towers():
    """buffIconName or buffLocsName -> towers whose models carry it (the source tower's CanBuffIndicatorModel)."""
    out = {}
    for f in sorted((DATA / "Towers").glob("*/*.json")):
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
    files = [("hero", f.parent.name, f) for f in sorted((DATA / "Heroes").glob("*/*.json"))] + \
            [("power", f.stem, f) for f in sorted((DATA / "Powers").glob("*.json"))]
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


# support model type -> what it changes (game code names, not in the export); others show their split type name
EFFECT_RU = {
    "RangeSupportModel": "Дальность", "RateSupportModel": "Перезарядка атаки", "PierceSupportModel": "Пробивание",
    "DamageSupportModel": "Урон", "VisibilitySupportModel": "Видит камуфляж", "DiscountZoneModel": "Скидка на башни и улучшения",
    "ProjectileSpeedSupportModel": "Скорость снарядов", "ProjectileRadiusSupportModel": "Размер снарядов",
    "DamageTypeSupportModel": "Тип урона", "FreezeDurationSupportModel": "Длительность заморозки",
    "AbilityCooldownScaleSupportModel": "Перезарядка способностей", "MonkeyCityIncomeSupportModel": "Доход",
    "BananaCashIncreaseSupportModel": "Доход от бананов", "PiercePercentageSupportModel": "Пробивание, %",
    "CashbackZoneModel": "Возврат денег при покупке", "FreeUpgradeSupportModel": "Бесплатные улучшения",
    "DamageModifierSupportModel": "Урон по типу шаров", "SupportStackingRangeModel": "Дальность, складывается",
    "RateSupportExplosiveModel": "Перезарядка взрывных башен", "RateSupportBombExpertModel": "Перезарядка бомб",
    "AddBehaviorToTowerSupportModel": "Добавляет поведение башне", "AddBehaviorToTowerTypeSupportModel": "Добавляет поведение башням",
    "SupportRemoveFilterOutTagModel": "Бьёт шары с тегом", "PoplustSupportModel": "Poplust: урон и пробивание",
    "PyrotechnicsSupportModel": "Пиротехника", "SupportShinobiTacticsModel": "Shinobi: перезарядка и пробивание",
    "ActivateRateSupportZoneModel": "Перезарядка атаки (способность)", "ActivatePierceSupportZoneModel": "Пробивание (способность)",
    "ActivateTowerDamageSupportZoneModel": "Урон (способность)", "ActivateRangeSupportZoneModel": "Дальность (способность)",
    "ActivateVisibilitySupportZoneModel": "Видит камуфляж (способность)", "ActivateDamageModifierSupportZoneModel": "Урон по типу шаров (способность)",
    "ActivateProjectileSpeedSupportZoneModel": "Скорость снарядов (способность)", "ActivateIgnoreStunSupportZoneModel": "Не оглушается (способность)",
    "ActivateTempTargetPrioSupportZoneModel": "Приоритет целей (способность)", "ActivateRicochetSupportZoneModel": "Рикошет (способность)",
    "ActivateDamageBypassSupportZoneModel": "Урон сквозь защиту (способность)", "ActivateSpreadSupportZoneModel": "Разброс (способность)",
    "AddAcidicMixtureToProjectileModel": "Кислота на снарядах", "AddBerserkerBrewToProjectileModel": "Berserker Brew на снарядах",
}
# fields that steer how the game tracks or shows a buff, not what it does; stacking is its own column
NOISE = {"mutatorId", "uniqueMutatorId", "isUnique", "buffLocsName", "buffIconName", "showBuffIcon", "maxStackSize",
         "onlyShowBuffIfMutated", "stackName", "priority", "lifespanFrames", "excludeAddToSubtower", "isCustomRadius",
         "useTowerRange", "displayModel", "buffDisplayModel", "upgradeId", "maxStacks", "stackLimit", "mutatorSaveId"}


def file_rank(f):
    """Where a model file sits in its tower's or hero's progression: total tier (Alchemist-300 = 3) or hero level."""
    if f.stem.endswith("-Paragon"):
        return 99  # after every tier: a paragon reuses its tower's buffs
    m = re.search(r"-(\d)(\d)(\d)$", f.stem) or re.search(r" (\d+)$", f.stem)
    return sum(map(int, m.groups())) if m else 0


@functools.cache
def buff_effects():
    """("icon" or "locs", buff icon or buff name) -> (where it first comes from, [support models]): towers, then heroes,
    powers and Geraldo items (a potion reuses the village's camo icon), lowest tier or level first. The marker on the
    receiving tower (CanBuffIndicatorModel) is not an effect."""
    out = {}
    kinds = ["Towers", "Heroes", "Powers", "GeraldoItems"]
    files = sorted((f for k in kinds for f in (DATA / k).rglob("*.json")),
                   key=lambda f: (kinds.index(f.relative_to(DATA).parts[0]), file_rank(f)))
    for f in files:
        text = f.read_text(encoding="utf-8")
        names = {(k.lower(), n) for k, n in re.findall(r'"buff(Icon|Locs)Name": "([^"]+)"', text)} - set(out)
        if not names:
            continue
        found = {}

        def walk(o):
            if isinstance(o, dict):
                if short_type(o) != "CanBuffIndicatorModel":
                    for n in {("icon", o.get("buffIconName")), ("locs", o.get("buffLocsName"))} & names:
                        found.setdefault(n, []).append(o)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        d = load(f)
        walk(d)
        hero = f.parent.parent.name == "Heroes"
        source = (f"уровень {file_rank(f) or 1}" if hero else (d.get("appliedUpgrades") or [None])[-1]
                  or (f.stem if f.parent.name in ("Powers", "GeraldoItems") else None))  # a power or Geraldo item: its own name
        for n, models in found.items():
            uniq = {json.dumps(m, sort_keys=True): m for m in models}  # one per tower set filter is repeated often
            out[n] = (source, list(uniq.values()))
    return out


def who(filters):
    """Readable target filter of a support model: tower classes, towers, paragons."""
    parts = []
    for fl in filters or []:
        k = short_type(fl)
        if k == "FilterInSetModel":
            names = [SET_NAMES.get(s, str(s)) for s in fl.get("towerSets") or [fl.get("towerSet")]]
            parts += ["герои" if n == "Hero" else t(n, fallback=n) for n in names]
        elif k == "FilterInBaseTowerIdModel":
            parts += [t(b, fallback=b) for b in fl.get("baseIds") or []]
        elif k == "FilterParagonModel":
            parts.append("парагоны" if fl.get("inclusive") else "кроме парагонов")
        else:
            parts.append(label(k))
    return ", ".join(p for p in parts if p)


SET_NAMES = {v: k for k, v in core.GAME["towerSets"].items()}  # 16 Hero, 32 Paragon too, not only monkey classes


def effect_name(m):
    k = short_type(m)
    return EFFECT_RU.get(k) if core.LANG == "ru" and k in EFFECT_RU else label(k)


def effect_line(m):
    """One support model: what it changes, its numbers and whom it targets."""
    kept = {p: v for p, v in flatten(m).items()
            if not p.startswith("Filter") and p.split(".")[-1] not in NOISE and v not in (False, 0, "")}
    badges = " ".join(param(p, "∞" if isinstance(v, float) and v >= 9e6 else v) for p, v in kept.items())
    target = who(m.get("filters"))
    if target:
        badges += f" <span class='badge'><span>кому</span><b>{esc(target)}</b></span>"
    return f"<div><b>{esc(effect_name(m))}</b> {badges}</div>"


def effect_html(icon_name, buff_name=""):
    src = buff_effects().get(("icon", icon_name)) or buff_effects().get(("locs", buff_name))
    if not src:
        return "–"
    upgrade, models = src
    lines = []
    for m in models:
        line = effect_line(m)
        if line not in lines:  # copies that differ only in tracking fields (mutator ids) read the same
            lines.append(line)
    desc = t(f"{upgrade} Description", fallback="") if upgrade and not upgrade.startswith("уровень") else ""
    title = t(upgrade, fallback=upgrade) if upgrade else ""
    if desc.startswith(title + ":"):
        desc = desc[len(title) + 1:].strip()  # some descriptions repeat the upgrade name
    head = f"<small class='note'>{esc(title)}" + (f": {esc(desc)}" if desc else "") + "</small>" if upgrade else ""
    return "<div class='mod-params'>" + "".join(lines) + head + "</div>"


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
        rows.append((Raw(src) or "–", Raw(buff), Raw(effect_html(name, d.get("buffName", ""))), Raw(stack)))
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
                 + table(["Источник", "Бафф", "Что делает", "Стакинг"], rows).replace("<table>", "<table id='buffs'>", 1), section="Баффы"))
    page("buffs.html", "Баффы и стакинг",
         "Баффы, которые видно иконкой над башней: откуда бафф, что он делает, стакается ли и до скольки раз.", body)
