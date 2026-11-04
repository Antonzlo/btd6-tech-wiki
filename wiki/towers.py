"""Tower pages: upgrades, crosspaths, abilities, numbers by tier."""
import json
import re
from wiki import core
from wiki.core import (
    DATA, INDEX, Raw, SHOP_ORDER, TOWER_SETS, card, esc, fmt, game_text, icon, json_files, label, load, page,
    scalar, short_type, skipped, stats, t, table,
)
from wiki.knowledge import knowledge_card, tower_knowledge
from wiki.bloons import BLOON_PROPS


EFFECT_WORDS = ("Slow", "Freeze", "Stun", "Knockback", "Wind", "DamageOverTime", "AddBehaviorToBloon", "Bleed", "Burn")


def num(v):
    return round(v, 4) if isinstance(v, float) else v


def mod_text(b):
    """A damage-modifier or effect behavior as text: kind + its numeric fields."""
    st = short_type(b)
    if "DamageModifier" in st:
        fields = {k: v for k, v in b.items() if scalar(v) and k not in ("$type", "name", "collisionPass") and v not in (0, 0.0, False, "")}
        return label_mod(st) + ": " + ", ".join(f"{k} {fmt(v)}" for k, v in fields.items())
    if any(w in st for w in EFFECT_WORDS):
        nums = {k: v for k, v in b.items() if scalar(v) and not k.startswith("$") and k not in ("name",)}
        return ", ".join([label(st)] + [f"{k} {fmt(v)}" for k, v in nums.items() if v not in (None, 0, 0.0, False, "")])
    return label(st)


def label_mod(st):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", st.replace("DamageModifierFor", "").replace("Model", "")) or st


def nested_towers(x, root=True):
    """TowerModels inside a model (not descending into them; combat_stats recurses on its own)."""
    if isinstance(x, dict):
        if not root and short_type(x) == "TowerModel":
            yield x
            return
        for v in x.values():
            yield from nested_towers(v, False)
    elif isinstance(x, list):
        for v in x:
            yield from nested_towers(v, False)


