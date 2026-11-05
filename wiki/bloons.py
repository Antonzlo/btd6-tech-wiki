"""Bloon and round pages."""
import collections
import functools
from wiki.core import (
    DATA, GAME, INDEX, Raw, SHOP_ORDER, bloon_css, bloon_icon_style, card, esc, fmt, game_text, group, icon,
    label, load, page, short_type, skipped, stats, t, table,
)


# ---------- bloons (shared by the bloons and rounds pages) ----------

BLOONS = {f.stem: load(f) for f in sorted((DATA / "Bloons").rglob("*.json"))}


def children(b):
    out = []
    for beh in BLOONS[b].get("behaviors") or []:
        if isinstance(beh, dict) and short_type(beh) == "SpawnChildrenModel":
            out += beh.get("children") or []
    return out


@functools.cache
def rbe(b):
    """Total HP of every layer."""
    return BLOONS[b].get("maxHealth", 1) + sum(rbe(c) for c in children(b))


@functools.cache
def pops(b):
    """Layers popped, one $ each."""
    return 1 + sum(pops(c) for c in children(b))


def bloon_name(b):
    m = BLOONS[b]
    parts = [t(m.get("baseId"), fallback=m.get("baseId"))]
    if m.get("isFortified"):
        parts.append("укрепл.")
    if m.get("isGrow"):
        parts.append(t("Regrow").lower())
    if m.get("isCamo"):
        parts.append(t("Camo").lower())
    return " ".join(parts)


BLOON_GROUPS = [
    ("regular", "Обычные шары", ["Red", "Blue", "Green", "Yellow", "Pink", "Black", "White", "Purple", "Lead", "Zebra",
                                 "Rainbow", "Ceramic"]),
    ("moab", "MOAB-класс", ["Moab", "Bfb", "Zomg", "Ddt", "Bad"]),
    ("golden", "Золотые", ["Golden", "GoldenLead", "GoldenLeadPurple", "GoldenLeadPurpleZebra"]),
    ("special", "Особые", ["AuraBloon", "DoshBloon", "GlassBloon", "DynamiteBloon", "RetributionBloon", "RingleaderBloon",
                           "DiamondBloon"]),
    ("undead", "Нежить", ["UndeadMoab", "UndeadBfb", "UndeadZomg"]),
]
# BloonProperties flags from the game code
# bits from the game enum (game.json), Russian labels by enum name
PROP_LABELS = {"Lead": "Свинец", "Black": "Чёрный", "White": "Белый", "Purple": "Фиолетовый", "Frozen": "Заморожен",
               "Immune": "Неуязвим", "Glass": "Стекло"}
BLOON_PROPS = [(bit, PROP_LABELS.get(n, n)) for n, bit in GAME["bloonProperties"].items() if bit]


PROP_INFO = {
    1: "Не лопается острыми атаками.", 2: "Невосприимчив к взрывам.", 4: "Невосприимчив к холоду и заморозке.",
    8: "Невосприимчив к огню, энергии и плазме.", 16: "Состояние замороженного шара: острые атаки его не лопают.",
    32: "Временно не получает урон.", 64: "Свойство шаров режима Frontier.",
}


def damage_masks(obj, out):
    """immuneBloonProperties of every DamageModel inside a tower model."""
    if isinstance(obj, dict):
        if short_type(obj) == "DamageModel":
            out.append(obj.get("immuneBloonProperties") or 0)
        for v in obj.values():
            damage_masks(v, out)
    elif isinstance(obj, list):
        for v in obj:
            damage_masks(v, out)
    return out


def properties_card():
    """What each bloon property means and which base towers (000) cannot damage it at all."""
    masks = {p.name: damage_masks(load(p / f"{p.name}.json"), []) for p in sorted((DATA / "Towers").iterdir()) if p.is_dir()}
    rows = []
    for bit, name in BLOON_PROPS:
        blocked = [tid for tid in SHOP_ORDER if masks.get(tid) and all(m & bit for m in masks[tid])]
        towers = " ".join(f"<a class='badge' href='tower-{tid}.html'><span>000</span><b>{icon('towers', tid, 18)}"
                          f"{esc(t(tid, fallback=tid))}</b></a>" for tid in blocked)
        rows.append(f"<div class='prop-row' id='prop-{bit}'><span class='badge no'><span>свойство</span><b>{esc(name)}</b></span>"
                    f"<div><p>{esc(PROP_INFO.get(bit, ''))}</p>"
                    + (f"<p class='note'>Не наносят урона базовой атакой:</p><div class='chips'>{towers}</div>" if towers else "")
                    + "</div></div>")
    return card("props", "Свойства", "<details class='fold'><summary>Что значит каждое свойство и какие башни его не лопают</summary>"
                "<p class='note'>Список башен посчитан по immuneBloonProperties урона их снарядов "
                "в базовой модели (000). Улучшения часто снимают ограничение.</p>" + "".join(rows) + "</details>", section="Шары")


