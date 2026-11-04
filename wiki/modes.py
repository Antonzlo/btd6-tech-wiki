"""Game mode and income pages."""
import collections
import re
from wiki.core import (
    card, esc, fmt, game_text, group, icon, json_files, load, page, short_type, stats, t, table,
)
from wiki.charts import dual_line_chart
from wiki.mods import mod_table
from wiki.bloons import bonus_cash_mod, raw_round_pops


# The game stacks a mode on the difficulty it is picked under; that link is not in the export (the in-game menu).
MODE_BASE = {"Impoppable": "Hard", "Clicks": "Hard", "HalfCash": "Hard", "DoubleMoabHealth": "Hard",
             "AlternateBloonsRounds": "Hard", "MagicOnly": "Hard", "MilitaryOnly": "Medium", "Apopalypse": "Medium",
             "Reverse": "Medium", "PrimaryOnly": "Easy", "Deflation": "Easy"}


INCOME_NAMES = {"DefaultIncomeSet": "Обычный доход", "AcceleratedIncomeSet": "Ускоренный доход",
                "EnduranceIncomeSet": "Доход в режиме выносливости", "FrontierIncomeSet": "Доход Frontier",
                "FrontierReducedIncomeSet": "Сниженный доход Frontier", "MOABMadnessIncomeSet": "Доход MOAB Madness",
                "RogueIncomeSet": "Доход Rogue Legends"}


def mode_name(stem):
    m = re.fullmatch(r"Coop(Standard|Deflation)Cash(\d)", stem)  # no game text for the coop cash variants
    if m:
        base = t("Mode Deflation", fallback="Deflation") if m[1] == "Deflation" else "Стандарт"
        return f"{base}, кооператив на {m[2]}"
    return t(f"Mode {stem}", stem, fallback=stem)


