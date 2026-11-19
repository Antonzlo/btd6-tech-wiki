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
    "GiveCashOnPopModel": "Деньги за лопание", "CashbackZoneModel": "Больше денег при продаже",
    "BonusCashZoneModel": "Бонус к деньгам в зоне", "CashIncreaseModel": "Больше денег за лопание",
    "MonkeyCityIncomeSupportModel": "Бонус Monkey City к доходу башен", "BananaCashIncreaseSupportModel": "Больше денег с бананов",
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
    if k in ("ThriveModel", "CashIncreaseModel"):
        return SPLIT
    if k == "BananaCentralBuffModel":
        return "владельцу фермы, получившей бонус"
    if k == "BananaCashIncreaseSupportModel" and m.get("mutatorId") == "BankHack:Regular":
        return "владельцу банка при сборе"
    if k == "MonkeyCityIncomeSupportModel":
        return "по правилам усиленной выплаты"
    if k in ("BankModel", "ImfLoanModel", "GiveCashOnPopModel"):
        return OWNER
    if k in ("CashPerTowerInRangeModel", "CashPerTowerInMakeshiftAreaModel"):
        return OWNER
    if k == "AddCashOnProjectileExpireModel":
        return "владельцу снаряда"
    if k == "CashbackZoneModel":
        return "владельцу проданной башни"
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
                elif kind_ == "MonkeyCityIncomeSupportModel":
                    parameters = (m["incomeModifier"],)
                elif kind_ == "CashIncreaseModel":
                    parameters = (m["increase"], m["multiplier"])
                elif kind_ == "CashPerTowerInRangeModel":
                    parameters = (m["baseCash"], tuple(m["extraCashPerTier"]), m["maxCashGeneration"])
                elif kind_ == "CashbackZoneModel":
                    parameters = (m["cashbackZoneMultiplier"], m["cashbackMaxPercent"], m["maxStacks"])
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


def captured_cash_layers(bloon, lowest_layer=None):
    """Raw Engineer capture income from the effective model tree (GetNonRegrowLayers, 0xFC7C90).

    The threshold is the lowest layer previously reached, not a minimum eligible layer.
    Preserve duplicate child IDs. Base dump inputs do not apply runtime mode mutations.
    """
    model = load(DATA / "Bloons" / bloon / f"{bloon}.json")
    if lowest_layer is None:
        lowest_layer = model["layerNumber"]
    own = 1 + model["layerCountOffset"] if model["layerNumber"] <= lowest_layer else 0
    return own + sum(captured_cash_layers(child, lowest_layer)
                     for behavior in model["behaviors"] if short_type(behavior) == "SpawnChildrenModel"
                     for child in behavior["children"])


