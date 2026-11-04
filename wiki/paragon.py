"""Paragon and boss pages."""
import json
import math
import re
from wiki.core import (
    DATA, card, esc, flatten, fmt, game_text, icon, json_files, kv_table, label, load, page, short_type,
    skipped, stats, t, table,
)
from wiki.charts import line_chart


def paragon_calc(req, d):
    paragons = []
    for p in sorted((DATA / "Towers").glob("*/*-Paragon.json")):
        tid = p.parent.name
        up_f = DATA / "Upgrades" / f"{tid} Paragon.json"
        cost = load(up_f).get("cost", 0) if up_f.exists() else 0
        paragons.append((tid, t(tid, fallback=tid), cost))
    pdata = {tid: {"name": name, "cost": cost} for tid, name, cost in paragons}
    options = "".join(f"<option value='{tid}'>{esc(name)} (${fmt(cost)})</option>" for tid, name, cost in paragons)
    # formula constants straight from paragonDegreeData.json, so a game patch updates the calculator
    cfg = {k: d.get(k, 0) for k in ("popsOverX", "cashEarnedContributionModifier", "maxPowerFromPops", "moneySpentOverX",
                                    "paidContributionPenalty", "maxPowerFromMoneySpent", "tier5TowersMultByX",
                                    "maxPowerFromTier5Count", "nonTier5TowersMultByX", "maxPowerFromNonTier5Count",
                                    "MaxInvestment")}
    k = lambda v: f"{v / 1000:g}k"
    tiers = cfg["maxPowerFromNonTier5Count"] > 0
    return (
        f"<div class='pcalc' data-reqs='{json.dumps(req)}' data-paragons='{json.dumps(pdata)}' data-cfg='{json.dumps(cfg)}'>"
        f"<div class='pcalc-fields'>"
        f"<div class='pcalc-field' style='grid-column:1/-1'><label>Башня с парагоном<select class='pcalc-tower'>{options}</select></label></div>"
        f"<div class='pcalc-field'><label>Лопания (1 сила / {fmt(cfg['popsOverX'])})<input type='number' class='pcalc-pops' min='0' step='10000' value='0' placeholder='0'></label></div>"
        f"<div class='pcalc-field'><label>Доход ($1 дохода = {fmt(cfg['cashEarnedContributionModifier'])} лопания)<input type='number' class='pcalc-inc' min='0' step='10000' value='0' placeholder='0'></label></div>"
        f"<div class='pcalc-field'><label>Пожертвования в $<input type='number' class='pcalc-cash' min='0' step='5000' value='0' placeholder='0'></label></div>"
        f"<div class='pcalc-field'><label>Слайдер вложений ($)<input type='number' class='pcalc-slider' min='0' step='5000' value='0' placeholder='0'></label></div>"
        f"<div class='pcalc-field'><label>Доп. T5 башни (сверх 3-х)<input type='number' class='pcalc-t5' min='0' max='8' value='0'></label></div>"
        + (f"<div class='pcalc-field'><label>Тиры non-T5<input type='number' class='pcalc-tiers' min='0' value='0'></label></div>" if tiers else "") +
        f"<div class='pcalc-field' style='grid-column:1/-1'><label>Тотемы Джеральдо (+2000 силы, без потолка)<input type='number' class='pcalc-totems' min='0' max='100' value='0'></label></div>"
        f"</div>"
        f"<div class='pcalc-result'>"
        f"<div class='pcalc-badge'><span class='pcalc-deg'>1</span><span class='pcalc-deg-lbl'>Степень</span></div>"
        f"<div class='pcalc-bar-wrap'><div class='pcalc-bar' style='width:0%'></div></div>"
        f"<div class='pcalc-power'>0 / {fmt(cfg['MaxInvestment'])} силы</div>"
        f"<div class='pcalc-next'>Нужно {fmt(req[1])} силы до степени 2</div>"
        f"<div class='pcalc-breakdown'>"
        f"<div><span>Лопания:</span> <b class='pb-pops'>0 / {k(cfg['maxPowerFromPops'])}</b></div>"
        f"<div><span>Деньги:</span> <b class='pb-cash'>0 / {k(cfg['maxPowerFromMoneySpent'])}</b></div>"
        f"<div><span>Доп. T5:</span> <b class='pb-t5'>0 / {k(cfg['maxPowerFromTier5Count'])}</b></div>"
        + (f"<div><span>Тиры:</span> <b class='pb-tiers'>0 / {k(cfg['maxPowerFromNonTier5Count'])}</b></div>" if tiers else "") +
        f"<div style='grid-column:1/-1'><span>Тотемы Джеральдо:</span> <b class='pb-totems'>+0</b></div>"
        f"</div>"
        f"</div>"
        f"</div>"
        f"<p class='note'>Внешние калькуляторы: <a href='https://btd6data.com/tools/paragon' rel='noopener'>BTD6 Open Data</a>, "
        f"<a href='https://kaister300.github.io/BTD6ParagonCalculator/' rel='noopener'>BTD6 Paragon Calculator</a>.</p>"
    )


