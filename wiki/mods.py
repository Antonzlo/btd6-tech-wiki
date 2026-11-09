"""Modifier tables: knowledge, mode and power mods rendered as readable parameters."""
import re
from wiki import core
from wiki.core import DATA, Raw, TOWER_SETS, esc, flatten, fmt, icon, label, short_type, t, table
from wiki.bloons import BLOONS


LOCK_SVG = ("<svg class='ic mod-ic' viewBox='0 0 24 24' width='22' height='22' aria-hidden='true'>"
            "<rect x='4' y='10' width='16' height='11' rx='3' fill='var(--gold)' stroke='var(--edge)' stroke-width='2'/>"
            "<path d='M8 10V7a4 4 0 0 1 8 0v3' fill='none' stroke='var(--edge)' stroke-width='2.5'/></svg>")
# modifier type -> icon (kind, id) from data/icons, or the drawn lock
MOD_ICONS = {
    "StartingCashModModel": ("ui", "startcash"), "ModifyAllCashModModel": ("ui", "coin"), "BonusCashPerRoundModModel": ("ui", "coin"),
    "GlobalCostModModel": ("ui", "coin"), "SellMultiplierModModel": ("ui", "coin"),
    "StartingHealthModModel": ("ui", "lives"), "MaxHealthModModel": ("ui", "lives"),
    "MonkeyMoneyModModel": ("ui", "mm"), "DisableSellTowerModModel": ("ui", "nosell"),
    "DisableMonkeyKnowledgeModModel": ("ui", "noknowledge"), "GlobalSpeedModModel": ("ui", "speed"),
    "StartingRoundModModel": ("ui", "startround"), "EndRoundModModel": ("ui", "endround"),
    "DisableContinueModModel": ("ui", "nocontinue"), "RoundSetModModel": ("ui", "roundset"),
    "RemoveManaShieldModModel": ("ui", "nomana"), "ChimpsModModel": ("ui", "mode-Clicks"),
    "ImpoppableModel": ("ui", "mode-Impoppable"), "DeflationModel": ("ui", "mode-Deflation"), "ReverseModel": ("ui", "mode-Reverse"),
    "SetHealthForBloonModModel": ("bloons", "Moab"), "BloonHealthModel": ("bloons", "Red"),
    "LockTowerSetModModel": "lock", "LockTowerModModel": "lock",
}


def mod_icon(type_name):
    spec = MOD_ICONS.get(type_name)
    if spec == "lock":
        return LOCK_SVG
    return icon(spec[0], spec[1], 22, "ic mod-ic") if spec else "<span class='mod-ic'></span>"