def build_coop():
    # Starting cash splits the integer pool and assigns the remainder in dictionary key order.
    # (Simulation init at 0xB44DF0..0xB44E79)
    start_rows = []
    more_cash_rows = []
    more_cash = load(DATA / "Knowledge" / "Primary" / "MoreCash.json")
    more_cash_bonus = next(m["addition"] for m in more_cash["mod"]["mutatorMods"]
                           if short_type(m) == "StartingCashModModel")

    def starting_share(base, players):
        share, remainder = divmod(int(base), players)
        if remainder:
            return f"${fmt(base)} → {remainder} × ${fmt(share + 1)} + {players - remainder} × ${fmt(share)}"
        return f"${fmt(base)} → ${fmt(share)}"

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
    chimps_mods = load(DATA / "Mods" / "Clicks.json")["mutatorMods"]
    chimps_start = next(m["round"] for m in chimps_mods if short_type(m) == "StartingRoundModModel")
    _, hard_base, hard_round_multiple = next(row for row in bonus_rows if row[0] == "Hard")
    chimps_first_bonus = hard_base + chimps_start * hard_round_multiple
    xp = load(DATA / "KnowledgeLayout" / "xp.json")
    chimps_first_xp = xp["heroXpPerRound"][chimps_start - 1] * xp["trackDifficultyXpScale"]["Beginner"]
    income_set = load(DATA / "IncomeSets" / "DefaultIncomeSet.json")
    income_rows = []
    first_round = 1
    for entry in income_set["thresholds"]:
        last_round = entry["threshold"]
        income_rows.append([f"{first_round}–{last_round}", entry["multiplier"]])
        first_round = last_round + 1
    income_rows.append([f"С {first_round}", income_set["finalMultiplier"]])
    first_round_groups = load(DATA / "Rounds" / "DefaultRoundSet" / "1.json")["groups"]
    red_count = sum(group["count"] for group in first_round_groups if group["bloon"] == "Red")

    def simple_bloon_cash(bloon, income_multiplier):
        """Sum separately popped layers for the Red, Blue and Green example rounds."""
        model = load(DATA / "Bloons" / bloon / f"{bloon}.json")
        cash = next(m for m in model["behaviors"] if short_type(m) == "DistributeCashModel")
        layer = 0 if cash["giveNoCash"] else (
            (cash["cash"] + cash["additionalCash"]) * income_multiplier * cash["multiplier"] + cash["additive"])
        children = (child for m in model["behaviors"] if short_type(m) == "SpawnChildrenModel"
                    for child in m["children"])
        return layer + sum(simple_bloon_cash(child, income_multiplier) for child in children)

    def income_multiplier_for_round(round_number):
        return next((entry["multiplier"] for entry in income_set["thresholds"]
                     if round_number <= entry["threshold"]), income_set["finalMultiplier"])

    pop_total = red_count * simple_bloon_cash("Red", income_multiplier_for_round(1))
    first_threshold = income_set["thresholds"][0]["threshold"]
    red_at_threshold = simple_bloon_cash("Red", income_multiplier_for_round(first_threshold))
    red_after_threshold = simple_bloon_cash("Red", income_multiplier_for_round(first_threshold + 1))
    chimps_round = load(DATA / "Rounds" / "DefaultRoundSet" / f"{chimps_start}.json")
    chimps_multiplier = income_multiplier_for_round(chimps_start)
    chimps_pop_cash = sum(group["count"] * simple_bloon_cash(group["bloon"], chimps_multiplier)
                          for group in chimps_round["groups"])
    chimps_rows = [[players, chimps_first_xp, chimps_first_xp / players, chimps_pop_cash / players,
                    chimps_first_bonus / players, (chimps_pop_cash + chimps_first_bonus) / players]
                   for players in (2, 3, 4)]
    _, easy_base, easy_round_multiple = next(row for row in bonus_rows if row[0] == "Easy")
    end_total = easy_base + easy_round_multiple
    example_rows = [[players, pop_total / players, end_total / players, (pop_total + end_total) / players]
                    for players in (2, 3, 4)]
    departure_balance = 300
    departure_rows = [[players, players - 1, departure_balance / (players - 1), pop_total / (players - 1)]
                      for players in (2, 3, 4)]
    thrive = load(DATA / "Powers" / "Thrive.json")
    thrive_model = next(model for model in thrive["behaviors"] if short_type(model) == "ThriveModel")
    thrive_scale = thrive_model["increaseBloonWorthSimBehaviorModel"]["cashScale"]
    thrive_rows = [[players, pop_share, pop_total * thrive_scale / players]
                   for players, pop_share, _, _ in example_rows]
    village = load(DATA / "Towers" / "MonkeyVillage" / "MonkeyVillage-003.json")
    town_model = next(model for model in village["behaviors"] if short_type(model) == "CashIncreaseModel")
    marked_red_cash = simple_bloon_cash("Red", income_multiplier_for_round(1)) * town_model["multiplier"]
    marked_red_cash += town_model["increase"]
    town_rows = [[players, marked_red_cash / players, marked_red_cash * thrive_scale / players]
                 for players in (2, 3, 4)]
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
        ["Перевод денег другому игроку", "получателю без Double Cash, с удержанием по его займу IMF", "Код игры: Simulation.SendCash → AddCash"],
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
    income_sources = sources()
    trap_multiplier = next(e["first"]["rbeCashMultiplier"]
                           for (kind, oid), types in income_sources.items()
                           if kind == "towers" and oid == "EngineerMonkey"
                           for key, e in types.items() if key[0] == "EatBloonModel")
    capture_rows = []
    red_layer = load(DATA / "Bloons" / "Red" / "Red.json")["layerNumber"]
    for bloon in ("Red", "Blue", "Green"):
        raw = captured_cash_layers(bloon)
        capture_rows.append([t(bloon, fallback=bloon), raw,
                             raw * (trap_multiplier - 1) * income_multiplier_for_round(1),
                             raw * (trap_multiplier - 1) * income_multiplier_for_round(first_threshold + 1),
                             captured_cash_layers(bloon, red_layer)])
    for (kind, oid), types in income_sources.items():
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
            elif k == "CashPerTowerInRangeModel":
                model = e["first"]
                extras = ", ".join(map(fmt, model["extraCashPerTier"]))
                what = (f"<b>{esc(INCOME_RU[k])}</b> ${fmt(model['baseCash'])}"
                        f" <small class='note'>Плюс за каждую подходящую башню в радиусе по её тиру: {extras}. "
                        f"Предел до множителей способности: ${fmt(model['maxCashGeneration'])}</small>")
            elif k == "MonkeyCityIncomeSupportModel":
                multiplier = e["first"]["incomeModifier"]
                what = (f"<b>{esc(INCOME_RU[k])}</b>"
                        f" <small class='note'>Для поддерживаемых выплат в конце раунда и дохода способности Друида: "
                        f"×{fmt(multiplier)}. К множителю выработки денежных снарядов: "
                        f"+{fmt((multiplier - 1) * 100)} п. п.</small>")
            elif k == "CashIncreaseModel":
                model = e["first"]
                what = (f"<b>{esc(INCOME_RU[k])}</b>"
                        f" <small class='note'>Для отмеченных шаров к множителю дохода за лопание: "
                        f"+{fmt((model['multiplier'] - 1) * 100)} п. п. "
                        f"Фиксированная прибавка: ${fmt(model['increase'])}.</small>")
            elif k == "CashbackZoneModel":
                model = e["first"]
                what = (f"<b>{esc(INCOME_RU[k])}</b> +{fmt(model['cashbackZoneMultiplier'] * 100)} п. п."
                        f" <small class='note'>Лимит эффектов этой модели: {model['maxStacks']}. "
                        f"Предел доли возврата в модели: {fmt(model['cashbackMaxPercent'] * 100)}%</small>")
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
                 "<p class='note'>Проверка выполнена по данным и коду, без записи живых кооп-матчей. "
                 "Для ловушки инженера подтверждён отдельный бонус владельцу; обычная выплата за поглощённые шары "
                 "ещё не подтверждена.</p>"
                 + table(["Игроков", "Стандарт: база → на игрока", "Deflation: база → на игрока"], start_rows)
                 + "<p>При делении стартовой суммы игра отбрасывает дробную часть, затем выдаёт по одному "
                 "дополнительному доллару за каждую единицу остатка в порядке обхода словаря игроков. "
                 "Double Cash удваивает уже назначенную сумму, если режим разрешает удвоение.</p>"
                 + f"<p>Если в матче действует знание More Cash, оно один раз добавляет ${fmt(more_cash_bonus)} "
                 "к стартовой сумме команды перед делением. Ниже суммы Standard с этим знанием, до Double Cash.</p>"
                 + table(["Игроков", "Standard с More Cash, команда → на игрока"], more_cash_rows)
                 + "<p>Когда игра окончательно удаляет игрока, его остаток делится на число оставшихся. "
                 "Эта сумма сразу прибавляется к их балансам без Double Cash и удержания по займу IMF. "
                 "Следующие общие выплаты тоже делятся на оставшихся, с обычными личными модификаторами. "
                 "При временном обрыве связи доля рассчитывается по прежнему числу игроков, пока симуляция сохраняет их записи. "
                 f"Ниже пример с остатком ${fmt(departure_balance)} и следующей общей выплатой ${fmt(pop_total)} "
                 "до личных модификаторов. Правило привязано к окончательному удалению из матча.</p>"
                 + table(["Игроков до выхода", "Осталось", "Из остатка на игрока, $", "Из следующей выплаты на игрока, $"],
                         departure_rows)
                 + "<p>Общий бонус в конце раунда равен базе плюс отображаемый номер раунда, умноженный на коэффициент. "
                 "Доля игрока равна общему бонусу, делённому на текущее число получателей. "
                 "Double Cash может удвоить эту долю для своего игрока. Затем из неё может удерживаться платёж по займу IMF.</p>"
                 + table(["Сложность", "База бонуса", "Коэффициент номера раунда"], bonus_rows)
                 + f"<p>Пример для первого раунда CHIMPS ({chimps_start}) на карте Beginner с рейтингом сложности 1. "
                 "У каждого игрока по одной учитываемой башне одинаковой стоимости. "
                 "В расчёте все шары лопаются обычными атаками, без дополнительных денежных эффектов. "
                 f"Команда получает ${fmt(chimps_pop_cash)} за все шары и ${fmt(chimps_first_bonus)} за завершение раунда.</p>"
                 + table(["Игроков", "XP аккаунта каждому", "XP башни каждого игрока",
                          "Шары на игрока, $", "Бонус на игрока, $", "Всего на игрока, $"],
                         chimps_rows), section="Кооп")
            + card("pop-income", "Деньги за лопание шаров",
                   "<p>Игра выбирает коэффициент по раунду появления шара, даже если его лопнули позже. "
                   "Для обычного поп-дохода она применяет коэффициент, затем делит итог между получателями.</p>"
                   "<p>Lead to Gold и Rubber to Gold дают владельцу Alchemist отдельную выплату. "
                   "Игра прибавляет к фиксированной сумме число снятых слоёв, засчитанных в <code>nonRegrowLayers</code>, "
                   "умноженное на коэффициент раунда появления и множитель бонуса. В CHIMPS обе части этой выплаты равны нулю.</p>"
                   + table(["Раунд появления", "Коэффициент DefaultIncomeSet"], income_rows)
                   + f"<p>Красный шар, появившийся в раунде {first_threshold}, даёт команде ${fmt(red_at_threshold)}. "
                   f"Если он появился на раунд позже, выплата составляет ${fmt(red_after_threshold)} "
                   "до деления и личных модификаторов.</p>"
                   + f"<p>Пример для первого раунда Easy Standard. За {red_count} красных шаров команда получает "
                   f"${fmt(pop_total)}, за завершение раунда ещё ${fmt(end_total)}. В таблице доли до личных "
                   "модификаторов. Стартовые деньги и доход башен в расчёт не входят.</p>"
                   + table(["Игроков", "За шары на игрока, $", "За конец раунда на игрока, $", "Всего на игрока, $"],
                           example_rows)
                   + f"<p>Один действующий Thrive умножает обычный доход за шары на {fmt(thrive_scale)}. "
                   "Бонус входит в общую сумму до деления. Одновременные эффекты с тем же именем "
                   "игра учитывает один раз. Ниже тот же доход за шары до личных модификаторов.</p>"
                   + table(["Игроков", "За шары без Thrive, $ на игрока", "За шары с Thrive, $ на игрока"], thrive_rows)
                   + "<p>Несколько меток Monkey Town на одном шаре не складываются. "
                   "Thrive умножает уже увеличенный доход. Ниже доли за один отмеченный красный шар "
                   "с полным коэффициентом дохода, до личных модификаторов.</p>"
                   + table(["Игроков", "Monkey Town, $ на игрока", "Monkey Town и Thrive, $ на игрока"], town_rows)
                   + "<p>Если один игрок имеет Double Cash и непогашенный заём IMF, обычный доход за шары "
                   "сначала делится, затем его доля удваивается, затем из неё удерживается погашение. "
                   f"Ставка удержания для 0-4-0 из дампа составляет {fmt(collection_rate * 100)}%. "
                   "Удержание ограничено остатком долга. Для примера ниже взята та же общая сумма за шары "
                   "и предполагается достаточный остаток долга.</p>"
                   + table(["Игроков", "Другим игрокам каждому, $", "Доля заёмщика после Double Cash, $",
                            "В погашение, $", "В кошелёк заёмщика, $"], modifier_rows)
                   + "<p>Для прямого начисления владельцу, например за подбор ловушки инженера, "
                   "игра сначала удерживает долг и затем удваивает остаток, если выплата допускает Double Cash. "
                   "Например, при доле или прямой выплате $100 до удвоения и остатке долга $10 получатель "
                   f"получит ${fmt(200 - min(200 * collection_rate, 10))} из общей выплаты "
                   f"или ${fmt(2 * (100 - min(100 * collection_rate, 10)))} из прямой. "
                   "Оба примера начинаются с одинакового долга и предполагают, что удвоение разрешено.</p>"
                   "<p>При переводе $100 другому игроку Double Cash не применяется. "
                   f"Если у получателя осталось не меньше ${fmt(100 * collection_rate)} долга по займу IMF, "
                   f"${fmt(100 * collection_rate)} уйдут на погашение, а ${fmt(100 * (1 - collection_rate))} поступят в кошелёк. "
                   "Сумма не зависит от числа игроков.</p>",
                   section="Кооп")
            + card("engineer-trap", "Бонус ловушки инженера",
                   "<p>База бонуса считается по пойманному шару и его потомкам из выгрузки. "
                   "Каждый слой с номером не выше наименьшего уже достигнутого номера даёт 1 плюс layerCountOffset. "
                   "Выросшие заново верхние слои не дают повторного бонуса.</p>"
                   f"<p>Ловушка умножает накопленную базу на коэффициент дохода раунда появления шара, "
                   f"затем при выдаче бонуса на ({fmt(trap_multiplier)} − 1). "
                   "Это отдельный бонус владельцу, одинаковый при 2, 3 и 4 игроках. "
                   "Таблица показывает вклад одного шара в будущую выплату до личных модификаторов, "
                   "без обычных денег за лопание. В CHIMPS этот бонус отключён.</p>"
                   + table(["Шар", "База свежего шара", "Бонус при появлении в раунде 1, $",
                            f"Бонус при появлении в раунде {first_threshold + 1}, $",
                            "База, если ранее достигнут красный слой"], capture_rows), section="Кооп")
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
                   "<p>Зоны возврата действуют при продаже обычной башни в режимах, где они разрешены. "
                   "При продаже парагона и в CHIMPS игра пропускает эти зоны. "
                   "Обычные зоны Buccaneer и зона парагона используют один счётчик при продаже. "
                   "Игра обходит подходящие зоны в порядке реестра и сверяет счётчик с лимитом текущей зоны. "
                   "Если первой идёт обычная зона, парагон уже пропускается. "
                   "Если первым идёт парагон, следующие обычные зоны могут добавить свой вклад до своего лимита.</p>"
                   "<p class='note'>«Делится» и «владельцу» взяты из флагов модели: distributeCash у денег в конце раунда, "
                   "у подбираемых денег PickupModel рядом, emittedByCashEarnedMultiplier и distributeBonusIncome. "
                   "«Не проверено»: путь этих денег в коде игры ещё не прослежен. Числа из "
                   "первого тира, где источник появляется.</p>"
                   "<input class='filter' type='search' placeholder='Фильтр: башня или источник' aria-label='Фильтр источников' "
                   "data-filter='#coop-src tbody tr'>"
                   + table(["Источник", "Что даёт", "В коопе"], rows).replace("<table>", "<table id='coop-src'>", 1), section="Кооп"))
    page("coop.html", "Деньги в коопе", "Откуда приходят деньги и делятся ли они между игроками в кооперативе.", body,
         [("rules", "Общие правила"), ("pop-income", "Деньги за лопание шаров"),
          ("engineer-trap", "Бонус ловушки инженера"),
          ("farm-income", "Автоматический доход ферм"),
          ("banks", "Monkey Bank"),
          ("sources", "Доход башен, героев и сил")])