def combat_stats(d, upgrade_costs):
    """Combat numbers of a tower (or sub-tower / hero) model as a flat list: attack -> projectile ->
    damage, pierce, attack rate, projectile count, range; each row also gets the damage per shot
    (damage x count) and the simplified DPS (shot damage / reload), plus effects with numbers and the
    bloon properties the projectile cannot pop (immuneBloonProperties)."""
    attacks, projectiles, abilities, other = [], [], [], []
    for b in d.get("behaviors") or []:
        if not isinstance(b, dict) or skipped(b):
            continue
        st = short_type(b)
        if st.startswith("AttackModel") or st.endswith("AttackModel") or st == "AttackAirUnitModel":  # Ace, Heli fly their attacks
            weapons = []
            for w in b.get("weapons") or []:
                em = w.get("emission") or {}
                rate, count = num(w.get("rate")), em.get("count") or 1
                projs = []
                if isinstance(w.get("projectile"), dict):
                    projs = []
                    stack = [(w["projectile"], "Снаряд", count, 0, rate, num(b.get("range")), projs)]
                    while stack:
                        p, lbl, cnt, depth, rt, rg, acc = stack.pop()
                        beh = [x for x in p.get("behaviors") or [] if isinstance(x, dict)]
                        mods, effects = [], []
                        for x in beh:
                            xs = short_type(x)
                            if "DamageModifier" in xs:
                                mods.append(mod_text(x))
                            elif any(w2 in xs for w2 in EFFECT_WORDS):
                                effects.append(mod_text(x))
                        dmg = next((x for x in beh if short_type(x) == "DamageModel"), None)
                        damage = num(dmg["damage"]) if dmg else None
                        pierce = num(p.get("pierce"))
                        mask = (dmg or {}).get("immuneBloonProperties") or 0
                        shot = None if damage is None else damage * cnt
                        acc.append({"attack": label(st), "weapon": len(weapons) + 1, "projectile": lbl, "depth": depth,
                                    "count": cnt, "damage": damage, "pierce": pierce, "rate": rt, "range": rg,
                                    "immune": [[bit, name] for bit, name in BLOON_PROPS if mask & bit],
                                    "shotDamage": shot, "dps": None if (shot is None or not rt) else shot / rt,
                                    "mods": mods, "effects": sorted(set(effects))})
                        kids = [(v, label(short_type(x)), (x.get("emission") or {}).get("count") or 1, depth + 1, rt, rg, acc)
                                for x in beh for v in x.values() if isinstance(v, dict) and "ProjectileModel" in v.get("$type", "")]
                        stack.extend(reversed(kids))  # popped in model order, children right after their parent
                projectiles.extend(projs)
                weapons.append({"rate": rate, "count": count, "emission": label(short_type(em)) if em else "", "proj": projs})
            attacks.append({"name": label(st), "range": num(b.get("range")), "weapons": weapons})
        elif st == "AbilityModel":
            abilities.append({"name": t(b.get("displayName") or "", fallback=b.get("displayName") or b.get("name", "")),
                              "cooldown": num(b.get("cooldown"))})
        elif not any(s in st for s in ("Sound", "Effect", "Display")):
            other.append(label(st))
    # sub-towers (sentries, drones, pets, totems) sit inside the model as whole TowerModels: their attacks
    # join this tower's, prefixed with the sub-tower name
    seen = set()
    for sub in nested_towers(d):
        sid = sub.get("baseId") or sub.get("name") or ""
        if sid in seen:
            continue
        seen.add(sid)
        s = combat_stats(sub, {})
        for a in s["attacks"]:
            a["name"] = f"{t(sid, fallback=sid)}: {a['name']}"
        attacks.extend(s["attacks"])
        projectiles.extend(s["projectiles"])
    parts = [d.get("cost", 0)] + [upgrade_costs.get(u, 0) for u in d.get("appliedUpgrades") or []]
    return {"cost": sum(parts), "parts": parts, "range": num(d.get("range")), "attacks": attacks,
            "projectiles": projectiles, "abilities": abilities, "other": sorted(set(other))}


def abilities_of(models):
    """Abilities across (upgrade, model) pairs, first appearance wins: {display name: AbilityModel}.
    The upgrade of the first model that has it replaces addedViaUpgrade, which keeps the old name when a
    tier 5 swaps the ability (Plasma Monkey Fan Club says "Super Monkey Fan Club")."""
    out = {}
    for up, d in models:
        for b in d.get("behaviors") or []:
            if isinstance(b, dict) and short_type(b) == "AbilityModel" and not b.get("isHidden") and b.get("displayName"):
                out.setdefault(b["displayName"], {**b, "addedViaUpgrade": up or b.get("addedViaUpgrade")})
    return out


def ability_effect(b):
    """Effect numbers of an AbilityModel: speed-up, damage, radius from its sub-behaviors."""
    bits = []
    for sub in b.get("behaviors") or []:
        if not isinstance(sub, dict):
            continue
        st = short_type(sub)
        if st == "TurboModel":
            bits.append(f"ускорение ×{fmt(sub.get('multiplier'))}")
        elif st == "ActivateAttackModel":
            for atk in sub.get("attacks") or []:
                for w in atk.get("weapons") or []:
                    proj = w.get("projectile") or {}
                    radius = proj.get("radius")
                    if radius is not None:
                        bits.append(f"радиус {fmt(radius)}")
                    for pbeh in proj.get("behaviors") or []:
                        if isinstance(pbeh, dict) and short_type(pbeh) == "DamageModel":
                            bits.append(f"урон {fmt(pbeh.get('damage'))}")
    return "; ".join(bits) if bits else "–"


