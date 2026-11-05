"""Shared state and helpers: paths, game data loading, languages, HTML building blocks, page shell, icons."""
import base64
import functools
import html
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent  # repo root: data/, style.css, site.js, site/
DATA = ROOT / "data"
SITE = ROOT / "site"

# Asset references, visuals and physics carry no gameplay numbers
SKIP_TYPES = ("ResourceUtils", "DisplayModel", "AudioClip", "SMath.Vector", "CollisionGroup",
              "PopEffectModel", "CreateSoundOn", "AnimDamageState", "SpawnDeathAnim", "ShowDamageText",
              "PlayAnimTrigger")
SKIP_KEYS = {"$type", "guidRef", "AssetGUID", "display", "icon", "iconSmall", "name", "_name"}

PAGES = [
    ("index.html", "Главная", ""),
    # your side, then the enemy, then the match rules, then account-wide extras
    ("towers.html", "Башни", "Улучшения и кроссапгрейды"),
    ("heroes.html", "Герои", "Уровни и опыт"),
    ("paragon.html", "Парагон", "Сила и степени"),
    ("buffs.html", "Баффы", "Что стакается"),
    ("bloons.html", "Шары", "Свойства, HP и дети"),
    ("rounds.html", "Раунды", "Состав, RBE и деньги"),
    ("bosses.html", "Боссы", "HP и механики по тирам"),
    ("modes.html", "Режимы", "Модификаторы сложностей"),
    ("income.html", "Доход", "Множители дохода по раундам"),
    ("knowledge.html", "Monkey Knowledge", "Цены и эффекты"),
    ("powers.html", "Силы", "Параметры сил"),
    ("links.html", "Ссылки", "Вики, моды, сообщество"),
]

CSS = (ROOT / "style.css").read_text(encoding="utf-8")

SEARCH_JS = (ROOT / "site.js").read_text(encoding="utf-8")

# Readable labels for model types whose meaning is clear from the name
TYPE_LABELS = {
    "AttackModel": "Атака",
    "AttackAirUnitModel": "Атака с воздуха",
    "StartingCashModModel": "Стартовые деньги",
    "LockTowerSetModModel": "Запрет категории башен",
    "EndRoundModModel": "Последний раунд",
    "MonkeyMoneyModModel": "Monkey Money за победу",
    "StartingHealthModModel": "Стартовые жизни",
    "StartingRoundModModel": "Стартовый раунд",
    "SellMultiplierModModel": "Доля при продаже",
    "BonusCashPerRoundModModel": "Бонус за раунд",
    "GlobalCostModModel": "Множитель цен",
    "MaxHealthModModel": "Максимум жизней",
    "LockTowerModModel": "Запрет башни",
    "GlobalSpeedModModel": "Скорость шаров",
    "DisableContinueModModel": "Без продолжения",
    "SetHealthForBloonModModel": "HP шара",
    "RoundSetModModel": "Набор раундов",
    "RemoveManaShieldModModel": "Без щита маны",
    "DisableSellTowerModModel": "Без продажи",
    "DisableMonkeyKnowledgeModModel": "Без обезьяньих знаний",
    "BloonHealthModel": "HP шаров",
    "ModifyAllCashModModel": "Весь доход",
    "HealSelfActionModel": "Самолечение",
    "SetSpeedPercentActionModel": "Скорость (доля)",
    "SpawnBloonsActionModel": "Спавн шаров",
    "LychTombstoneSpawnActionModel": "Спавн надгробий",
    "AbsorbTowerBuffsActionModel": "Снятие баффов с башен",
    "DistributeCashModel": "Деньги за урон",
    "WorthReductionModel": "Снижение стоимости",
}

