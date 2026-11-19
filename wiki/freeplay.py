"""Freeplay page: how bloons get tougher after the last round of a mode.

data/KnowledgeLayout/freeplay.json comes from the dumper (Ctrl+Shift+F6): the thresholds of
ProgressiveDifficultyManager and the game's own GetHealthMultiplier / GetSpeedMultiplier / GetStunResistance for
rounds 1 to 1000 (list index 0 is round 1).
"""
from wiki.core import DATA, card, fmt, load, page, stats, table
from wiki.charts import dual_line_chart

FREEPLAY = DATA / "KnowledgeLayout" / "freeplay.json"
SAMPLE_ROUNDS = (81, 90, 100, 101, 120, 125, 150, 151, 200, 201, 250, 251, 252, 300, 350, 400, 500, 750, 1000)
CHART_END = 400


def pct(v):
    return f"+{v * 100:g}%"


def steps(pairs, start_text):
    """[[round, per-round increase], ...] as table rows: from round, increase per round."""
    return [[f"{start_text} {int(r)}", pct(v)] for r, v in pairs if r]


def build_freeplay():
    if not FREEPLAY.exists():
        page("freeplay.html", "Фриплей", "Нет данных: запустите KnowledgeDumper (Ctrl+Shift+F6).", "")
        return
    fp = load(FREEPLAY)
    hp, speed, stun = fp["healthMultiplierPerRound"], fp["speedMultiplierPerRound"], fp["stunResistancePerRound"]
    x = lambda v: f"×{fmt(round(v, 2))}"

    top = stats([("начало", fp["fromRound"]), ("в Rogue Legends", fp["fromRoundRogue"]),
                 (f"HP на {len(hp)}", x(hp[-1])), (f"скорость на {len(speed)}", x(speed[-1]))])
    chart = dual_line_chart(hp[:CHART_END], speed[:CHART_END], (1, 81, 100, 150, 200, 250, 300, 400),
                            f"Фриплей 1–{CHART_END}", x, x,
                            lambda r, h, s: f"Раунд {r}: HP {x(h)} · скорость {x(s)}",
                            legend=("HP (слева)", "Скорость (справа)"))
    intro = card("growth", "Рост по раундам",
                 "<p>Множители от функций самой игры (<code>ProgressiveDifficultyManager</code>), по номеру раунда "
                 "на экране. До раунда "
                 f"{fp['fromRound'] - 1} всё ×1. К каким шарам игра их применяет, по коду не проверено: по "
                 "наблюдениям игроков, HP растёт у MOAB-класса, а скорость у всех шаров.</p>" + top + chart,
                 section="Фриплей")

    rows = [[r, x(hp[r - 1]), x(speed[r - 1]), f"{stun[r - 1] * 100:g}%"] for r in SAMPLE_ROUNDS if r <= len(hp)]
    lookup = card("rounds", "Множители на раундах",
                  table(["Раунд", "HP", "Скорость", "Сопротивление оглушению"], rows), section="Фриплей")

    hp_rows = steps(fp["roundBasedHealthIncrease"], "с раунда")
    speed_rows = steps(fp["roundBasedSpeedIncrease"], "с раунда")
    jumps = [[int(r), pct(v)] for r, v in fp["bonusSpeedIncreaseRounds"]]
    jumps += [[int(r), pct(v) + " HP"] for r, v in fp["bonusHealthIncreaseRounds"]]
    stun_rows, prev = [], 0
    for r, v in enumerate(stun, 1):
        if v != prev:
            stun_rows.append([f"с раунда {r}", f"{v * 100:g}%"])
            prev = v
    rules = card("rules", "Правила роста",
                 "<p>Каждый раунд множитель растёт на прибавку текущей ступени. Скачки добавляются один раз, "
                 "на своём раунде.</p>"
                 + "<h3>HP за раунд</h3>" + table(["Раунды", "Прибавка"], hp_rows)
                 + "<h3>Скорость за раунд</h3>" + table(["Раунды", "Прибавка"], speed_rows)
                 + "<h3>Разовые скачки скорости</h3>" + table(["Раунд", "Прибавка"], jumps)
                 + "<h3>Сопротивление оглушению</h3>" + table(["Раунды", "Сопротивление"], stun_rows)
                 + f"<p class='note'>Предел роста HP в данных игры: <code>healthIncreaseMax</code> = "
                 f"{fmt(fp['healthIncreaseMax'])}. Опыт во фриплее: <a href='xp.html#freeplay'>страница опыта</a>.</p>",
                 section="Фриплей")

    page("freeplay.html", "Фриплей",
         f"После последнего раунда режима шары становятся крепче и быстрее. Данные игры {fp['version']}.",
         f"<div class='cards'>{intro}{lookup}{rules}</div>",
         [("growth", "Рост по раундам"), ("rounds", "Множители на раундах"), ("rules", "Правила роста")])