def abilities_table(abils, source):
    """Table of abilities: icon, name, where it comes from (source(upgrade name)), cooldown, effect, game text."""
    rows = []
    for key, b in abils.items():
        pic = icon("abilities", (b.get("icon") or {}).get("guidRef") or "", 40) or "<span class='mod-ic'></span>"
        text = t(f"{key} Ability Description", fallback=b.get("description") or "")
        rows.append((Raw(f"<span class='mod-name'>{pic}<b>{esc(t(f'{key} Ability', key, fallback=key))}</b></span>"),
                     Raw(source(b.get("addedViaUpgrade") or "")), Raw(f"{fmt(num(b.get('cooldown')))}&nbsp;с"),
                     Raw(ability_effect(b)),
                     re.sub(r"</?(sup|sub|b|i|u)>|</?color[^>]*>", "", text)))
    return table(["Способность", "Откуда", "Перезарядка", "Эффект", "Описание"], rows) if rows else ""


TIER_ROW_KEYS = ["000"]
for _i in range(3):
    for _t in range(1, 6):
        TIER_ROW_KEYS.append(("0" * _i) + str(_t) + ("0" * (2 - _i)))
TIER_ROW_KEYS.append("Paragon")


def tier_stats(d):
    """Numbers of one tier model for its main projectile (highest simplified DPS over all attacks):
    range, cooldown, damage per shot (× projectile count), pierce, DPS, properties it cannot pop."""
    d = d or {}
    projs = [p for p in d.get("projectiles") or [] if p.get("damage") is not None]
    p = max(projs, key=lambda p: p.get("dps") or 0, default={})
    return {"range": num(d.get("range")), "rate": p.get("rate"), "damage": p.get("shotDamage"), "pierce": p.get("pierce"),
            "dps": num(p.get("dps")), "immune": p.get("immune") or []}


def levels_table(rows, first_col="Тир", only_changed=False):
    """Attack numbers per row: (label, stats, previous stats or None). Cells that differ from the previous
    row's are highlighted; with only_changed, rows where nothing changed are left out."""
    head = f"<tr><th>{first_col}</th><th>Дальность</th><th>Перезарядка, с</th><th>Урон за выстрел</th><th>Пробив.</th><th>Примерный DPS</th><th>Не лопает</th></tr>"
    keys = ("range", "rate", "damage", "pierce", "dps", "immune")
    body = ""
    for label, s, prev in rows:
        diff = {k for k in keys if prev is not None and s[k] != prev[k]}
        if only_changed and prev is not None and not diff:
            continue
        immune = "".join(f"<a class='chip no' href='bloons.html#prop-{bit}'>{esc(n)}</a> " for bit, n in s["immune"]) or "\u2013"
        cells = "".join(f"<td class='n{' chg' if k in diff else ''}'>{fmt(s[k])}</td>" for k in keys[:-1])
        body += (f"<tr><td>{esc(label)}</td>{cells}"
                 f"<td{' class=chg' if 'immune' in diff else ''}>{immune}</td></tr>")
    return f"<div class='wrap'><table><thead>{head}</thead><tbody>{body}</tbody></table></div>"


def tier_table(variants):
    """Static per-tier numbers: base tower, then every tier of each upgrade path, then the paragon.
    Each tier is compared with the tier below it on the same path (100 with 000, 200 with 100)."""
    stats_of = {k: tier_stats(variants[k]) for k in TIER_ROW_KEYS if variants.get(k)}
    below = lambda k: None if k in ("000", "Paragon") else re.sub(r"[1-5]", lambda m: str(int(m.group()) - 1), k)
    return levels_table([(k, s, stats_of.get(below(k))) for k, s in stats_of.items()], first_col="Тир")