INDEX = []  # [title, section, url, extra search text]
JS_VER = __import__("hashlib").md5(SEARCH_JS.encode()).hexdigest()[:8]  # cache-bust search.js when the script changes


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# game.json from btd6-knowledge-dumper (F6 in game): version, shop order, bloon property bits
GAME = load(DATA / "KnowledgeLayout" / "game.json")
# the numbers come from the Mod Helper export, so its version (VERSION.txt) is the one shown
VERSION = (DATA / "VERSION.txt").read_text(encoding="utf-8").strip()
if not VERSION.startswith(GAME["version"] + " "):
    print(f"warning: game is {GAME['version']}, data export is {VERSION}: export again", file=sys.stderr)

# Languages: Russian is written in the code; other languages translate the finished HTML with a phrase
# dictionary (i18n_<lang>.json) and take game names/descriptions from data/textTable.<lang>.json.
LANGS = {"ru": "textTable.json", "en": "textTable.en.json"}
MAIN_LANG = "en"  # served at the site root; the other language lives in /<lang>/
LANG, OUT, TEXT, PHRASES = "ru", SITE, {}, None


def set_lang(lang):
    global LANG, OUT, PHRASES
    LANG = lang
    OUT = SITE if lang == MAIN_LANG else SITE / lang
    table = DATA / LANGS[lang]
    if not table.exists():
        print(f"warning: {table.name} missing, {lang} uses Russian game text", file=sys.stderr)
        table = DATA / LANGS["ru"]
    TEXT.clear()  # in place: other modules hold this dict
    TEXT.update(load(table))
    PHRASES = None
    if lang != "ru":
        words = load(ROOT / f"i18n_{lang}.json")
        keys = sorted(words, key=len, reverse=True)
        # whole phrases only: no Cyrillic letter right before or after the match
        cyr = "А-Яа-яЁё"
        # a phrase that starts/ends with a letter must not be glued to another letter (so "да" never hits "даёт")
        alts = [("(?<![" + cyr + "])" if re.match(f"[{cyr}]", k) else "") + re.escape(k)
                + ("(?![" + cyr + "])" if re.search(f"[{cyr}]$", k) else "") for k in keys]
        first = "".join(sorted({re.escape(k[0]) for k in keys}))
        # the leading class lets the engine skip non-matching positions (base64 icons) without trying every phrase
        PHRASES = (re.compile(f"(?=[{first}])(?:" + "|".join(f"(?:{a})" for a in alts) + ")"), words)


def translate(text):
    if PHRASES is None:
        return text
    pattern, words = PHRASES
    return pattern.sub(lambda m: words[m.group(0)], text)


def t(*keys, fallback=""):
    """First localized string found among keys, from the game's own text table."""
    for key in keys:
        value = TEXT.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("-\n", "-")  # game wraps some names: "Супер-\nобезьяна"
    return fallback


def esc(x):
    return html.escape(str(x))


def short_type(obj):
    full = obj.get("$type", "") if isinstance(obj, dict) else ""
    return full.split(",")[0].split(".")[-1] if full else ""