def build_bloons():
    body, toc = [properties_card()], [("props", "Свойства")]
    for gid, title, members in BLOON_GROUPS:
        cards = []
        for b in members:
            if b not in BLOONS:
                continue
            m = BLOONS[b]
            name = t(b, fallback=b)
            props = " ".join(f"<a class='badge no' href='#prop-{bit}'><span>свойство</span><b>{esc(p)}</b></a>"
                             for bit, p in BLOON_PROPS if (m.get("bloonProperties") or 0) & bit)
            kids = collections.Counter(children(b))
            kid_badges = " ".join(
                f"<a class='badge' href='bloons.html#{esc(BLOONS[c].get('baseId', c))}'><span>дети</span>"
                f"<b>{icon('bloons', c, 18)}{n}× {esc(bloon_name(c))}</b></a>" for c, n in kids.items() if c in BLOONS)
            variants = sorted((f.stem for f in (DATA / "Bloons" / b).glob("*.json") if f.stem != b),
                              key=lambda v: (rbe(v), v))
            vrows = [(Raw(f"<span class='mod-name'>{icon('bloons', v, 22) or '<span class=mod-ic></span>'}{esc(bloon_name(v))}</span>"),
                      BLOONS[v].get("maxHealth"), rbe(v), BLOONS[v].get("speed")) for v in variants]
            beh = sorted({label(short_type(x)) for x in m.get("behaviors") or [] if isinstance(x, dict) and not skipped(x)})
            pic = icon("bloons", b, 72, "ic kicon")
            inner = ("<div class='hero-row'>" + pic + "<div>"
                     + game_text(t(f"{b}Desc"))
                     + stats([("HP слоя", m.get("maxHealth")), ("RBE", rbe(b)), ("$ за лопание", pops(b)),
                              ("скорость", m.get("speed")), ("урон слоя при утечке", m.get("leakDamage"))])
                     + (f"<div class='chips'>{props} {kid_badges}</div>" if props or kid_badges else "")
                     + "</div></div>"
                     + (f"<h3>Варианты ({len(vrows)})</h3>" + table(["Вариант", "HP слоя", "RBE", "Скорость"], vrows) if vrows else "")
                     + (f"<h3>Поведения</h3><div class='chips'>{''.join(f'<span class=chip>{esc(x)}</span>' for x in beh)}</div>" if beh else ""))
            cards.append(card(b, name, inner, en_id=b, section="Шары"))
        if cards:
            body.append(group(gid, title, cards))
            toc.append((gid, title))
    page("bloons.html", "Шары",
         "HP слоя, RBE (сумма HP всех слоёв), деньги за полное лопание, скорость, свойства и дети каждого шара.",
         "".join(body), toc)


@functools.cache
def raw_round_pops(rs="DefaultRoundSet"):
    out = {}
    for f in sorted((DATA / "Rounds" / rs).glob("*.json")):
        r = int(f.stem)
        out[r] = sum(g["count"] * pops(g["bloon"]) for g in load(f).get("groups") or [])
    return dict(sorted(out.items()))


@functools.cache
def bonus_cash_mod():
    return next((m for m in load(DATA / "Mods" / "Medium.json").get("mutatorMods") or []
                 if short_type(m) == "BonusCashPerRoundModModel"), {})


@functools.cache
def round_cash(rs="DefaultRoundSet"):
    """{round: (pop cash, end of round bonus)}: 1 $ per layer popped times the DefaultIncomeSet multiplier of the round,
    bonus from the Medium mode model (BonusCashPerRoundModModel: baseCash + round * roundMultiple)."""
    income = load(DATA / "IncomeSets" / "DefaultIncomeSet.json")

    def income_mult(r):
        return next((th["multiplier"] for th in income.get("thresholds") or [] if r <= th["threshold"]),
                    income.get("finalMultiplier", 1))
    raw = raw_round_pops(rs)
    bmod = bonus_cash_mod()
    base_b = bmod.get("baseCash", 100)
    mult_b = bmod.get("roundMultiple", 1)
    return {r: (p * income_mult(r), base_b + r * mult_b) for r, p in raw.items()}