def mode_total(stem, files):
    """Effective values of a mode: its base difficulty's modifiers, then its own, with where each value comes from.
    Stacking (inferred, matches in-game prices and lives): multipliers multiply, changeBase/round/set replace,
    addition adds; a multiplier of 0 next to an addition or changeBase means "not used"."""
    chain = [s for s in (MODE_BASE.get(stem), stem) if s and s in files]
    name = mode_name
    v, src = {}, collections.defaultdict(list)
    for s in chain:
        who = name(s)
        for m in load(files[s]).get("mutatorMods") or []:
            ty = short_type(m)
            if ty == "StartingCashModModel":
                if m.get("changeBase"):
                    v["cash"], src["cash"] = m["changeBase"], [f"{who}: {fmt(m['changeBase'])}"]
                if m.get("multiplier"):
                    v["cash"] = v.get("cash", 0) * m["multiplier"]; src["cash"].append(f"{who} ×{m['multiplier']:g}")
                if m.get("addition"):
                    v["cash"] = v.get("cash", 0) + m["addition"]; src["cash"].append(f"{who} +{fmt(m['addition'])}")
            elif ty == "StartingHealthModModel":
                v["lives"] = v.get("lives", 0) * m.get("multiplier", 0) + m.get("addition", 0)
                src["lives"] = [f"{who}: {fmt(v['lives'])}"]
            elif ty == "MaxHealthModModel" and m.get("set"):
                v["maxlives"], src["maxlives"] = m["set"], [f"{who}: {fmt(m['set'])}"]
            elif ty in ("GlobalCostModModel", "GlobalSpeedModModel", "ModifyAllCashModModel"):
                k = {"GlobalCostModModel": "cost", "GlobalSpeedModModel": "speed", "ModifyAllCashModModel": "allcash"}[ty]
                v[k] = v.get(k, 1) * m.get("multiplier", 1); src[k].append(f"{who} ×{m.get('multiplier', 1):g}")
            elif ty == "SellMultiplierModModel":
                v["sell"] = v.get("sell", 0) * m.get("multiplier", 0) + m.get("addition", 0)
                src["sell"] = [f"{who}: {v['sell'] * 100:g}%"]
            elif ty == "BonusCashPerRoundModModel":
                v["bonus"] = (m.get("baseCash", 0), m.get("roundMultiple", 0)); src["bonus"] = [who]
            elif ty in ("StartingRoundModModel", "EndRoundModModel"):
                k = "start" if ty == "StartingRoundModModel" else "end"
                v[k], src[k] = m.get("round"), [f"{who}: {'начало с раунда' if k == 'start' else 'конец на раунде'} {m.get('round')}"]
            elif ty == "MonkeyMoneyModModel":
                if m.get("changeBase"):
                    v["mm"], src["mm"] = m["changeBase"], [f"{who}: {fmt(m['changeBase'])}"]
                if m.get("multiplier", 1) != 1:
                    v["mm"] = v.get("mm", 0) * m["multiplier"]; src["mm"].append(f"{who} ×{m['multiplier']:g}")
            elif ty == "RoundSetModModel":
                v["rounds"], src["rounds"] = m.get("roundsetName"), [who]
    if "maxlives" in v and v.get("lives", 0) > v["maxlives"]:
        v["lives"] = v["maxlives"]
        src["lives"].append(src["maxlives"][0].replace(": ", ": максимум "))
    cm = v.get("allcash", 1)
    one = "×1" if chain[0] in ("Easy", "Medium", "Hard") else None  # coop, sandbox, tutorial: no difficulty under them
    rows = [
        ("Стартовые деньги", f"${fmt(round(v['cash']))}" if "cash" in v else None, "cash"),
        ("Жизни", fmt(v.get("lives")) if "lives" in v else None, "lives"),
        ("Цены", f"×{v['cost']:.4g}" if "cost" in v else one, "cost"),
        ("Скорость шаров", f"×{v['speed']:.4g}" if "speed" in v else one, "speed"),
        ("Деньги за лопание", f"×{cm:g}" if "allcash" in v else None, "allcash"),
        ("Бонус за раунд", (f"${fmt(v['bonus'][0] * cm)} + {v['bonus'][1] * cm:g} × раунд" if "bonus" in v else None), "bonus"),
        ("Продажа", f"{v['sell'] * 100:g}%" if "sell" in v else None, "sell"),
        ("Раунды", f"{v.get('start', 1)}–{v['end']}" if "end" in v else None, "end"),
        ("Набор раундов", f"<a href='rounds.html#{esc(v['rounds'])}'>{esc(v['rounds'])}</a>" if v.get("rounds") else None, "rounds"),
        ("Monkey Money за победу", fmt(round(v["mm"])) if "mm" in v else None, "mm"),
    ]
    out = []
    for lbl, val, k in rows:
        if val is None:
            continue
        s = src.get(k) or []
        if k == "end" and "start" in v:
            s = src["start"] + s
        if k == "bonus" and "allcash" in v:
            s = s + src["allcash"]
        out.append((lbl, val, ", ".join(s) or "по умолчанию"))
    if not out:
        return ""
    base = f" База: {name(chain[0])}." if len(chain) > 1 else ""
    return ("<h3>Итог</h3>" + table(["Параметр", "Значение", "Откуда"], out).replace("<table>", "<table class='nosort'>", 1)
            + f"<p class='note'>Сложено из модификаторов сложности и режима.{base} Monkey Money это база, "
            "в игре она ещё зависит от сложности карты.</p>")


MODE_GROUPS = [
    ("difficulty", "Сложности", ["Easy", "Medium", "Hard", "Impoppable"]),
    ("modes", "Режимы игры", None),  # everything not listed elsewhere
    ("coop", "Кооператив", ["CoopStandardCash2", "CoopStandardCash3", "CoopStandardCash4",
                             "CoopDeflationCash2", "CoopDeflationCash3", "CoopDeflationCash4"]),
    ("other", "Прочее", ["Sandbox", "Tutorial"]),
]


