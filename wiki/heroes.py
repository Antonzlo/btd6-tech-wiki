"""Hero pages: levels, XP calculator, abilities."""
import json
import re
from wiki import core
from wiki.core import (
    DATA, GAME, Raw, card, esc, game_text, icon, json_files, load, page, sort_bar, stats, t, table,
)
from wiki.knowledge import knowledge_mods
from wiki.towers import (
    abilities_of, abilities_table, combat_stats, diff_selector, levels_table, num, price, tier_stats,
)
from wiki.bloons import round_cash


def hero_level_rows(folder, base, ucost):
    """Attack numbers per hero level: level 1 is the base model, level N the "<Hero> N.json" model."""
    rows, prev = [], None
    for lvl in range(1, 21):
        f = folder / f"{folder.name} {lvl}.json"
        if lvl > 1 and not f.exists():
            continue
        s = tier_stats(combat_stats(base if lvl == 1 else load(f), ucost))
        rows.append((lvl, s, prev))
        prev = s
    return rows


START_CASH = 650  # standard starting cash; not in the export (the game model default, not a mode modifier)


def hero_calc(totals, cost):
    """Hero calculator: round each level is reached for a placement round and map difficulty, and the round the
    hero becomes affordable. totals = cumulative XP for levels 2..20. XP per round and the map difficulty scales come
    from xp.json (the knowledge dumper calls the game's own functions); per round it is XP x map scale, rounded.
    hcalc() in site.js does the math and continues the table linearly past its last round."""
    cash = [round(p + b) for p, b in round_cash().values()]
    xp = load(DATA / "KnowledgeLayout" / "xp.json")
    maps = list(xp["trackDifficultyXpScale"].items())
    km = knowledge_mods()
    mods = {n: (km.get(n) or [{}])[0] for n in ("MonkeyEducation", "SelfTaughtHeroes", "EmpoweredHeroes", "HeroFavors")}
    # ponytail: XP bonuses assumed additive (1 + 0.08 + 0.10); Monkeys Together Strong left out, it needs a second hero
    mk = {"xp": mods["MonkeyEducation"].get("multiplier", 0) + mods["SelfTaughtHeroes"].get("multiplier", 0),
          "levels": mods["EmpoweredHeroes"].get("levels", 0), "discount": mods["HeroFavors"].get("multiplier", 0)}
    names = ", ".join(t(n, fallback=n) for n in mods)
    return (f"<div class='hcalc' data-reqs='{json.dumps(totals)}' data-cost='{cost}' "
            f"data-cash='{json.dumps(cash)}' data-mk='{json.dumps(mk)}' "
            # index 0 of the dump is GetXpForRound(0) = XP for finishing round 1
            f"data-xp='{json.dumps([round(v) for v in xp['heroXpPerRound']])}'><div class='hcalc-in'>"
            "<label>Карта <select>" + "".join(f"<option value='{m}'>{esc(t(n, fallback=n))}</option>" for n, m in maps)
            + "</select></label><label>Ставлю на раунде <input class='hc-round' type='number' min='1' max='140' value='1'></label>"
            f"<label>Старт $ <input class='hc-start' type='number' min='0' step='50' value='{START_CASH}'></label>"
            f"<label title='{esc(names)}'><input class='hc-mk' type='checkbox'> Знания</label></div>"
            "<p class='hcalc-cash'></p><div class='hcalc-out'></div>"
            f"<p class='note'>Знания: {esc(names)}: опыт +{mk['xp'] * 100:g}%, старт с {1 + mk['levels']} уровня, "
            f"цена −{mk['discount'] * 100:g}%. Бонусы к опыту сложены. Другие бонусы к опыту: <a href='https://svrng.github.io/BTD6-Hero-XP-Calculator/' "
            "rel='noopener'>BTD6 Hero XP Calculator</a>.</p></div>")