PARAM_RU = {  # model field -> words; fields not listed fall back to their camelCase split into words
    "addative": "прибавка", "addition": "прибавка", "additional": "прибавка", "additionalAmount": "доп. количество",
    "additionalCapacity": "доп. вместимость", "additionalCount": "доп. количество", "additionalFrames": "доп. кадры",
    "additionalLifespan": "доп. время жизни", "additionalLoanAmount": "доп. сумма займа", "additionalMoney": "доп. деньги",
    "additionalMultiplier": "доп. множитель", "additionalTime": "доп. время", "additionalTrapAmount": "доп. ёмкость ловушки",
    "additive": "прибавка", "additiveAmount": "прибавка", "additiveBonus": "прибавка к бонусу",
    "aditionalTimeBonus": "доп. бонус времени", "amount": "количество", "amountReduced": "уменьшение",
    "baseCash": "базовые деньги", "baseTowerID": "башня", "bloonId": "шар", "bloonProperties": "свойства шара",
    "bloonTag": "тег шара", "bloonTags": "теги шаров", "bonusMultiplierBuff": "множитель бонуса",
    "canHitbloonProperties": "может бить свойства", "cashMultiplierIncrease": "рост множителя денег",
    "centralMarketLives": "жизни от рынка", "chance": "шанс", "chanceIncrease": "рост шанса", "changeBase": "задать базу",
    "charges": "заряды", "cooldown": "перезарядка", "cooldownPercentageReduction": "сокращение перезарядки, %",
    "cooldownTimeReduction": "сокращение перезарядки, с", "costDecrease": "снижение цены", "costMultiplier": "множитель цены",
    "count": "количество", "damage": "урон", "damageBossIncrease": "рост урона по боссам", "damageIncrease": "рост урона",
    "damageIncreaseAmount": "рост урона", "depositPercent": "процент вклада", "discountMultiplier": "множитель скидки",
    "displayLifespan": "время показа", "displayLifetime": "время показа", "distFromEdgeOfMap": "отступ от края карты",
    "duration": "длительность", "durationAdd": "доп. длительность", "durationIncrease": "рост длительности",
    "durationModifier": "множитель длительности", "gameMode": "режим", "healthMod": "множитель HP",
    "healthMultiplier": "множитель HP", "id": "id", "increase": "рост", "interestRateDecreaseAmount": "снижение процента",
    "interval": "интервал", "layers": "слои", "levels": "уровни", "lifespan": "время жизни",
    "lifespanFrames": "время жизни, кадры", "marketplaceLives": "жизни от рынка", "maxCountAdditive": "доп. максимум",
    "maxShield": "максимум щита", "minTier": "мин. тир", "multiplier": "множитель", "multiplierAdditive": "прибавка к множителю",
    "multiplierAmount": "множитель", "multiplierTurnRate": "множитель поворота", "mutltiplier": "множитель",
    "path": "путь", "path1TierMax": "верхний путь, макс. тир", "path1TierMin": "верхний путь, мин. тир",
    "path2TierMax": "средний путь, макс. тир", "path2TierMin": "средний путь, мин. тир",
    "path3TierMax": "нижний путь, макс. тир", "path3TierMin": "нижний путь, мин. тир", "percentBonus": "бонус, %", "percentChanceToFreeze": "шанс заморозки, %",
    "percentIncrease": "рост, %", "percentMultiplier": "множитель, %", "percentMultiplierAdded": "прибавка к множителю, %",
    "percentMultiplierOverride": "замена множителя, %", "percentageHealthReduced": "снижение HP, %",
    "percentageReduced": "снижение, %", "pierce": "пробивание", "pierceIncrease": "рост пробивания", "priority": "приоритет",
    "radius": "радиус", "range": "дальность", "rangeMultiplier": "множитель дальности", "rate": "скорость атаки",
    "rateFrames": "скорость атаки, кадры", "rateMultiplier": "множитель скорости атаки", "reductionAmount": "снижение",
    "round": "раунд", "roundMultiple": "за номер раунда", "rounds": "раунды", "roundsetName": "набор раундов",
    "set": "задать", "shieldPerRound": "щит за раунд", "shotCount": "выстрелы", "slowModifier": "множитель замедления",
    "speed": "скорость", "speedMultiplier": "множитель скорости", "startingShield": "стартовый щит",
    "subtractHeroCost": "минус цена героя", "subtraction": "вычет", "tag": "тег", "targetType": "тип цели",
    "tier": "тир", "timeReductionAmount": "сокращение времени", "tower": "башня", "towerBaseId": "башня",
    "towerSetToLock": "запрет класса", "towerToLock": "запрет башни", "towers": "башни", "upgradeName": "улучшение",
    "useAbilityDuration": "длительность способности", "useAllHeroes": "все герои", "withTag": "с тегом", "tagFilter": "фильтр тегов",
    "xpToAdd": "доп. опыт", "maxActivationsPerRound": "макс. за раунд", "maxActivationsPerGame": "макс. за игру",
    "livesCost": "цена в жизнях", "maxDamage": "макс. урон", "maxPierce": "макс. пробивание", "glueLevel": "уровень клея",
    "maxStackSize": "макс. стак",
    "cashPerRound": "денег за раунд", "minimum": "минимум", "maximum": "максимум", "capacity": "вместимость",
    "interest": "процент", "flatCashAmount": "денег за шар", "incomeModifier": "множитель дохода", "salvage": "при продаже",
    "cashbackZoneMultiplier": "возврат за башню", "cashbackMaxPercent": "максимум возврата, %", "cashToAdd": "денег",
    "cashAmount": "денег", "incomeRecoveryRate": "доля дохода на долг", "collectionRate": "доля на долг",
    "emittedByCashEarnedMultiplier": "доля сразу", "distributeCash": "делится",
}