def build_modes():
    files = {f.stem: f for f in json_files("Mods")}
    listed = {m for _, _, ms in MODE_GROUPS if ms for m in ms}
    body, toc = [], []
    for gid, title, members in MODE_GROUPS:
        cards = []
        for stem in members or sorted(set(files) - listed):
            if stem not in files:
                continue
            mods = load(files[stem]).get("mutatorMods") or []
            name = mode_name(stem)
            key = {"PrimaryOnly": "Primary", "MilitaryOnly": "Military", "MagicOnly": "Magic"}.get(stem) or (
                "mode-Deflation" if stem.startswith("CoopDeflation") else "mode-Medium" if stem.startswith("CoopStandard")
                else f"mode-{stem}")
            pic = icon("ui", key, 96, "ic mode-ic")
            desc = t(f"et_{stem.lower()}description")
            if "{0}" in desc:  # Deflation: "start at round {0} with {1} cash", values from its own modifiers
                vals = {short_type(m): m for m in mods}
                desc = desc.replace("{0}", fmt(vals.get("StartingRoundModModel", {}).get("round", "?"))).replace(
                    "{1}", fmt(vals.get("StartingCashModModel", {}).get("changeBase", "?")))
            inner = (f"<div class='hero-row'>{pic}<div>" if pic else "<div><div>") + game_text(desc) + mode_total(stem, files) + mod_table(mods) + "</div></div>"
            cards.append(card(stem, name, inner, en_id=stem, section="Режимы"))
        if cards:
            body.append(group(gid, title, cards))
            toc.append((gid, title))
    page("modes.html", "Режимы и сложности",
         "Модификаторы каждого режима: деньги, HP, цены, запреты. CoopStandardCash и CoopDeflationCash "
         "задают деньги для 2, 3 и 4 игроков в коопе.",
         "".join(body), toc)


def build_income():
    body, toc = [], []
    raw = raw_round_pops("DefaultRoundSet")
    bmod = bonus_cash_mod()
    base_b = bmod.get("baseCash", 100)
    mult_b = bmod.get("roundMultiple", 1)
    ticks = (1, 20, 40, 60, 80, 100, 120, 140)
    k = lambda v: f"{round(v / 1000, 1):g}k" if v >= 1000 else fmt(round(v))
    tip = lambda r, c, s: f"раунд {r}: ${fmt(round(c))} за раунд · всего ${fmt(round(s))}"

    for f in sorted(json_files("IncomeSets"), key=lambda f: (f.stem != "DefaultIncomeSet", f.stem)):
        d = load(f)
        thresholds = d.get("thresholds") or []
        final_mult = d.get("finalMultiplier", 1)

        def inc_mult(r, ths=thresholds, fm=final_mult):
            for th in ths:
                if r <= th["threshold"]:
                    return th["multiplier"]
            return fm

        cash = [raw.get(r, 0) * inc_mult(r) + base_b + r * mult_b for r in range(1, 141)]
        total = [sum(cash[:i + 1]) for i in range(len(cash))]

        rows, start = [], 1
        for th in thresholds:
            rows.append((f"{start}–{th['threshold']}", th["multiplier"], f"{th['multiplier'] * 100:g}%"))
            start = th["threshold"] + 1
        rows.append((f"{start}+", final_mult, f"{final_mult * 100:g}%" if final_mult is not None else "–"))

        chart = dual_line_chart(cash, total, ticks, f"{f.stem} 1–140", k, k, tip,
                                ys3=[inc_mult(r) for r in range(1, 141)])
        st = stats([("всего 1–80", f"${fmt(round(sum(cash[:80])))}"),
                    ("всего 1–100", f"${fmt(round(sum(cash[:100])))}"),
                    ("всего 1–140", f"${fmt(round(sum(cash)))}")])
        inner = st + chart + table(["Раунды", "Множитель", "От обычного"], rows)
        title = INCOME_NAMES.get(f.stem, f.stem)
        body.append(card(f.stem, title, inner, en_id=f.stem, tagline=f.stem, section="Доход"))
        toc.append((f.stem, title))

    page("income.html", "Доход по раундам",
         "Деньги за лопание умножаются на коэффициент раунда. Для каждого набора показан график 1–140 "
         "с падением дохода за раунд (слева) и накопленной суммой денег (справа).",
         f"<div class='cards'>{''.join(body)}</div>", toc)