def build_heroes():
    upgrades = {f.stem: load(f) for f in json_files("Upgrades")}
    ucost = {u.get("name"): u.get("cost", 0) for u in upgrades.values()}
    heroes = []
    for folder in sorted(p for p in (DATA / "Heroes").iterdir() if p.is_dir()):
        hid = folder.name
        base = load(folder / f"{hid}.json")
        # level N comes from the upgrade's tier (N - 1); xpCost is the XP from level N-1 to N, hero XP scale included
        top = load(folder / f"{hid} 20.json")
        levels = sorted(((upgrades[u].get("tier", 0) + 1, upgrades[u].get("xpCost", 0))
                         for u in top.get("appliedUpgrades") or [] if u in upgrades))
        heroes.append((base.get("cost", 0), t(hid, fallback=hid), hid, base, levels, abilities_of([(None, top)]), top))
    selector = diff_selector()
    heroes.sort(key=lambda h: h[:3])
    for cost, name, hid, base, levels, abils, top in heroes:
        core.current_file = f"hero-{hid}.html"
        # ability icon on the level that unlocks it (level upgrades have no icons of their own)
        pics = {upgrades[b["addedViaUpgrade"]].get("tier", 0) + 1: icon("abilities", (b.get("icon") or {}).get("guidRef") or "", 32)
                for b in abils.values() if b.get("addedViaUpgrade") in upgrades}

        def lvl_text(n):
            text = esc(re.sub(r"</?(sup|sub|b|i|u)>|</?color[^>]*>", "", t(f"{hid} Level {n} Description", fallback="")))
            return f"<span class='mod-name'>{pics[n]}<span>{text}</span></span>" if pics.get(n) else text
        total, rows = 0, [(1, "–", 0, lvl_text(1))]
        for lvl, xp in levels:
            total += xp
            rows.append((lvl, xp, total, lvl_text(lvl)))
        lvl_rows = hero_level_rows(DATA / "Heroes" / hid, base, ucost)
        about = ("<div class='hero-row'>" + icon("heroes", hid, 120, "ic portrait") + "<div>"
                 + game_text(t(f"{hid} Description"))
                 + stats([("цена", price([cost])), ("дальность", num(base.get("range"))), ("XP до 20 уровня", total)])
                 + "</div></div>")
        numbers = (levels_table(lvl_rows, first_col="Уровень", only_changed=True)
                   + (f"<details><summary>Все уровни</summary>" + levels_table(lvl_rows, first_col="Уровень") + "</details>"
                      if len(lvl_rows) > 2 else ""))
        body = (selector
                + card("about", name, about, en_id=hid, section="Герои")
                + card("levels", "Уровни и опыт", table(["Уровень", "XP до уровня", "XP всего", "Что даёт"],
                                                        [(a, b, c, Raw(d)) for a, b, c, d in rows]), section=name)
                + card("calc", "Калькулятор", hero_calc([r[2] for r in rows[1:]], cost), section=name)
                + card("numbers", "Числа по уровням", numbers, section=name)
                + (card("abilities", "Способности", abilities_table(
                    abils, lambda up: f"уровень {upgrades[up].get('tier', 0) + 1}" if up in upgrades else esc(up)), section=name)
                   if abils else ""))
        page(core.current_file, name, esc(t(f"{hid} Short Description", fallback="")), body,
             toc=[("about", "Описание"), ("levels", "Уровни и опыт"), ("calc", "Калькулятор"), ("numbers", "Числа по уровням")]
             + ([("abilities", "Способности")] if abils else []))
    core.current_file = "heroes.html"
    # hero select screen order from game.json (btd6-knowledge-dumper F6 on that screen); heroSet index, then cost, as fallbacks
    order = {hid: i for i, hid in enumerate(GAME.get("heroScreen") or [])} or {h["id"]: h["index"] for h in GAME.get("heroSet") or []}
    heroes.sort(key=lambda h: (order.get(h[2], 99), h[:3]))
    grid = "".join(f"<a class='tile tower-tile' href='hero-{esc(hid)}.html' data-order='{i}' data-cost='{cost}' "
                   f"data-xp='{sum(xp for _, xp in levels)}'>{icon('heroes', hid, 72)}"
                   f"<span><b>{esc(name)}</b>{price([cost], 'cost tile-price')}</span></a>"
                   for i, (cost, name, hid, base, levels, *_) in enumerate(heroes))
    page("heroes.html", "Герои", "",
         selector + sort_bar("hero-grid", [("order", "Как в игре"), ("cost", "По цене"), ("xp", "По XP до 20 уровня")])
         + f"<div class='grid cols3' id='hero-grid'>{grid}</div>")
