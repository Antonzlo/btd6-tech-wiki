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
}
SPLIT, OWNER, PICKER, UNKNOWN = "делится на всех", "владельцу башни", "одному игроку", "не проверено"


def verdict(m):
    """Who gets this cash in co-op, from the model's own flag; game code: PerRoundCashBonusTower.OnRoundComplete
    (distributeCash: AddSharedCash, else AddCash to the owner) and Cash.Pickup (a share to one player, the rest
    shared when distributeBonusIncome; which player is not traced yet)."""
    k = short_type(m)
    if k == "PerRoundCashBonusTowerModel":
        return SPLIT if m.get("distributeCash") else OWNER
    if k == "CashModel":
        return "основное одному игроку, бонус делится" if m.get("distributeBonusIncome") else PICKER
    return UNKNOWN


def model_name(m):
    """The model's own name without its type prefix and tier suffix: two models of one type stay apart
    (Alchemist: LeadToGold and RubberToGold are both GiveCashOnPopModel), one model across tiers stays together."""
    n = re.sub(r"_?[A-Za-z]+-(\d{3}|Paragon)_?$", "", m.get("name") or "")
    n = n.removeprefix(short_type(m)).strip("_")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)


def sources():
    """(kind, id) -> (model type, model name) -> {"first": first model, "tiers": {verdict: [tier keys]}} over towers, heroes,
    powers and Geraldo items, lowest tier first."""
    out = {}
    folders = [("towers", "Towers"), ("heroes", "Heroes"), ("powers", "Powers"), ("geraldo", "GeraldoItems")]
    for kind, folder in folders:
        files = [f for f in (DATA / folder).rglob("*.json")]
        for f in sorted(files, key=lambda f: (f.parent.name, len(tier_key(f)), tier_key(f))):
            oid = f.parent.name if kind in ("towers", "heroes") else f.stem
            found = []

            def walk(o):
                if isinstance(o, dict):
                    if short_type(o) in INCOME_RU:
                        found.append(o)
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(load(f))
            for m in found:
                e = out.setdefault((kind, oid), {}).setdefault((short_type(m), model_name(m)), {"first": m, "tiers": {}})
                tiers = e["tiers"].setdefault(verdict(m), [])
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


def build_coop():
    # starting cash: the co-op mode's base split evenly, one extra dollar to the first players for a remainder
    # (Simulation init at 0xB44DF0..0xB44E79)
    start_rows = []
    for n in (2, 3, 4):
        row = [n]
        for mode in ("Standard", "Deflation"):
            f = DATA / "Mods" / f"Coop{mode}Cash{n}.json"
            base = next((m.get("changeBase") for m in load(f).get("mutatorMods", []) if short_type(m) == "StartingCashModModel"), None) if f.exists() else None
            row.append(f"${fmt(base)} → ${fmt(int(base) // n)}" + (f" (+1 первым {int(base) % n})" if base and int(base) % n else "") if base else "–")
        start_rows.append(row)
    rules = table(["Откуда", "В коопе", "Основание"], [
        ["Стартовые деньги", "делятся поровну", "Код игры: база режима делится на число игроков"],
        ["Деньги за лопание шаров", "делятся поровну", "Код игры: Simulation.UpdateStagedCash → AddSharedCash"],
        ["Бонус в конце раунда (100 + номер раунда)", "делится поровну", "Код игры: AddSharedCash (EndOfRound)"],
        ["Перевод денег другому игроку", "напрямую от игрока игроку", "Код игры: Simulation.SendCash"],
    ])
    rows = []
    for (kind, oid), types in sources().items():
        for (k, name), e in types.items():
            who = "<br>".join(f"<b>{esc(v)}</b>" + (f" <small class='note'>{esc(tier_text(kind, keys))}</small>" if tier_text(kind, keys) else "")
                              for v, keys in e["tiers"].items())
            what = effect_line(e["first"]).replace(f"<b>{esc(EFFECT_RU.get(k) or label(k))}</b>", f"<b>{esc(INCOME_RU[k])}</b>" + (f" <small class='note'>{esc(name)}</small>" if name else ""), 1)
            rows.append((Raw(source_badge(kind, oid)), Raw(what), Raw(who)))
    body = (card("rules", "Общие правила", rules
                 + "<p class='note'>Правила прочитаны в коде игры (GameAssembly.dll версии 57.4): в выгрузке данных их нет. "
                 "При 2, 3 и 4 игроках доля без других модификаторов: половина, треть, четверть.</p>"
                 + table(["Игроков", "Стандарт: база → на игрока", "Deflation: база → на игрока"], start_rows), section="Кооп")
            + card("sources", "Доход башен, героев и сил",
                   "<p class='note'>«Делится» и «владельцу» взяты из флага модели (distributeCash, distributeBonusIncome). "
                   "«Не проверено»: у модели нет такого флага, а путь денег в коде игры ещё не прослежен. Числа из "
                   "первого тира, где источник появляется.</p>"
                   "<input class='filter' type='search' placeholder='Фильтр: башня или источник' aria-label='Фильтр источников' "
                   "data-filter='#coop-src tbody tr'>"
                   + table(["Источник", "Что даёт", "В коопе"], rows).replace("<table>", "<table id='coop-src'>", 1), section="Кооп"))
    page("coop.html", "Деньги в коопе", "Откуда приходят деньги и делятся ли они между игроками в кооперативе.", body,
         [("rules", "Общие правила"), ("sources", "Доход башен, героев и сил")])
