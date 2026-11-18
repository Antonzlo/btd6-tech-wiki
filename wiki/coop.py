"""Co-op money page: where cash comes from and whether co-op splits it between players.

Model flags from the export decide it where a model has one (distributeCash, distributeBonusIncome). The general
rules come from reading the game code (GameAssembly.dll 57.4, notes in ../coop-xp-evidence.md): the code is not in the
export, so they are written here by hand; a source with neither shows "not checked"."""
import re

from wiki.buffs import EFFECT_RU, effect_line
from wiki.core import DATA, Raw, card, esc, fmt, icon, label, load, page, short_type, t, table
from wiki.place import tier_key

# model types that bring cash in (not ones that only show it, collect it or scale damage by it)
INCOME_RU = {
    "PerRoundCashBonusTowerModel": "Деньги в конце раунда", "CashModel": "Подбираемые деньги (бананы, ящики)",
    "BankModel": "Банк", "ImfLoanModel": "Займ IMF", "CashPerTowerInRangeModel": "Деньги за башни в радиусе",
    "GiveCashOnPopModel": "Деньги за лопание", "CashbackZoneModel": "Возврат денег при покупке",
    "BonusCashZoneModel": "Бонус к деньгам в зоне", "CashIncreaseModel": "Больше денег за лопание",
    "MonkeyCityIncomeSupportModel": "Больше денег за лопание (город)", "BananaCashIncreaseSupportModel": "Больше денег с бананов",
    "BountyHunterZoneModel": "Награда за шары", "AddCashOnProjectileExpireModel": "Деньги по истечении снаряда",
    "CashPerTowerInMakeshiftAreaModel": "Деньги за башни на площадке", "MonkeyBankerModel": "Доход банков",
    "EatBloonModel": "Бонус ловушки", "WallOfTreesModel": "Бонус Wall of Trees",
    "ThriveModel": "Бонус к доходу за шары",
    "BananaCentralBuffModel": "Доход Banana Research Facility",
}
CAPTURE_BONUSES = {"EatBloonModel", "WallOfTreesModel"}
SPLIT, OWNER, UNKNOWN = "делится на всех", "владельцу башни", "не проверено"


def verdict(m, pickup=False, instant_expiry=False):
    """Who gets this cash in co-op, from the model's own flags; game code: PerRoundCashBonusTower.OnRoundComplete
    (distributeCash: AddSharedCash, else AddCash to the owner) and Cash.Pickup. Pickup looks for a Pickup behavior
    on the same projectile (pickup: a PickupModel sits next to the CashModel): the share emittedByCashEarnedMultiplier
    goes to Pickup.Owner.PlayerOwnerId, the owner of the emitting tower, whoever collects it; the rest is shared when
    distributeBonusIncome, else it goes to the owner too. Automatic farm cash with an immediate expiry uses
    Cash.Exhausted and follows distributeSalvage instead."""
    k = short_type(m)
    if k == "ThriveModel":
        return SPLIT
    if k == "BananaCentralBuffModel":
        return "владельцу фермы, получившей бонус"
    if k == "BananaCashIncreaseSupportModel" and m.get("mutatorId") == "BankHack:Regular":
        return "владельцу банка при сборе"
    if k in ("BankModel", "ImfLoanModel", "GiveCashOnPopModel"):
        return OWNER
    if k == "PerRoundCashBonusTowerModel":
        return SPLIT if m.get("distributeCash") else OWNER
    if k in CAPTURE_BONUSES:
        behaviors = (m.get("projectile") or {}).get("behaviors") or []
        cash = next((b for b in behaviors if short_type(b) == "CashModel"), None)
        has_pickup = any(short_type(b) == "PickupModel" for b in behaviors)
        return verdict(cash, has_pickup) if cash else UNKNOWN
    if (k == "CashModel" and instant_expiry and not pickup
            and m.get("distributeSalvage") is False and m.get("salvage", 0) > 0):
        return OWNER
    if k == "CashModel" and pickup:
        share = m.get("emittedByCashEarnedMultiplier", 1)
        if share >= 1 or not m.get("distributeBonusIncome"):
            return OWNER
        return f"{share * 100:g}% владельцу башни, остальное делится на всех"
    return UNKNOWN