MOD_LABELS_RU = {  # generic knowledge/mode modifiers; RU pages only, EN falls back to the split type name
    "AbilityCooldownPercentageModModel": "Перезарядка способностей, %", "AbilityCooldownTimeModModel": "Перезарядка способностей",
    "ActivateAttackModModel": "Включает атаку", "AddAbilityToTowerModModel": "Добавляет способность",
    "BloonHealthModModel": "HP шаров", "CashIncreaseModModel": "Больше денег", "CashModModel": "Деньги",
    "CashPerRoundModModel": "Деньги за раунд", "ChimpsModModel": "Правила CHIMPS", "DeflationModel": "Правила Deflation",
    "ImpoppableModel": "Правила Impoppable", "ReverseModel": "Обратный путь",
    "DamageModifierForBloonTypeModModel": "Урон по типу шаров", "DamageModifierForTagModModel": "Урон по тегу",
    "DamageOverTimeModModel": "Урон со временем", "DamageTypeModModel": "Тип урона", "FreeTowerModModel": "Бесплатная башня",
    "FreezeModifierModModel": "Заморозка", "GrantCamoDetectForAbilityModModel": "Видит камуфляж в способности",
    "HeroCostToLevelModModel": "Цена прокачки героя", "HeroXPBonusModModel": "Бонус опыта героя",
    "HeroXpInjectionModModel": "Опыт герою", "IgnoreBlockersModModel": "Сквозь препятствия",
    "IgnoreImmunityForBloonTypeModModel": "Без иммунитета шаров", "IncreaseRangeModModel": "Дальность",
    "KnockbackModModel": "Отбрасывание", "LivesModModel": "Жизни",
    "OnMonkeyKnowledgePurchaseModModel": "При покупке знания", "PowerModModel": "Сила",
    "ProjectilePierceModModel": "Пробивание снарядов", "ProjectileRadiusModModel": "Радиус снарядов",
    "ProjectileRangePercentageModModel": "Дальность снарядов, %", "ProjectileSpeedModModel": "Скорость снарядов",
    "ProjectileTrackTargetModModel": "Самонаведение", "PushBackIncreaseModModel": "Сильнее отбрасывание",
    "RangeModModel": "Дальность", "RetargetIncreaseModModel": "Перенацеливание", "SimTowerDiscountModModel": "Скидка на башни",
    "SlowModifierForTagModModel": "Замедление по тегу", "SlowModifierModModel": "Замедление",
    "StartingShieldModModel": "Стартовый щит", "SupportMaxRangeModModel": "Дальность поддержки",
    "TierFiveCountModModel": "Число башен 5-го тира", "TowerExpireModModel": "Время жизни башни",
    "TowerSellModModel": "Продажа башни", "TowerXpModModel": "Опыт башен", "UpgradeCostModModel": "Цена улучшений",
    "WeaponReloadPercentageModModel": "Перезарядка, %", "WeaponReloadPercentageOnTargetPrioModModel": "Перезарядка по приоритету",
    "WeaponReloadReductionModModel": "Быстрее перезарядка", "EmissionArcCountModModel": "Число снарядов в дуге",
}


def label(type_name):
    if type_name in TYPE_LABELS:
        return TYPE_LABELS[type_name]
    if LANG == "ru" and type_name in MOD_LABELS_RU:
        return MOD_LABELS_RU[type_name]
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", re.sub(r"Model$", "", type_name))


def skipped(value):
    return isinstance(value, dict) and any(s in value.get("$type", "") for s in SKIP_TYPES)


class Raw(str):
    """Ready HTML that fmt() passes through unescaped."""


def fmt(value):
    if isinstance(value, Raw):
        return value
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,}".replace(",", " ")
        s = f"{value:,.6g}"
        return (f"{value:.8f}".rstrip("0") if "e" in s else s).replace(",", " ")  # no 9e-05 in tables
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return esc(value)


def scalar(value):
    return isinstance(value, (str, int, float, bool))


def flatten(obj, prefix="", out=None):
    """Scalar leaves of a model as {readable.path: value}, skipping visuals and asset refs."""
    out = {} if out is None else out
    if not isinstance(obj, dict) or skipped(obj):
        return out
    counts = {}
    for key, value in obj.items():
        if key in SKIP_KEYS or value is None or skipped(value):
            continue
        if key[:1].isupper() and (key[:1].lower() + key[1:]) in obj:
            continue  # Il2Cpp duplicates (speed / Speed)
        path = f"{prefix}{key}"
        if scalar(value):
            out[path] = value
        elif isinstance(value, list) and value and all(scalar(v) for v in value):
            out[path] = ", ".join(str(v) for v in value)
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, dict) or skipped(item):
                    continue
                name = short_type(item) or key
                counts[name] = counts.get(name, 0) + 1
                tag = name if counts[name] == 1 else f"{name}#{counts[name]}"
                flatten(item, f"{prefix}{tag}.", out)
        elif isinstance(value, dict):
            flatten(value, f"{path}.", out)
    return out