def diff_selector():
    """Difficulty switch. Every price() on the page is recomputed in the browser (applyDiff in search.js)."""
    diffs = {}
    for mode in ("Easy", "Medium", "Hard", "Impoppable"):
        mult = next((m.get("multiplier") for m in load(DATA / "Mods" / f"{mode}.json").get("mutatorMods") or []
                     if short_type(m) == "GlobalCostModModel"), None)
        diffs[mode] = mult if mult is not None else 1.0
    # Impoppable is a mode played on Hard: the two cost bonuses add up (1 + 0.08 + 0.12 = 1.2; Quincy $650,
    # Super Monkey $3000; multiplying them would give $655 and $3025)
    diffs["Impoppable"] = round(diffs["Impoppable"] + diffs["Hard"] - 1, 6)
    return ("<div class='diff' role='group' aria-label='Сложность'><span>Сложность</span>" + "".join(
        f"<button type='button' data-mult='{m}'{' class=on' if m == 1 else ''}>{icon('ui', f'mode-{n}', 22)}{esc(t(n, fallback=n))}</button>"
        for n, m in diffs.items()) + "</div>")


def price(parts, cls="cost"):
    """A price shown at Medium; diff_selector() on the page switches it, each part (purchase) rounded on its own."""
    return Raw(f"<span class='{cls}' data-parts='{','.join(str(p) for p in parts)}'>${fmt(sum(parts))}</span>")