def build_paragon():
    d = load(DATA / "paragonDegreeData.json")
    req = d["powerDegreeRequirements"]
    top = req[-1]
    chart = line_chart(req, (1, 25, 50, 75, 100), "Сила по степеням", lambda v: f"{int(v) // 1000}k")

    # donut: share of each power source cap
    srcs = [("макс. от лопаний", d.get("maxPowerFromPops", 0)), ("макс. от денег", d.get("maxPowerFromMoneySpent", 0)),
            ("макс. от T5", d.get("maxPowerFromTier5Count", 0))]
    total = sum(v for _, v in srcs)
    R, SW, C = 70, 26, 2 * math.pi * 70
    segs, acc = [], 0.0
    for i, (lbl, v) in enumerate(srcs):
        length = C * v / total
        segs.append(f"<circle class='seg s{i + 1}' r='{R}' cx='100' cy='100' stroke-width='{SW}' "
                    f"stroke-dasharray='{max(length - 3, 0):.2f} {C:.2f}' stroke-dashoffset='{-acc:.2f}'>"
                    f"<title>{esc(lbl)}: {fmt(v)} ({v / total * 100:.1f}%)</title></circle>")
        acc += length
    legend = "".join(f"<li><i class='sw s{i + 1}'></i><span>{esc(lbl)}</span><b>{fmt(v)}</b><small>{v / total * 100:.1f}%</small></li>"
                     for i, (lbl, v) in enumerate(srcs))
    donut = (f"<div class='donut-row'><svg class='donut' viewBox='0 0 200 200' width='200' height='200' role='img' "
             f"aria-label='Потолки силы по источникам'><g transform='rotate(-90 100 100)'>{''.join(segs)}</g>"
             f"<text x='100' y='98' text-anchor='middle' class='dc-v'>{fmt(total)}</text>"
             f"<text x='100' y='118' text-anchor='middle' class='dc-l'>сумма потолков</text></svg>"
             f"<div><ul class='legend'>{legend}</ul><p class='note'>Для 100-й степени нужно {fmt(top)} силы, "
             f"а сумма потолков этих источников {fmt(total)}. Ни один из них в одиночку до {fmt(top)} не доходит.</p></div></div>")
    rows = [(i + 1, p, p - req[i - 1] if i else 0) for i, p in enumerate(req)]
    fields = [
        ("maxPowerFromPops", "Потолок силы от лопаний"),
        ("popsOverX", "Делитель лопаний (лопаний на 1 силу)"),
        ("maxPowerFromMoneySpent", "Потолок силы от потраченных денег"),
        ("moneySpentOverX", "Параметр формулы денег"),
        ("maxPowerFromTier5Count", "Потолок силы от башен 5-го тира"),
        ("tier5TowersMultByX", "Сила за одну башню 5-го тира"),
        ("maxPowerFromNonTier5Count", "Потолок силы от остальных улучшений"),
        ("nonTier5TowersMultByX", "Множитель за остальные улучшения"),
        ("cashEarnedContributionModifier", "Модификатор вклада заработанных денег"),
        ("paidContributionPenalty", "Штраф вклада оплаченных денег"),
        ("MaxInvestment", "Максимум вложений"),
        ("damageIncreasePerDegree", "Урон за степень"),
        ("damageIncreaseForDegrees", "…каждые N степеней"),
        ("damagePercentPerDegree", "Урон, % за степень"),
        ("pierceIncreasePerDegree", "Пробивание за степень"),
        ("piercePercentPerDegree", "Пробивание, % за степень"),
        ("attackCooldownReductionX", "Параметр ускорения атаки"),
        ("bonusBossDamagePercent", "Доп. урон по боссам"),
        ("bonusBossDamagePerDegrees", "…каждые N степеней"),
        ("degreeCount", "Число степеней"),
    ]
    frows = [(f"<span class='id'>{esc(k)}</span>", esc(name), d[k]) for k, name in fields if k in d]
    body = (
        stats([("степеней", d.get("degreeCount")), ("сила для 100", top)])
        + card("calc", "Калькулятор степени", paragon_calc(req, d), section="Парагон")
        + card("pie", "Откуда берётся сила", donut, section="Парагон")
        + card("towers", "Башни с парагоном", "<div class='chips'>" + " ".join(
            f"<a class='badge' href='tower-{p.parent.name}.html#crosspath'><span>парагон</span><b>{icon('towers', p.parent.name, 18)}"
            f"{esc(t(p.parent.name, fallback=p.parent.name))}</b></a>" for p in sorted((DATA / "Towers").glob("*/*-Paragon.json")))
            + "</div>", section="Парагон")
        + card("curve", "Сколько силы нужно на степень",
               chart + "<p class='note'>Прирост между соседними степенями растёт, поэтому последние степени самые дорогие.</p>"
               "<details><summary>Таблица всех 100 степеней</summary>"
               + table(["Степень", "Сила", "Прирост"], rows) + "</details>", section="Парагон")
        + card("sources", "Параметры модели парагона",
               "<p class='note'>Значения взяты как есть. Русские подписи сделаны по названиям полей, точную формулу "
               "игра в данных не хранит.</p>" + table(["Поле", "Смысл", "Значение"], frows), section="Парагон"))
    page("paragon.html", "Парагон",
         "Степень парагона от 1 до 100 зависит от силы. Сила копится от лопаний, потраченных денег "
         "и пожертвованных улучшений, у каждого источника свой потолок.",
         body, toc=[("calc", "Калькулятор степени"), ("pie", "Откуда берётся сила"), ("towers", "Башни с парагоном"), ("curve", "Сила на степень"), ("sources", "Параметры")])