def model_name(m):
    """The model's own name without its type prefix and tier suffix: two models of one type stay apart
    (Alchemist: LeadToGold and RubberToGold are both GiveCashOnPopModel), one model across tiers stays together."""
    n = re.sub(r"_?[A-Za-z]+-(\d{3}|Paragon)_?$", "", m.get("name") or "")
    n = n.removeprefix(short_type(m)).strip("_")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)


def sources():
    """Group each unit's income behaviors by model and payout parameters, lowest tier first."""
    out = {}
    folders = [("towers", "Towers"), ("heroes", "Heroes"), ("powers", "Powers"), ("geraldo", "GeraldoItems")]
    for kind, folder in folders:
        files = [f for f in (DATA / folder).rglob("*.json")]
        for f in sorted(files, key=lambda f: (f.parent.name, len(tier_key(f)), tier_key(f))):
            oid = f.parent.name if kind in ("towers", "heroes") else f.stem
            found = []

            def walk(o, pickup=False, suppress_cash=False, instant_expiry=False):
                if isinstance(o, dict):
                    kind_ = short_type(o)
                    if kind_ in INCOME_RU and not (suppress_cash and kind_ == "CashModel"):
                        found.append((o, pickup, instant_expiry))
                    bank_emission = short_type(o.get("emission")) == "SendToBankModel"
                    for key, v in o.items():
                        walk(v, suppress_cash=(key == "projectile" and (bank_emission or kind_ in CAPTURE_BONUSES))
                             or (suppress_cash and key == "behaviors"))
                elif isinstance(o, list):
                    pickup = any(short_type(v) == "PickupModel" for v in o)  # behaviors of one projectile
                    instant_expiry = oid == "BananaFarm" and any(
                        short_type(v) == "AgeModel" and v.get("lifespanFrames") == 0
                        and v.get("useRoundTime") is False for v in o
                    )
                    for v in o:
                        walk(v, pickup, suppress_cash, instant_expiry)
            walk(load(f))
            for m, pickup, instant_expiry in found:
                kind_ = short_type(m)
                parameters = (m.get("rbeCashMultiplier"), m.get("rbeCapacity"))
                if kind_ == "PerRoundCashBonusTowerModel":
                    parameters = (m.get("cashPerRound"), m.get("cashRoundBonusMultiplier"))
                elif kind_ == "CashModel":
                    parameters = (m.get("minimum"), m.get("maximum"), m.get("bonusMultiplier"))
                elif kind_ == "BankModel":
                    parameters = (m.get("capacity"), m.get("interest"), m.get("autoCollect"))
                elif kind_ == "BananaCashIncreaseSupportModel":
                    parameters = (m.get("mutatorId"), m.get("multiplier"))
                key = (kind_, model_name(m), *parameters)
                e = out.setdefault((kind, oid), {}).setdefault(key, {"first": m, "tiers": {}})
                tiers = e["tiers"].setdefault(verdict(m, pickup, instant_expiry), [])
                if tier_key(f) not in tiers:
                    tiers.append(tier_key(f))
    return out


def tier_text(kind, keys):
    name = (lambda k: f"ур. {k}") if kind == "heroes" else (lambda k: "парагон" if k == "Paragon" else "-".join(k))
    if kind in ("powers", "geraldo"):
        return ""
    return name(keys[0]) + (f" и ещё {len(keys) - 1}" if len(keys) > 1 else "")


def source_badge(kind, oid):
    href = {"towers": f"tower-{oid}.html", "heroes": f"hero-{oid}.html", "powers": f"powers.html#{oid}"}.get(kind)
    pic = icon({"geraldo": "geraldo"}.get(kind, kind), oid, 18) if kind != "powers" else icon("ui", f"power-{oid}", 18)
    body = f"{pic}{esc(t(oid, fallback=oid))}"
    return f"<a class='badge' href='{href}'><b>{body}</b></a>" if href else f"<span class='badge'><b>{body}</b></span>"