def build_towers():
    upgrades = {load(f).get("name"): load(f) for f in json_files("Upgrades")}
    ucost = {k: v.get("cost", 0) for k, v in upgrades.items()}
    selector = diff_selector()
    tiles = {}
    for folder in sorted(p for p in (DATA / "Towers").iterdir() if p.is_dir()):
        tid = folder.name
        base = load(folder / f"{tid}.json")
        variants = {}
        for f in folder.glob(f"{tid}-*.json"):
            suffix = f.stem.split("-", 1)[1]
            variants[suffix] = combat_stats(load(f), ucost)
        variants["000"] = combat_stats(base, ucost)
        # upgrade paths from the max-tier files of each single path
        paths = []
        for i in range(3):
            key = "".join("5" if j == i else "0" for j in range(3))
            top = load(folder / f"{tid}-{key}.json") if (folder / f"{tid}-{key}.json").exists() else {}
            paths.append(top.get("appliedUpgrades") or [])
        name = t(tid, fallback=tid)
        file = f"tower-{tid}.html"
        core.current_file = file
        cols = []
        for i, path in enumerate(paths):
            done, rows = [], []
            for tier, u in enumerate(path, 1):
                c = ucost.get(u, 0)
                done.append(c)
                INDEX.append([t(u, fallback=u), name, f"{file}#upgrades", u])
                rows.append(f"<li>{icon('upgrades', u, 56, 'ic up-ic')}<div><div class='up-head'><b>{tier}. {esc(t(u, fallback=u))}</b>"
                            f"<span class='price'>{price([c], 'cost big')}<small>всего {price(done)}</small></span></div>"
                            f"<p>{esc(t(u + ' Description'))}</p></div></li>")
            cols.append(f"<div class='path'><h3>Путь {i + 1}</h3><ol>{''.join(rows)}</ol></div>")
        para = ""
        if (folder / f"{tid}-Paragon.json").exists():
            u = (load(folder / f"{tid}-Paragon.json").get("appliedUpgrades") or [""])[-1]
            INDEX.append([t(u, fallback=u), name, f"{file}#upgrades", u])
            para = (f"<div class='paragon'><h3>Парагон</h3><ol><li>{icon('upgrades', u, 72, 'ic up-ic para-ic')}<div>"
                    f"<div class='up-head'><b>{esc(t(u, fallback=u))}</b><span class='price'>{price([ucost.get(u, 0)], 'cost big')}</span></div>"
                    f"<p>{esc(t(u + ' Description'))}</p></div></li></ol></div>")
        picker = "".join(
            f"<div class='xp-row' data-path='{i}'><span>Путь {i + 1}</span>"
            + "".join(f"<button type='button' data-tier='{n}'>{n}</button>" for n in range(6)) + "</div>"
            for i in range(3))
        extra = [k for k in variants if not k.isdigit()]
        # abilities from the single-path models, tier by tier, then the paragon
        codes = ["".join(str(n) if j == i else "0" for j in range(3)) for n in range(1, 6) for i in range(3)] + ["Paragon"]
        models = [load(folder / f"{tid}-{c}.json") for c in codes if (folder / f"{tid}-{c}.json").exists()]
        abils = abilities_of(((m.get("appliedUpgrades") or [None])[-1], m) for m in models)
        up_code = {u: "".join(str(n) if j == i else "0" for j in range(3)) for i, path in enumerate(paths) for n, u in enumerate(path, 1)}
        where = {u: f"{'-'.join(c)}: {t(u, fallback=u)}" for u, c in up_code.items()}
        if para:
            where[u] = f"{t('Paragon', fallback='Парагон')}: {t(u, fallback=u)}"
        kn = tower_knowledge(tid, folder, up_code)
        body = (
            selector
            + card("about", name,
                 "<div class='hero-row'>" + icon('towers', tid, 120, 'ic portrait') + "<div>" + game_text(t(f"{tid} Description", f"{tid}Description"))
                 + stats([("цена", price([base.get("cost", 0)])), ("дальность", base.get("range")),
                          ("радиус места", base.get("radius")), ("категория", t(TOWER_SETS.get(base.get("towerSet")), fallback=""))])
                 + "</div></div>",
                 en_id=tid, section="Башни")
            + card("upgrades", "Улучшения", f"<div class='paths'>{''.join(cols)}</div>{para}", section=name)
            + (card("abilities", "Способности", abilities_table(abils, lambda up: esc(where.get(up, t(up, fallback=up)))),
                    section=name) if abils else "")
            + card("crosspath", "Кроссапгрейд",
                   "<p class='note'>Выберите тиры путей, как в игре. Показаны цена со всеми улучшениями, "
                   "атаки, перезарядка, урон и пробивание каждого снаряда, включая вложенные (взрывы, осколки).</p>"
                   f"<div class='xp' data-tower='{esc(tid)}'>{picker}"
                   + (f"<div class='xp-row'><span>Особые</span>" + "".join(
                       f"<button type='button' data-variant='{esc(k)}'>{esc(k)}</button>" for k in sorted(extra)) + "</div>" if extra else "")
                   + "<div class='xp-out'></div></div>"
                   f"<script type='application/json' class='xp-data'>{json.dumps(variants, ensure_ascii=False).replace('</', '<\\/')}</script>",
                   section=name)
            + card("tiers", "Числа по тирам", tier_table(variants), section=name)
            + (card("knowledge", "Знания", knowledge_card(kn), section=name) if kn else "")
        )
        page(file, name, esc(t(TOWER_SETS.get(base.get('towerSet')), fallback='')),
             body, toc=[("about", "Описание"), ("upgrades", "Улучшения")] + ([("abilities", "Способности")] if abils else [])
             + [("crosspath", "Кроссапгрейд"), ("tiers", "Числа по тирам")] + ([("knowledge", "Знания")] if kn else []))
        tiles.setdefault(base.get("towerSet"), []).append((tid, name, base.get("cost")))
    core.current_file = "towers.html"
    body = []
    for ts in sorted(tiles):
        grid = "".join(f"<a class='tile tower-tile' href='tower-{esc(tid)}.html'>{icon('towers', tid, 72)}<span><b>{esc(n)}</b>{price([c], 'cost tile-price')}</span></a>"
                       for tid, n, c in sorted(tiles[ts], key=lambda x: (SHOP_ORDER.index(x[0]) if x[0] in SHOP_ORDER else 99, x[2])))
        body.append(f"<h2 class='group' id='set-{TOWER_SETS.get(ts)}'>{esc(t(TOWER_SETS.get(ts), fallback=''))}</h2><div class='grid'>{grid}</div>")
    page("towers.html", "Башни",
         "Башни по категориям, в порядке магазина.", selector + "".join(body))