def param_name(k):
    """Readable name of a (possibly nested a.b.c) model field; the raw id stays in the badge tooltip."""
    leaf = k.split(".")[-1].split("#")[0]
    if core.LANG == "ru" and leaf in PARAM_RU:
        return PARAM_RU[leaf]
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])", " ", leaf).lower()


def ref(k, v):
    """(href, html) for a value that names something with a page here (tower, hero, bloon, ...), else None."""
    s = str(v)
    if k == "towerSetToLock" and v in TOWER_SETS:
        return f"towers.html#set-{TOWER_SETS[v]}", icon("ui", TOWER_SETS[v], 18) + esc(t(TOWER_SETS[v], fallback=TOWER_SETS[v]))
    if k == "roundsetName" and (DATA / "Rounds" / s).is_dir():
        return f"rounds.html#{s}", esc(s)
    if not re.fullmatch(r"[A-Za-z][\w-]*", s) or s in ("True", "False"):
        return None
    if (DATA / "Towers" / s).is_dir():
        return f"tower-{s}.html", icon("towers", s, 18) + esc(t(s, fallback=s))
    if (DATA / "Heroes" / s).is_dir():
        return f"hero-{s}.html", icon("heroes", s, 18) + esc(t(s, fallback=s))
    if s in BLOONS:
        return f"bloons.html#{BLOONS[s].get('baseId', s)}", icon("bloons", s, 18) + esc(t(s, fallback=s))
    return None


def param(k, v):
    """A model parameter as a two-part badge; values naming a tower, hero or bloon link to its page,
    and a comma-separated list of them becomes one linked chip per item."""
    items = re.split(r"\s*,\s*", v.strip(", ")) if isinstance(v, str) and "," in v else [v]
    refs = [ref(k, x) for x in items]
    title = f" title='{esc(k)}'"
    name = f"<span>{esc(param_name(k))}</span>"
    if len(items) > 1 and all(refs):
        chips = "".join(f"<a href='{h}'>{body}</a>" for h, body in refs)
        return f"<span class='badge multi'{title}>{name}<b>{chips}</b></span>"
    if refs[0]:
        h, body = refs[0]
        return f"<a class='badge' href='{h}'{title}>{name}<b>{body}</b></a>"
    if "percent" in k.lower() and isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) < 1e6:
        # the game stores most percentages as fractions (0.03 = 3%); a value above 1 is already in percent
        pct = v * 100 if abs(v) <= 1 else v
        name = f"<span>{esc(param_name(k).removesuffix(', %'))}</span>"
        return f"<span class='badge'{title}>{name}<b>{fmt(round(pct, 4))}%</b></span>"
    return f"<span class='badge'{title}>{name}<b>{fmt(v)}</b></span>"


def mod_table(mods):
    """Mutator models as rows: icon + readable name, then their parameters as badges."""
    rows = [(Raw(f"<span class='mod-name'>{mod_icon(short_type(m))}{esc(label(short_type(m)))}</span>"),
             Raw(f"<div class='mod-params'>{' '.join(param(k, v) for k, v in flatten(m).items() if v != '') or '–'}</div>")) for m in mods]
    return table(["Модификатор", "Параметры"], rows).replace("<table>", "<table class='nosort'>", 1) if rows else "<p class='note'>Без модификаторов.</p>"
