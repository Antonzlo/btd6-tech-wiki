"""XP page: round XP, freeplay reduction, co-op split, ranks.

Numbers come from the dump: xp.json (GetXpForRound and the map scales), rank-xp.json (RankInfo from the game data
bundle), the modes' EndRoundModModel and the XP knowledge. The rules around them come from reading the game code
(GameAssembly.dll 57.4, notes in ../coop-xp-evidence.md) and are written here by hand."""
from wiki.core import DATA, card, fmt, load, page, short_type, t, table
from wiki.modes import mode_name

ROUNDS = (1, 10, 20, 21, 40, 41, 50, 51, 60, 61, 80, 81, 100, 101, 120, 140)


def end_rounds():
    """Mode -> last round, from the modes that set one themselves."""
    out = {}
    for f in sorted((DATA / "Mods").glob("*.json")):
        for m in load(f).get("mutatorMods", []):
            if short_type(m) == "EndRoundModModel" and f.stem != "Tutorial":
                out[f.stem] = m["round"]
    return sorted(out.items(), key=lambda kv: (kv[1], kv[0]))


def freeplay(round_, end):
    """Multiplier on account and tower XP for a displayed round (Simulation.DistributeXp, 0xB45E45)."""
    if round_ <= end:
        return 1
    return 0.3 if round_ <= 100 else 0.1


def build_xp():
    xp = load(DATA / "KnowledgeLayout" / "xp.json")
    base, scales = xp["heroXpPerRound"], xp["trackDifficultyXpScale"]
    ranks = load(DATA / "KnowledgeLayout" / "rank-xp.json")
    need, veteran = ranks["totalXpNeeded"], ranks["xpNeededPerVeteranRank"]
    bonus = {k: next(m["multiplier"] for m in load(f)["mod"]["mutatorMods"] if short_type(m) == "TowerXpModModel")
             for k, f in (("MonkeyEducation", DATA / "Knowledge" / "Support" / "MonkeyEducation.json"),
                          ("EliteMilitaryTraining", DATA / "Knowledge" / "Military" / "EliteMilitaryTraining.json"))}

    round_rows = [[r] + [base[r - 1] * s for s in scales.values()] for r in ROUNDS if r <= len(base)]
    round_card = card("round", "Опыт за раунд",
                      "<p>Формула из кода игры (Simulation.GetXpForRound): <code>20 × (r + 2 + max(0, r − 19)) + 50 × max(0, r − 49)</code>, "
                      "где r = номер раунда − 1. Потом множитель сложности карты. Числа ниже из выгрузки, они совпадают с формулой.</p>"
                      + table(["Раунд"] + list(scales), round_rows)
                      + "<p class='note'>Перед картой опыт умножается на рейтинг сложности матча (selectedDifficultyRating), "
                      "его значений в выгрузке нет. Режим BossRush даёт ×0,2, Rogue Legends ×3.</p>", section="Опыт")

    fp_rows = [[mode_name(m), e, e + 1, freeplay(e + 1, e), round(base[e] * freeplay(e + 1, e), 2) if e < len(base) else "–"]
               for m, e in end_rounds()]
    fp_card = card("freeplay", "Опыт во фриплее",
                   "<p>После последнего раунда режима опыт аккаунта и башен умножается на 0,3, после раунда 100 на 0,1 "
                   "и не больше 3000 за раунд. Опыт героя не уменьшается. Раунд, на котором режим заканчивается, даёт полный опыт.</p>"
                   + table(["Режим", "Последний раунд", "Первый сниженный", "Множитель", "Опыт за него, карта Beginner"], fp_rows),
                   section="Опыт")

    edu, emt = bonus["MonkeyEducation"], bonus["EliteMilitaryTraining"]
    both = (1 + edu) * (1 + emt)
    coop_rows = [[n, base[19], base[19] / n, base[19] / n * both] for n in (1, 2, 3, 4)]
    coop_card = card("coop", "Опыт в коопе",
                     "<p><b>Опыт аккаунта</b> каждый игрок получает полностью, без деления на число игроков.</p>"
                     "<p><b>Опыт башен</b>: опыт раунда × (сколько стоила башня / сколько вся команда потратила на такие башни). "
                     "Считается цена, которую заплатили, со скидками. Не считаются герои, подбашни, башни-силы и предметы Geraldo, "
                     "бесплатные и insta-башни добавляют 0. Во Frontier считается полная цена башни и её улучшений. "
                     "Дробный опыт сохраняется, не округляется. Опыт идёт по типу башни: все улучшения одной башни копят один опыт. "
                     "Если игрок вышел, его башни переходят другим и дальше копят опыт новому владельцу.</p>"
                     f"<p><b>Бонусы знаний</b> к опыту башен перемножаются: {t('MonkeyEducation', fallback='MonkeyEducation')} "
                     f"{1 + edu:g} × {t('EliteMilitaryTraining', fallback='EliteMilitaryTraining')} {1 + emt:g} = {both:g}. "
                     "Какие знания игроков работают в коопе, в коде ещё не прослежено.</p>"
                     + table(["Игроков", "Опыт аккаунта каждому", "Опыт башен игрока", "С обоими бонусами"], coop_rows)
                     + "<p class='note'>Раунд 20, карта Beginner, все тратят на башни поровну.</p>", section="Опыт")

    gate_card = card("none", "Где опыта нет",
                     "<ul><li>Песочница, редактор карт и редактор игр.</li>"
                     "<li>Продвинутые испытания (Advanced), Contested Territory в гонке.</li>"
                     "<li>Игра в чужие испытания, одиссеи, карты и игры, созданные игроками, и их создание.</li>"
                     "<li>Режим зрителя.</li>"
                     "<li>Испытания с флагом disableTowerXp: несмотря на имя, он отключает и опыт аккаунта.</li></ul>",
                     section="Опыт")

    rank_rows = [[i + 1, need[i] - need[i - 1] if i else 0, need[i]] for i in range(len(need))]
    rank_card = card("ranks", "Уровни аккаунта",
                     f"<p>Уровней: {len(need)}, последний на {fmt(need[-1])} опыта. Дальше уровень ветерана каждые {fmt(veteran)} опыта: "
                     "опыт сверх последнего уровня идёт в опыт ветерана.</p>"
                     + table(["Уровень", "Опыт до уровня", "Опыт всего"], rank_rows), section="Опыт")

    page("xp.html", "Опыт", "Сколько опыта даёт раунд, как он делится в коопе и сколько нужно до уровня аккаунта.",
         round_card + fp_card + coop_card + gate_card + rank_card,
         [("round", "Опыт за раунд"), ("freeplay", "Опыт во фриплее"), ("coop", "Опыт в коопе"),
          ("none", "Где опыта нет"), ("ranks", "Уровни аккаунта")])
