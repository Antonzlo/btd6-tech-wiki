"""XP page: round XP, freeplay reduction, co-op split, ranks.

Numbers come from the dump: xp.json (GetXpForRound and the map scales), rank-xp.json (RankInfo from the game data
bundle), the modes' EndRoundModModel and the XP knowledge. The rules around them come from reading the game code
(GameAssembly.dll 57.4, notes in ../coop-xp-evidence.md) and are written here by hand."""
from wiki.core import DATA, card, esc, fmt, load, page, short_type, t, table
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


def freeplay_award(award, round_, end):
    adjusted = award * freeplay(round_, end)
    return min(adjusted, 3000) if round_ > max(end, 100) else adjusted


def build_xp():
    xp = load(DATA / "KnowledgeLayout" / "xp.json")
    base, scales = xp["heroXpPerRound"], xp["trackDifficultyXpScale"]
    ranks = load(DATA / "KnowledgeLayout" / "rank-xp.json")
    need, veteran = ranks["totalXpNeeded"], ranks["xpNeededPerVeteranRank"]
    education = load(DATA / "Knowledge" / "Support" / "MonkeyEducation.json")["mod"]["mutatorMods"]
    training = load(DATA / "Knowledge" / "Military" / "EliteMilitaryTraining.json")["mod"]["mutatorMods"]
    purchase = next(m for m in training if short_type(m) == "OnMonkeyKnowledgePurchaseModModel")
    purchase_towers = [tower.strip() for tower in purchase["towers"].split(",") if tower.strip()]
    purchase_names = ", ".join(esc(t(tower, fallback=tower)) for tower in purchase_towers)
    base_models = {
        folder.name: load(folder / f"{folder.name}.json")
        for folder in sorted((DATA / "Towers").iterdir())
        if (folder / f"{folder.name}.json").is_file()
    }
    model_mods = {tower: {mod["mod"] for mod in data.get("mods") or [] if short_type(mod) == "ApplyModModel"}
                  for tower, data in base_models.items()}
    training_names = ", ".join(esc(t(tower, fallback=tower)) for tower, mods in model_mods.items()
                               if "EliteMilitaryTraining" in mods)

    round_rows = [[r] + [base[r - 1] * s for s in scales.values()] for r in ROUNDS if r <= len(base)]
    round_card = card("round", "Опыт за раунд",
                      "<p>Формула из кода игры (Simulation.GetXpForRound): <code>20 × (r + 2 + max(0, r − 19)) + 50 × max(0, r − 49)</code>, "
                      "где r = номер раунда − 1. Потом множитель сложности карты. Числа ниже из выгрузки, они совпадают с формулой.</p>"
                      + table(["Раунд"] + list(scales), round_rows)
                      + "<p class='note'>Перед коэффициентом карты игра применяет рейтинг сложности матча (selectedDifficultyRating). "
                      "GameModel начинает с рейтинга 1. Модификатор SelectedDifficultyRating умножает текущий рейтинг "
                      "и затем прибавляет поправку. Итоговых значений по режимам в выгрузке нет. "
                      "Режим Rogue Legends даёт ×3.</p>", section="Опыт")

    bosses_card = card("bosses", "Опыт за боссов",
                       "<p>Победа над боссом не даёт отдельного опыта аккаунта или башен. "
                       "Начисление за завершённый раунд зависит от режима.</p>"
                       + table(["Где находится босс", "Опыт аккаунта и башен за раунд"], [
                           ["Официальный Boss Event или встроенный Boss Challenge", "Да, если матч допускает начисление опыта"],
                           ["Boss Rush", "Да, если матч допускает начисление опыта. Множитель ×0,2 до поправки за фриплей"],
                           ["Пользовательское испытание, карта или игра", "Нет"],
                           ["Сторонний мод с боссом", "Зависит от режима и правил мода. Требует отдельной проверки"],
                       ])
                       + "<p class='note'>Проверено по данным и коду версии 57.4. Это правила обычного XP за раунды; "
                       "награды за завершение события считаются отдельно.</p>", section="Опыт")

    beginner = scales["Beginner"]
    mode_ends = end_rounds()
    fp_rows = []
    for mode, end in mode_ends:
        first = end + 1
        multiplier = freeplay(first, end)
        award = "–"
        if end < len(base):
            award = round(freeplay_award(base[end] * beginner, first, end), 2)
        fp_rows.append([mode_name(mode), end, first, multiplier, award])
    ends = dict(mode_ends)
    boundary_rows = [[r, *(round(freeplay_award(base[r - 1] * beginner, r, ends[mode]), 2)
                           for mode in ("Hard", "Clicks"))] for r in (99, 100, 101)]
    intermediate_award = freeplay_award(base[100] * scales["Intermediate"], 101, ends["Hard"])
    fp_card = card("freeplay", "Опыт во фриплее",
                   "<p>После последнего раунда режима опыт аккаунта и башен умножается на 0,3, после раунда 100 на 0,1 "
                   "и не больше 3000 за раунд. Опыт героя не уменьшается. Раунд, на котором режим заканчивается, даёт полный опыт.</p>"
                   + table(["Режим", "Последний раунд", "Первый сниженный", "Множитель", "Опыт за него, карта Beginner"], fp_rows)
                   + "<p>Пример для карты Beginner с рейтингом сложности 1. Каждый игрок получает указанное число XP аккаунта. "
                   "Для башен это общая база, к которой применяются доли вложений и бонусы знаний.</p>"
                   + table(["Раунд", "XP в Hard Standard", "XP в CHIMPS"], boundary_rows),
                   section="Опыт")

    edu, emt = (next(m["multiplier"] for m in mods if short_type(m) == "TowerXpModModel")
                for mods in (education, training))
    both = (1 + edu) * (1 + emt)
    coop_round_xp = base[19] * beginner
    coop_rows = [[n, coop_round_xp, coop_round_xp / n, coop_round_xp / n * both] for n in (2, 3, 4)]
    spending_towers = ("DartMonkey", "TackShooter", "SniperMonkey", "BoomerangMonkey")
    spending_rows = []
    for players in (2, 3, 4):
        weights = [base_models[tower]["cost"] for tower in spending_towers[:players]]
        total = sum(weights)
        spending_rows.append([players, " / ".join(map(fmt, weights)), coop_round_xp,
                              " / ".join(fmt(coop_round_xp * weight / total) for weight in weights)])
    example_towers = [(1, "DartMonkey"), (1, "TackShooter"), (2, "SniperMonkey")]
    purchases = [(player, tower, base_models[tower]["cost"])
                 for player, tower in example_towers]
    team_cost = sum(cost for _, _, cost in purchases)
    tower_rows = []
    for player, tower, cost in purchases:
        award = coop_round_xp * cost / team_cost
        boosted = award
        for knowledge, bonus in (("MonkeyEducation", edu), ("EliteMilitaryTraining", emt)):
            if knowledge in model_mods[tower]:
                boosted *= 1 + bonus
        tower_rows.append([player, t(tower, fallback=tower), cost, award, boosted])
    frontier_tower = load(DATA / "Towers" / "DartMonkey" / "DartMonkey-100.json")
    frontier_upgrade_cost = sum(load(DATA / "Upgrades" / f"{name}.json")["cost"]
                                for name in frontier_tower["appliedUpgrades"])
    frontier_weight = frontier_tower["cost"] + frontier_upgrade_cost
    cape = load(DATA / "GeraldoItems" / "WornHerosCape.json")
    dart_cost = base_models["DartMonkey"]["cost"]
    dart_paragon = load(DATA / "Upgrades" / "DartMonkey Paragon.json")
    coop_card = card("coop", "Опыт в коопе",
                     "<p><b>Опыт аккаунта</b> каждый игрок получает полностью, без деления на число игроков. "
                     "Профиль сохраняет дробную часть. Например, на раунде 101 во фриплее Hard Standard "
                     f"на карте Intermediate с рейтингом 1 каждый игрок получает около {fmt(intermediate_award)} XP.</p>"
                     "<p><b>Опыт башен</b> для каждой башни равен опыту раунда, умноженному на долю её стоимости "
                     "в суммарной стоимости всех учитываемых башен команды. "
                     "Если башню продали или уничтожили при создании парагона до начисления XP за раунд, "
                     "она перестаёт участвовать в расчёте как отдельная башня. "
                     "В обычных режимах вес башни складывается из цены размещения и цен купленных улучшений с учётом обычных скидок. "
                     "Бесплатное размещение и размещение Insta-Monkey дают нулевой начальный вес. "
                     "Из расчёта исключаются герои, подбашни, башни-силы и предметы Geraldo. "
                     "Во Frontier вес равен сумме цен из моделей башни и её установленных улучшений. "
                     f"Например, для Dart Monkey 1-0-0 выгрузка даёт вес {fmt(frontier_tower['cost'])} "
                     f"+ {fmt(frontier_upgrade_cost)} = {fmt(frontier_weight)}.</p>"
                     "Дробный опыт сохраняется, не округляется. Опыт идёт по типу башни: все улучшения одной башни копят один опыт. "
                     "Если общая учитываемая стоимость равна нулю, игроки всё равно получают опыт аккаунта, а башням опыт не начисляется. "
                     "После окончательного удаления игрока из матча игра перестаёт начислять ему XP за раунды. "
                     "Переданные другим игрокам башни дальше копят опыт новым владельцам.</p>"
                     "<p>При временном обрыве связи симуляция продолжает считать XP за завершённые раунды для игрока, "
                     "пока его запись остаётся в матче. При пересинхронизации снимок карты переносит баланс игрока. "
                     "В сохранённых данных игрока нет накопленного XP. Загрузка снимка возобновляет игру с раунда "
                     "после последнего завершённого и сама не начисляет XP за пропущенные раунды.</p>"
                     "<p>В обычном расчёте по стоимости есть отдельное правило Monkeyopolis: "
                     "игра прибавляет к весу деревни стоимость каждой поглощённой фермы, усечённую до целого. "
                     "Поглощаются подходящие фермы того же владельца. После удаления фермы её вес участвует "
                     "в XP деревни, а не отдельной фермы. Во Frontier применяется описанный выше расчёт по ценам моделей.</p>"
                     "<p>Worn Hero’s Cape задаёт вес новой башни как вес исходной Dart Monkey плюс стоимость плаща "
                     "из применённой модели предмета Geraldo. Это замена веса, а не добавление полной цены Super Monkey. "
                     f"Пример с ценами базовых дампов: {fmt(dart_cost)} + {fmt(cape['cost'])} = {fmt(dart_cost + cape['cost'])}.</p>"
                     "<p>При покупке парагона игра прибавляет рассчитанную цену улучшения к текущему весу выбранной башни. "
                     "Дополнительный денежный взнос влияет на списание денег и степень парагона. "
                     f"Базовая цена улучшения Dart Monkey из дампа составляет ${fmt(dart_paragon['cost'])}. "
                     f"Для разблокировки требуется {fmt(dart_paragon['xpCost'])} XP башни.</p>"
                     f"<p><b>Бонусы знаний</b> к опыту башен перемножаются: {t('MonkeyEducation', fallback='MonkeyEducation')} "
                     f"{1 + edu:g} × {t('EliteMilitaryTraining', fallback='EliteMilitaryTraining')} {1 + emt:g} = {both:g}. "
                     "Кооп объединяет изученные знания всех игроков с включённым Monkey Knowledge. "
                     "Каждое знание применяется один раз. В CHIMPS и испытаниях с флагом disableMK "
                     "знания из профилей не применяются.</p>"
                     f"<p>При покупке {esc(t('EliteMilitaryTraining', fallback='EliteMilitaryTraining'))} "
                     f"профиль разово получает по {fmt(purchase['xpToAdd'])} опыта для каждой из этих башен "
                     f"({purchase_names}). Эта награда не делится между участниками коопа.</p>"
                     f"<p>Ссылку на бонус Elite Military Training за раунд содержат базовые модели следующих башен из дампа "
                     f"({training_names}). В выгрузке улучшения, включая парагонов, сохраняют те же ссылки на "
                     "XP-бонусы знаний, что и базовая башня. Бонус применяется при активном знании в матче.</p>"
                     + table(["Игроков", "Опыт аккаунта каждому", "Опыт башен игрока", "С обоими бонусами"], coop_rows)
                     + "<p class='note'>Раунд 20, карта Beginner, рейтинг сложности 1. Вложения игроков равны. "
                     "Последняя колонка предполагает, что оба бонуса действуют на все учитываемые башни игрока.</p>"
                     "<p>На том же раунде каждый игрок поставил по одной башне без скидок. В порядке игроков "
                     "это Dart Monkey, Tack Shooter, Sniper Monkey и Boomerang Monkey в зависимости от размера команды. "
                     "Цены взяты из выгрузки. Бонусы знаний в этом примере отключены.</p>"
                     + table(["Игроков", "Вложения по игрокам, $", "XP аккаунта каждому", "XP башен по игрокам"],
                             spending_rows)
                     + f"<p>Если в коопе на двоих игроки заплатили цены из дампа без скидок, в этом примере "
                     f"общая стоимость башен составляет ${fmt(team_cost)}. У игрока 1 опыт зачисляется "
                     "отдельно для Dart Monkey и Tack Shooter. Последняя колонка учитывает ссылки на Monkey Education "
                     "и Elite Military Training в моделях этих башен при обоих активных знаниях.</p>"
                     + table(["Игрок", "Тип башни", "Уплаченная цена, $", "XP без знаний", "XP с указанными знаниями"],
                             tower_rows)
                     + "<p class='note'>Перенос стоимости поглощённых башен в XP-вес парагона пока не подтверждён. "
                     "Приведённое правило исключения относится к самим уничтоженным башням.</p>", section="Опыт")

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
         round_card + bosses_card + fp_card + coop_card + gate_card + rank_card,
         [("round", "Опыт за раунд"), ("bosses", "Опыт за боссов"), ("freeplay", "Опыт во фриплее"), ("coop", "Опыт в коопе"),
          ("none", "Где опыта нет"), ("ranks", "Уровни аккаунта")])