def skulls(boss_model):
    """HP fractions where the boss triggers its skull actions (multi-step health triggers)."""
    out = set()
    for beh in boss_model.get("behaviors") or []:
        if not isinstance(beh, dict):
            continue
        vals = beh.get("percentageValues") or beh.get("etherealHealthPercentageValues") or []
        if "HealthPercentTrigger" in beh.get("$type", "") and (len(vals) < 2 or beh.get("repeatFirst")):
            continue
        out.update(v for v in vals if isinstance(v, (int, float)) and 0 < v < 1)
    return sorted(out, reverse=True)


def plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many



def hp_row(elite, n, b, top):
    sk = skulls(b)
    width = 100 * math.log10(b["maxHealth"]) / math.log10(top)
    ticks = "".join(f"<span class='skull' style='left:{v * 100:.2f}%' title='{v * 100:g}%'></span>" for v in sk)
    cls = "e" if elite else "n"
    return (f"<span class='t {cls}'>{'E' if elite else 'T'}{n}</span>"
            f"<span class='bar {cls}' style='width:{width:.1f}%'><span class='fill' style='width:100%'></span>{ticks}</span>"
            f"<span class='v'>{fmt(b['maxHealth'])}<small>{len(sk)} {plural(len(sk), 'череп', 'черепа', 'черепов')}</small></span>")


def build_bosses():
    body, toc = [], []
    for boss in sorted(p.stem for p in json_files("Bosses")):
        tiers = []
        for f in sorted((DATA / "Bloons" / boss).glob("*.json")):
            m = re.fullmatch(rf"{boss}(Elite)?(\d)", f.stem)
            if m:
                tiers.append((bool(m.group(1)), int(m.group(2)), load(f)))
        if not tiers:
            continue
        tiers.sort(key=lambda x: (x[0], x[1]))
        name = t(boss, fallback=boss)
        top = max(b["maxHealth"] for _, _, b in tiers)
        bars = "".join(hp_row(e, n, b, top) for e, n, b in tiers)
        # parameters per tier: which numbers change, which stay the same
        flats = [flatten(b) for _, _, b in tiers]
        keys = list(dict.fromkeys(k for fl in flats for k in fl))
        heads = ["Параметр"] + [f"{'E' if e else 'T'}{n}" for e, n, _ in tiers]
        varying, constant = [], []
        for k in keys:
            vals = [fl.get(k) for fl in flats]
            if len({json.dumps(v) for v in vals}) > 1:
                varying.append([f"<span class='id'>{esc(k)}</span>"] + vals)
            else:
                constant.append((k, vals[0]))
        normal = next(b for e, n, b in tiers if not e and n == 1)
        mechanics = sorted({label(short_type(x)) for x in normal.get("behaviors") or []
                            if isinstance(x, dict) and not skipped(x)})
        inner = (
            "<div class='split'><div><div class='hero-row'>" + icon("ui", f"boss-{boss}", 104, "ic mode-ic") + "<div>"
            + game_text(t(f"{boss}InfoPanelDescription")) + "</div></div>"
            + stats([("HP T1", normal["maxHealth"]), ("HP элит. T5", top), ("скорость T1", normal["speed"]),
                     ("скорость элит. T5", tiers[-1][2]["speed"])])
            + "<h3>Поведения</h3><div class='chips'>" + "".join(f"<span class='chip'>{esc(m)}</span>" for m in mechanics) + "</div>"
            + "</div><div>"
            + "<h3>HP и черепа по тирам</h3><p class='note'>T обычный, E элитный. Засечки на полосе это черепа: "
              "пороги HP, на которых босс применяет способность. Длина полосы показывает HP тира относительно "
              "самого крепкого, в логарифмической шкале.</p>"
            + f"<div class='hp'>{bars}</div></div></div>"
            + f"<h3>Что меняется по тирам ({len(varying)})</h3>" + table(heads, varying)
            + f"<details><summary>Одинаково на всех тирах ({len(constant)})</summary>{kv_table(constant)}</details>")
        tagline = " ".join(x for x in (t(f"{boss}TagLine"), t(f"{boss}TagLine2")) if x)
        body.append(card(boss, name, inner, en_id=boss, tagline=tagline, section="Боссы"))
        toc.append((boss, name))
    page("bosses.html", "Боссы",
         "5 обычных и 5 элитных тиров. HP по тирам и параметры, которые растут с тиром.",
         "".join(body), toc)