def kv_table(pairs):
    rows = "".join(f"<tr><td class='k'>{esc(k)}</td><td class='n'>{fmt(v)}</td></tr>" for k, v in pairs)
    return f"<div class='wrap'><table>{rows}</table></div>"


def table(headers, rows, row_attr=""):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(f"<tr{row_attr}>" + "".join(
        f"<td class='n'>{fmt(c)}</td>" if isinstance(c, (int, float)) and not isinstance(c, bool)
        else f"<td>{c if isinstance(c, str) else fmt(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<div class='wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def stats(items):
    return "<div class='stats'>" + "".join(
        f"<div class='stat'><b>{fmt(v)}</b><small>{esc(k)}</small></div>" for k, v in items) + "</div>"


def game_text(text):
    text = re.sub(r"</?(sup|sub|b|i|u)>|</?color[^>]*>", "", text or "")  # game rich-text tags
    return f"<div class='game'>{esc(text)}</div>" if text else ""


def card(anchor, title, body, en_id="", tagline="", section=""):
    INDEX.append([title, section, f"{current_file}#{anchor}", en_id])
    head = (f"<div class='card-head'><h2>{esc(title)}</h2>"
            + (f"<span class='tag'>{esc(tagline)}</span>" if tagline else "")
            + (f"<span class='id'>{esc(en_id)}</span>" if en_id and en_id != title else "") + "</div>")
    return f"<section class='card' id='{esc(anchor)}'>{head}{body}</section>"


current_file = "index.html"


def page(file, title, lead, body, toc=()):
    side = "".join(f"<a href='{f}'{' class=on' if f == file else ''}>{esc(t(n, fallback=n))}</a>" for f, n, _ in PAGES)
    other = ("ru/" if LANG == MAIN_LANG else "../") + file
    switch = f"<a class='lang' href='{other}' aria-label='Язык'>{'RU' if LANG == MAIN_LANG else 'EN'}</a>"
    toc_html = ("<div class='toc'><h4>На странице</h4>" + "".join(
        f"<a href='#{esc(a)}'>{esc(n)}</a>" for a, n in toc) + "</div>") if toc else ""
    head = (f"<meta charset=\"utf-8\"><title>{'BTD6 Tech Wiki' if file == 'index.html' else esc(title) + ' · BTD6 Tech Wiki'}</title>"
            "<meta name=\"claude:viewport-fit-sides\" content=\"cover\">"
            "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400"
            "&family=Roboto+Mono&display=swap\">"
            f"<style>{CSS}</style>")
    content = (
        f"<header class='top'><a class='brand' href='index.html'>BTD6 Tech Wiki<span title='{esc(VERSION)}'>"
        f"{esc(VERSION.split(' ')[0])}</span></a>"
        "<div class='search'><input id='q' type='search' placeholder='Поиск: босс, режим, знание, сила…  ( / )' "
        "autocomplete='off' aria-label='Поиск по вики'><div class='results' id='qr' hidden></div></div>"
        f"{switch}</header>"
        f"<div class='layout'><aside class='side'><h4>Разделы</h4><nav>{side}</nav>{toc_html}</aside>"
        f"<main class='page-{file.removesuffix('.html')}'><h1>{esc(title)}</h1><p class='lead'>{lead}</p>"
        f"{body}<footer class='foot'>Неофициальная фанатская вики, без монетизации. Данные, названия, тексты и изображения "
        "принадлежат <a href='https://ninjakiwi.com' rel='noopener'>Ninja Kiwi</a>. Данные выгружены через "
        "<a href='https://github.com/gurrenm3/BTD-Mod-Helper' rel='noopener'>BTD6 Mod Helper</a>, иконки из спрайтов игры. "
        "<a href='https://github.com/Antonzlo/btd6-tech-wiki' rel='noopener'>Исходный код</a>. Сделано с ♥ <a href='https://github.com/Antonzlo' rel='noopener'>Antonzlo</a>.</footer>"
        f"</main></div><script src='search.js?v={JS_VER}'></script>")
    # the artifact page itself is a fragment (the host adds the skeleton); --pages builds plain files for GitHub Pages
    if file == "index.html" and LANG == MAIN_LANG and "--pages" not in sys.argv:
        doc = head + content
    else:
        doc = (f"<!doctype html><html lang=\"{LANG}\"><head>"
               f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
               f"{head}</head><body>{content}</body></html>")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / file).write_text(translate(doc), encoding="utf-8")


def json_files(folder):
    return sorted((DATA / folder).rglob("*.json"))


def group(gid, title, cards):
    """A titled section whose small cards sit two per row on wide screens."""
    return f"<h2 class='group' id='{esc(gid)}'>{esc(title)}</h2><div class='cards'>{''.join(cards)}</div>"


@functools.cache
def webp_uri(f):
    """data: URI of a webp file, or "" when it is missing (pages cannot load images from other hosts)."""
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def sort_bar(grid_id, options):
    """Buttons that reorder the tiles of #grid_id by a numeric data-<key>; the first option is the initial order.
    The "order" key also lays the grid out in 3 columns, like the game's hero select screen."""
    return (f"<div class='tagbar sortbar' data-grid='{grid_id}'>"
            + "".join(f"<button type='button' data-sort='{k}'{' class=on' if i == 0 else ''}>{esc(n)}</button>"
                      for i, (k, n) in enumerate(options)) + "</div>")


# ---------- icons (game sprites via tools/game_icons.sh: data/icons/web/<kind>/<id>.webp) ----------

def data_uri(kind, oid):
    # file names keep [A-Za-z0-9_-] of the id, like the dumper mod writes them
    return webp_uri(DATA / "icons" / "web" / kind / (re.sub(r"[^A-Za-z0-9_-]", "_", oid) + ".webp"))


def icon(kind, oid, size, cls="ic"):
    """Inline <img> for an icon, or "" when there is none."""
    uri = data_uri(kind, oid)
    return f"<img class='{cls}' src='{uri}' width='{size}' height='{size}' alt='' loading='lazy'>" if uri else ""


PAGE_ICONS = {"paragon.html": ("ui", "paragon"), "bosses.html": ("ui", "boss-Bloonarius"), "modes.html": ("ui", "mode-Clicks"),
              "income.html": ("ui", "coin"), "buffs.html": ("towers", "MonkeyVillage"), "knowledge.html": ("ui", "knowledge"),
              "powers.html": ("ui", "powers"), "towers.html": ("towers", "DartMonkey"), "rounds.html": ("ui", "startround"),
              "bloons.html": ("bloons", "Red"), "heroes.html": ("heroes", "Quincy")}


def page_icon(file, size):
    spec = PAGE_ICONS.get(file)
    return icon(spec[0], spec[1], size) if spec else ""


def bloon_css(b):
    return re.sub(r"[^A-Za-z0-9]", "", b)


def bloon_icon_style(ids):
    """One CSS class per bloon icon, so a page with hundreds of chips embeds each image once."""
    rules = "".join(f".bi-{bloon_css(b)}{{background-image:url({data_uri('bloons', b)})}}" for b in sorted(ids) if data_uri("bloons", b))
    return f"<style>{rules}</style>"


# ---------- towers (game constants shared by several pages) ----------

# monkey tower categories: the single-bit TowerSet values inside AllMonkeyTowerSets (game.json), bit -> name
TOWER_SETS = {v: k for k, v in GAME["towerSets"].items()
              if v and v & (v - 1) == 0 and v & GAME["towerSets"]["AllMonkeyTowerSets"]}
# shop order: GameModel.towerSet from game.json. Towers missing from data/Towers are skipped by the pages.
SHOP_ORDER = [t["id"] for t in sorted(GAME["towerSet"], key=lambda t: t["index"])]