def farm_income_rows():
    rows = []
    bank_rows = []
    files = sorted((DATA / "Towers" / "BananaFarm").glob("*.json"), key=tier_key)
    for file in files:
        tier = tier_key(file)
        if len(tier) != 3 or not tier.isdigit():
            continue
        behaviors = load(file).get("behaviors", [])
        bank = next((model for model in behaviors if short_type(model) == "BankModel"), None)
        for attack in behaviors:
            for weapon in attack.get("weapons", []):
                count = next((m["count"] for m in weapon.get("behaviors", [])
                              if short_type(m) == "EmissionsPerRoundFilterModel"), None)
                cash = next((m for m in (weapon.get("projectile") or {}).get("behaviors", [])
                             if short_type(m) == "CashModel"), None)
                if count is None or cash is None:
                    continue
                multiplier = 1 + cash["bonusMultiplier"]
                if bank and short_type(weapon.get("emission")) == "SendToBankModel":
                    amount = cash["maximum"] * multiplier
                    bank_rows.append(["-".join(tier), count, fmt(amount), fmt(amount * count),
                                      fmt(bank["capacity"]), fmt(bank["interest"] * 100)])
                    continue
                if tier[2] not in "345":
                    continue
                low, high = (cash[bound] * multiplier for bound in ("minimum", "maximum"))
                per_emission = fmt(low) if low == high else f"{fmt(low)}–{fmt(high)}"
                per_round = fmt(low * count) if low == high else f"{fmt(low * count)}–{fmt(high * count)}"
                rows.append(["-".join(tier), count, per_emission, per_round])
    return rows, bank_rows