def build_rounds():
    bloons = BLOONS

    def tags(b):
        m = bloons[b]
        return {k for k, on in (("camo", m.get("isCamo")), ("regrow", m.get("isGrow")), ("fortified", m.get("isFortified")),
                                ("lead", m.get("baseId") == "Lead"), ("ceramic", m.get("baseId") == "Ceramic"),
                                ("moab", m.get("isMoab"))) if on}

    prop_names = {"camo": t("Camo"), "regrow": t("Regrow"), "fortified": "Укреплённые"}
    filters = [("", "Все"), ("new", "С новым"), ("camo", t("Camo")), ("regrow", t("Regrow")), ("fortified", "Укреплённые"),
               ("lead", t("Lead")), ("ceramic", t("Ceramic")), ("moab", "MOAB-класс")]

    sections, toc = [], []
    for rs, title in (("DefaultRoundSet", "Обычные раунды"), ("AlternateRoundSet", "Альтернативные раунды (ABR)")):
        folder = DATA / "Rounds" / rs
        rows, total, seen = [], 0, set()
        for f in sorted(folder.glob("*.json"), key=lambda f: int(f.stem)):
            r = int(f.stem)
            groups = load(f).get("groups") or []
            chips = "".join(f"<a class='chip bchip' href='bloons.html#{esc(bloons[g['bloon']].get('baseId', g['bloon']))}'>"
                            f"<i class='bi bi-{bloon_css(g["bloon"])}'></i>{g['count']}× {esc(bloon_name(g['bloon']))}</a>" for g in groups)
            r_rbe = sum(g["count"] * rbe(g["bloon"]) for g in groups)
            cash, bonus = round_cash(rs)[r]
            total += cash + bonus
            dur = max((g["end"] for g in groups), default=0) / 60
            # first appearance of a bloon type or a property (camo, regrow, fortified)
            row_tags = set().union(*(tags(g["bloon"]) for g in groups)) if groups else set()
            feats = [bloons[g["bloon"]].get("baseId") for g in groups] + [p for p in ("camo", "regrow", "fortified") if p in row_tags]
            new = list(dict.fromkeys(x for x in feats if x not in seen))
            seen.update(new)
            badges = "".join(f"<span class='chip new'>{esc(prop_names[x])}</span>" if x in prop_names
                             else f"<a class='chip new' href='bloons.html#{esc(x)}'>{esc(t(x, fallback=x))}</a>" for x in new)
            if new:
                row_tags.add("new")
            cells = [r, Raw(f"<div class='chips'>{chips}</div>"), Raw(f"<div class='chips'>{badges}</div>"), r_rbe,
                     round(cash, 1), bonus, round(total, 1), round(dur, 2)]
            rows.append(f"<tr data-tags='{' '.join(sorted(row_tags))}'{' class=newrow' if new else ''}>" + "".join(
                f"<td class='n'>{fmt(c)}</td>" if isinstance(c, (int, float)) else f"<td>{c}</td>" for c in cells) + "</tr>")
        head = "".join(f"<th>{h}</th>" for h in ("Раунд", "Шары", "Впервые", "RBE", "$ за лопание", "$ бонус", "$ всего с 1-го", "Длит., с"))
        bar = (f"<div class='tagbar' data-target='#{rs}-t'>"
               + "".join(f"<button type='button' data-tag='{k}'{' class=on' if not k else ''}>{esc(n)}</button>" for k, n in filters)
               + "</div>")
        INDEX.append([title, "Раунды", f"rounds.html#{rs}", rs])
        sections.append(card(rs, title,
                             (f"<div class='chips'><a class='badge' href='modes.html#AlternateBloonsRounds'><span>режим</span><b>{icon('ui', 'mode-AlternateBloonsRounds', 18)}{esc(t('Mode AlternateBloonsRounds', fallback='ABR'))}</b></a></div>" if rs == "AlternateRoundSet" else "") + bar + "<input class='filter' type='search' placeholder='Фильтр: номер или шар' aria-label='Фильтр раундов' "
                             f"data-filter='#{rs}-t tbody tr'>"
                             f"<div class='wrap'><table id='{rs}-t'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
                             section="Раунды"))
        toc.append((rs, title))
    page("rounds.html", "Раунды",
         "Шары каждого раунда, RBE и деньги. За лопание 1 $ за слой с множителем дохода раунда, "
         "бонус за раунд 100 $ + номер раунда. HP MOAB-класса в поздних раундах растёт, здесь базовые значения.",
         bloon_icon_style(set(bloons)) + "".join(sections), toc)