def build_coop():
    # starting cash: the co-op mode's base split evenly, one extra dollar to the first players for a remainder
    # (Simulation init at 0xB44DF0..0xB44E79)
    start_rows = []
    more_cash_rows = []
    more_cash = load(DATA / "Knowledge" / "Primary" / "MoreCash.json")
    more_cash_bonus = next(m["addition"] for m in more_cash["mod"]["mutatorMods"]
                           if short_type(m) == "StartingCashModModel")

    def starting_share(base, players):
        share, remainder = divmod(int(base), players)
        extra = f" (+1 первым {remainder})" if remainder else ""
        return f"${fmt(base)} → ${fmt(share)}{extra}"

    for n in (2, 3, 4):
        row = [n]
        for mode in ("Standard", "Deflation"):
            f = DATA / "Mods" / f"Coop{mode}Cash{n}.json"
            base = next((m.get("changeBase") for m in load(f).get("mutatorMods", []) if short_type(m) == "StartingCashModModel"), None) if f.exists() else None
            row.append(starting_share(base, n) if base is not None else "–")
            if mode == "Standard" and base is not None:
                more_cash_rows.append([n, starting_share(base + more_cash_bonus, n)])
        start_rows.append(row)
    bonus_rows = []
    for difficulty in ("Easy", "Medium", "Hard"):
        models = load(DATA / "Mods" / f"{difficulty}.json").get("mutatorMods", [])
        for model in models:
            if short_type(model) == "BonusCashPerRoundModModel":
                bonus_rows.append([difficulty, model["baseCash"], model["roundMultiple"]])
    income_set = load(DATA / "IncomeSets" / "DefaultIncomeSet.json")
    income_rows = []
    first_round = 1
    for entry in income_set["thresholds"]:
        last_round = entry["threshold"]
        income_rows.append([f"{first_round}–{last_round}", entry["multiplier"]])
        first_round = last_round + 1
    income_rows.append([f"С {first_round}", income_set["finalMultiplier"]])
    first_round_groups = load(DATA / "Rounds" / "DefaultRoundSet" / "1.json")["groups"]
    red = load(DATA / "Bloons" / "Red" / "Red.json")
    red_cash = next(m for m in red["behaviors"] if short_type(m) == "DistributeCashModel")
    red_count = sum(group["count"] for group in first_round_groups if group["bloon"] == "Red")
    first_multiplier = next((entry["multiplier"] for entry in income_set["thresholds"]
                             if entry["threshold"] > 0), income_set["finalMultiplier"])
    pop_total = 0 if red_cash["giveNoCash"] else red_count * (
        (red_cash["cash"] + red_cash["additionalCash"]) * first_multiplier * red_cash["multiplier"]
        + red_cash["additive"])
    _, easy_base, easy_round_multiple = next(row for row in bonus_rows if row[0] == "Easy")
    end_total = easy_base + easy_round_multiple
    example_rows = [[players, pop_total / players, end_total / players, (pop_total + end_total) / players]
                    for players in (2, 3, 4)]
    thrive = load(DATA / "Powers" / "Thrive.json")
    thrive_model = next(model for model in thrive["behaviors"] if short_type(model) == "ThriveModel")
    thrive_scale = thrive_model["increaseBloonWorthSimBehaviorModel"]["cashScale"]
    thrive_rows = [[players, pop_share, pop_total * thrive_scale / players]
                   for players, pop_share, _, _ in example_rows]
    imf_farm = load(DATA / "Towers" / "BananaFarm" / "BananaFarm-040.json")
    loan = next(model for behavior in imf_farm["behaviors"] for model in (behavior.get("behaviors") or [])
                if short_type(model) == "ImfLoanModel")
    collection_rate = loan["imfLoanCollection"]["collectionRate"]
    modifier_rows = []
    for players, pop_share, _, _ in example_rows:
        doubled = 2 * pop_share
        repayment = doubled * collection_rate
        modifier_rows.append([players, pop_share, doubled, repayment, doubled - repayment])
    rules = table(["Откуда", "В коопе", "Основание"], [
        ["Стартовые деньги", "делятся поровну", "Код игры: база режима делится на число игроков"],
        ["Деньги за лопание шаров", "делятся поровну", "Код игры: Simulation.UpdateStagedCash → AddSharedCash"],
        ["Бонус в конце раунда", "делится поровну до личных модификаторов, включая Double Cash, если он разрешён в режиме", "Код игры: AddSharedCash (EndOfRound)"],
        ["Перевод денег другому игроку", "напрямую от игрока игроку", "Код игры: Simulation.SendCash"],
        ["Подбираемые деньги (бананы, ящики)", "владельцу башни, кто бы их ни подобрал", "Код игры: Cash.Pickup → Pickup.Owner.PlayerOwnerId"],
        ["Бонус ловушки инженера", "владельцу ловушки. Стоимость пойманных шаров учитывает доход раунда появления. В CHIMPS бонус отключён", "Код игры: EatBloon.Collide, EatBloon.EmitCash"],
        ["Бонус Wall of Trees", "владельцу стены при подборе. В CHIMPS бонус отключён", "Код игры: WallOfTrees.EmitCash → Cash.Pickup"],
        ["Автоматический доход Marketplace, Central Market и Monkey Wall Street", "владельцу фермы", "Код игры: Age.Process → Cash.Exhausted"],
        ["Продажа башни", "владельцу башни", "Код игры: TowerManager.SellTower → AddCash"],
        ["Банк и выдача займа IMF", "владельцу башни", "Код игры: Bank.Collect, ImfLoan.Activate → AddCash"],
        ["Пополнение банка", "из кошелька владельца фермы. Доступность зависит от знания Bank Deposits, которое отключено в CHIMPS", "Дамп Bank Deposits и код игры BankDeposits.OnTsmThemeAction"],
        ["Возврат займа IMF", "из доли заёмщика после деления, и из переводов ему", "Код игры: ImfLoanCollection.AddCashTransform"],
        ["Double Cash", "удваивает долю своего игрока после деления", "Код игры: AddSharedCash"],
        ["Игрок окончательно удалён из матча", "его баланс делится поровну между оставшимися. Следующие общие выплаты делятся на оставшихся", "Код игры: RemovePeerPermanently → Simulation.RemovePlayer"],
    ])
    rows = []
    for (kind, oid), types in sources().items():
        for (k, name, *_), e in types.items():
            who = "<br>".join(f"<b>{esc(v)}</b>" + (f" <small class='note'>{esc(tier_text(kind, keys))}</small>" if tier_text(kind, keys) else "")
                              for v, keys in e["tiers"].items())
            multiplier = e["first"].get("rbeCashMultiplier")
            capacity = e["first"].get("rbeCapacity")
            if k == "ThriveModel":
                what = f"<b>{esc(INCOME_RU[k])}</b> ×{fmt(e['first']['increaseBloonWorthSimBehaviorModel']['cashScale'])}"
            elif k == "BananaCentralBuffModel":
                what = f"<b>{esc(INCOME_RU[k])}</b> ×{fmt(e['first']['multiplier'])}"
                what += " <small class='note'>Бафф действует на подходящие фермы всей команды, в том числе после их постройки или улучшения</small>"
            elif k == "BananaCashIncreaseSupportModel" and e["first"].get("mutatorId") == "BankHack:Regular":
                bonus = fmt(e["first"]["multiplier"] * 100)
                what = (f"<b>Bank Hack</b> +{bonus} п. п. к множителю выработки банка"
                        " <small class='note'>Действует и на подходящие банки напарников. "
                        "Бонусы нескольких Бенджаминов не складываются. Игра берёт первый эффект в списке банка, "
                        "который сортируется по приоритету без учёта величины бонуса. "
                        "После продажи Бенджамина игра пересчитывает бонус по оставшимся эффектам</small>")
            elif k in CAPTURE_BONUSES and multiplier is not None:
                what = f"<b>{esc(INCOME_RU[k])}</b> ({fmt(multiplier)} − 1) × накопленный доход"
                if capacity is not None:
                    what += f" <small class='note'>Ёмкость {fmt(capacity)} RBE</small>"
            else:
                what = effect_line(e["first"]).replace(f"<b>{esc(EFFECT_RU.get(k) or label(k))}</b>", f"<b>{esc(INCOME_RU[k])}</b>" + (f" <small class='note'>{esc(name)}</small>" if name else ""), 1)
            rows.append((Raw(source_badge(kind, oid)), Raw(what), Raw(who)))
    farm_rows, bank_rows = farm_income_rows()
    body = (card("rules", "Общие правила", rules
                 + "<p class='note'>Правила прочитаны в коде игры (GameAssembly.dll версии 57.4): в выгрузке данных их нет. "
                 "При 2, 3 и 4 игроках доля без других модификаторов: половина, треть, четверть.</p>"
                 + table(["Игроков", "Стандарт: база → на игрока", "Deflation: база → на игрока"], start_rows)
                 + f"<p>Если в матче действует знание More Cash, оно один раз добавляет ${fmt(more_cash_bonus)} "
                 "к стартовой сумме команды перед делением. Ниже суммы Standard с этим знанием, до Double Cash.</p>"
                 + table(["Игроков", "Standard с More Cash, команда → на игрока"], more_cash_rows)
                 + "<p>Общий бонус в конце раунда равен базе плюс номер раунда, умноженный на коэффициент. "
                 "Доля игрока равна общему бонусу, делённому на текущее число получателей. "
                 "Double Cash может удвоить эту долю для своего игрока. Затем из неё может удерживаться платёж по займу IMF.</p>"
                 + table(["Сложность", "База бонуса", "Коэффициент номера раунда"], bonus_rows), section="Кооп")
            + card("pop-income", "Деньги за лопание шаров",
                   "<p>Игра выбирает коэффициент по раунду появления шара, даже если его лопнули позже. "
                   "Для обычного поп-дохода она применяет коэффициент, затем делит итог между получателями.</p>"
                   "<p>Lead to Gold и Rubber to Gold дают владельцу Alchemist отдельную выплату. "
                   "Игра прибавляет к фиксированной сумме число снятых слоёв, засчитанных в <code>nonRegrowLayers</code>, "
                   "умноженное на коэффициент раунда появления и множитель бонуса. В CHIMPS обе части этой выплаты равны нулю.</p>"
                   + table(["Раунд появления", "Коэффициент DefaultIncomeSet"], income_rows)
                   + f"<p>Пример для первого раунда Easy Standard. За {red_count} красных шаров команда получает "
                   f"${fmt(pop_total)}, за завершение раунда ещё ${fmt(end_total)}. В таблице доли до личных "
                   "модификаторов. Стартовые деньги и доход башен в расчёт не входят.</p>"
                   + table(["Игроков", "За шары на игрока, $", "За конец раунда на игрока, $", "Всего на игрока, $"],
                           example_rows)
                   + f"<p>Один действующий Thrive умножает обычный доход за шары на {fmt(thrive_scale)}. "
                   "Бонус входит в общую сумму до деления. Одновременные эффекты с тем же именем "
                   "игра учитывает один раз. Ниже тот же доход за шары до личных модификаторов.</p>"
                   + table(["Игроков", "За шары без Thrive, $ на игрока", "За шары с Thrive, $ на игрока"], thrive_rows)
                   + "<p>Если один игрок имеет Double Cash и непогашенный заём IMF, обычный доход за шары "
                   "сначала делится, затем его доля удваивается, затем из неё удерживается погашение. "
                   f"Ставка удержания для 0-4-0 из дампа составляет {fmt(collection_rate * 100)}%. "
                   "Удержание ограничено остатком долга. Для примера ниже взята та же общая сумма за шары "
                   "и предполагается достаточный остаток долга.</p>"
                   + table(["Игроков", "Другим игрокам каждому, $", "Доля заёмщика после Double Cash, $",
                            "В погашение, $", "В кошелёк заёмщика, $"], modifier_rows)
                   + "<p>Для прямого начисления владельцу, например за подбор ловушки инженера, "
                   "игра сначала удерживает долг и затем удваивает остаток, если выплата допускает Double Cash.</p>",
                   section="Кооп")
            + card("farm-income", "Автоматический доход ферм",
                   "<p>Marketplace, Central Market и Monkey Wall Street начисляют эти деньги владельцу. "
                   "Сумма за раунд предполагает, что ферма использует все запланированные срабатывания. "
                   "Дополнительная выплата Monkey Wall Street в конце раунда считается отдельно. "
                   "В CHIMPS игра обнуляет эти суммы и сумму выдачи займа IMF.</p>"
                   + table(["Улучшения фермы", "Срабатываний", "За срабатывание, $", "За полный набор, $"],
                           farm_rows), section="Кооп")
            + card("banks", "Monkey Bank",
                   "<p>Обычная выработка сразу пополняет банк и базу для процентов. При начислении процентов "
                   "игра прибавляет к текущему балансу базу, умноженную на ставку, ограничивает сумму ёмкостью "
                   "банка и сохраняет результат как новую базу. Ручное пополнение входит в базу при её следующем обновлении.</p>"
                   "<p>Суммы выработки указаны до лимита банка и процентов. В CHIMPS выработка равна нулю. "
                   "При сборе деньги получает владелец фермы.</p>"
                   + table(["Улучшения фермы", "Срабатываний", "За срабатывание, $", "За полный набор, $",
                            "Ёмкость, $", "Ставка, %"], bank_rows), section="Кооп")
            + card("sources", "Доход башен, героев и сил",
                   "<p class='note'>«Делится» и «владельцу» взяты из флагов модели: distributeCash у денег в конце раунда, "
                   "у подбираемых денег PickupModel рядом, emittedByCashEarnedMultiplier и distributeBonusIncome. "
                   "«Не проверено»: путь этих денег в коде игры ещё не прослежен. Числа из "
                   "первого тира, где источник появляется.</p>"
                   "<input class='filter' type='search' placeholder='Фильтр: башня или источник' aria-label='Фильтр источников' "
                   "data-filter='#coop-src tbody tr'>"
                   + table(["Источник", "Что даёт", "В коопе"], rows).replace("<table>", "<table id='coop-src'>", 1), section="Кооп"))
    page("coop.html", "Деньги в коопе", "Откуда приходят деньги и делятся ли они между игроками в кооперативе.", body,
         [("rules", "Общие правила"), ("pop-income", "Деньги за лопание шаров"),
          ("farm-income", "Автоматический доход ферм"),
          ("banks", "Monkey Bank"),
          ("sources", "Доход башен, героев и сил")])
