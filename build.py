"""Build the BTD6 tech wiki (static HTML) from a Mod Helper "Export Game Data" dump.

Usage: python3 -I build.py            (reads ./data, writes ./site)
Refresh data: copy Bosses Bloons Mods IncomeSets Buffs Knowledge Powers
paragonDegreeData.json textTable.json from the export folder into ./data
and the KnowledgeLayout folder written by btd6-knowledge-dumper (F6 in game, gives game.json too).
"""
import html
import base64
import collections
import datetime
import functools
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SITE = ROOT / "site"

# Asset references, visuals and physics carry no gameplay numbers
SKIP_TYPES = ("ResourceUtils", "DisplayModel", "AudioClip", "SMath.Vector", "CollisionGroup",
              "PopEffectModel", "CreateSoundOn", "AnimDamageState", "SpawnDeathAnim", "ShowDamageText",
              "PlayAnimTrigger")
SKIP_KEYS = {"$type", "guidRef", "AssetGUID", "display", "icon", "iconSmall", "name", "_name"}

PAGES = [
    ("index.html", "Главная", ""),
    ("paragon.html", "Парагон", "Сила и степени"),
    ("bosses.html", "Боссы", "HP и механики по тирам"),
    ("modes.html", "Режимы", "Модификаторы сложностей"),
    ("income.html", "Доход", "Множители дохода по раундам"),
    ("buffs.html", "Баффы", "Что стакается"),
    ("knowledge.html", "Monkey Knowledge", "Цены и эффекты"),
    ("powers.html", "Силы", "Параметры сил"),
    ("towers.html", "Башни", "Улучшения и кроссапгрейды"),
    ("bloons.html", "Шары", "Свойства, HP и дети"),
    ("rounds.html", "Раунды", "Состав, RBE и деньги"),
]

CSS = (ROOT / "style.css").read_text(encoding="utf-8")

SEARCH_JS = """
(function(){
var box=document.getElementById('q'),out=document.getElementById('qr');if(!box)return;var sel=0,hits=[];
function norm(s){return s.toLowerCase().replace(/ё/g,'е')}
function draw(){out.innerHTML='';hits.forEach(function(h,i){var a=document.createElement('a');a.href=h[2];
if(i===sel)a.className='sel';var s=document.createElement('span');s.textContent=h[0];var m=document.createElement('small');
m.textContent=h[1];a.appendChild(s);a.appendChild(m);out.appendChild(a)});out.hidden=!hits.length}
box.addEventListener('input',function(){var q=norm(box.value.trim());sel=0;
hits=q?WIKI_INDEX.filter(function(e){return norm(e[0]+' '+e[3]).indexOf(q)>=0}).slice(0,14):[];draw()});
box.addEventListener('keydown',function(e){if(!hits.length)return;if(e.key==='ArrowDown'){sel=Math.min(sel+1,hits.length-1);draw();e.preventDefault()}
else if(e.key==='ArrowUp'){sel=Math.max(sel-1,0);draw();e.preventDefault()}else if(e.key==='Enter'){location.href=hits[sel][2]}
else if(e.key==='Escape'){hits=[];draw()}});
document.addEventListener('click',function(e){if(!e.target.closest('.search')){hits=[];draw()}});
document.addEventListener('keydown',function(e){if(e.key==='/'&&document.activeElement!==box&&!/INPUT|TEXTAREA/.test(document.activeElement.tagName)){box.focus();e.preventDefault()}});
document.querySelectorAll('[data-filter]').forEach(function(f){var rows=document.querySelectorAll(f.dataset.filter);
f.addEventListener('input',function(){var q=norm(f.value);rows.forEach(function(r){r.dataset.th=q&&norm(r.textContent).indexOf(q)<0?'1':'';r.hidden=!!(r.dataset.th||r.dataset.gh)})})});
document.querySelectorAll('.tagbar').forEach(function(bar){var rows=document.querySelectorAll(bar.dataset.target+' tbody tr');bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){bar.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});var tag=b.dataset.tag;rows.forEach(function(r){r.dataset.gh=tag&&(' '+r.dataset.tags+' ').indexOf(' '+tag+' ')<0?'1':'';r.hidden=!!(r.dataset.th||r.dataset.gh)})})})});
document.querySelectorAll('.kgraph').forEach(function(g){var nodes={};g.querySelectorAll('.kn').forEach(function(n){nodes[n.dataset.id]=n});
function chain(id,acc){if(acc[id]||!nodes[id])return acc;acc[id]=1;(nodes[id].dataset.req||'').split(' ').filter(Boolean).forEach(function(p){chain(p,acc)});return acc}
function clear(){g.classList.remove('dim');g.querySelectorAll('.lit').forEach(function(e){e.classList.remove('lit')})}
function light(id){clear();var on=chain(id,{});g.classList.add('dim');Object.keys(on).forEach(function(k){nodes[k].classList.add('lit')});
g.querySelectorAll('.edge').forEach(function(e){if(on[e.dataset.from]&&on[e.dataset.to])e.classList.add('lit')})}
Object.keys(nodes).forEach(function(id){var n=nodes[id];n.addEventListener('mouseenter',function(){light(id)});
n.addEventListener('focus',function(){light(id)});n.addEventListener('mouseleave',clear);n.addEventListener('blur',clear)});var tip=g.querySelector('.ktip');if(tip)Object.keys(nodes).forEach(function(id){var n=nodes[id];n.addEventListener('mouseenter',function(){var b=n.getBoundingClientRect();tip.innerHTML='';var t=document.createElement('b');t.textContent=n.dataset.name;var c=document.createElement('small');c.textContent=n.dataset.cost+' MM';tip.appendChild(t);if(n.dataset.desc){var p=document.createElement('p');p.textContent=n.dataset.desc;tip.appendChild(p)}tip.appendChild(c);tip.hidden=false;var top=b.top-tip.offsetHeight-6;if(top<70)top=b.bottom+6;tip.style.left=Math.max(8,Math.min(innerWidth-tip.offsetWidth-8,b.left+b.width/2-tip.offsetWidth/2))+'px';tip.style.top=top+'px'});n.addEventListener('mouseleave',function(){tip.hidden=true})})});

var DIFF_KEY='btd6-diff';function curMult(){try{return +localStorage.getItem(DIFF_KEY)||1}catch(x){return 1}}
function applyDiff(){var m=curMult();document.querySelectorAll('.diff button').forEach(function(b){b.classList.toggle('on',+b.dataset.mult===m)});
document.querySelectorAll('.cost[data-parts]').forEach(function(el){var s=el.dataset.parts.split(',').reduce(function(a,p){return a+(m===1?+p:Math.round(p*m/5)*5)},0);
el.textContent='$'+s.toLocaleString('ru-RU')})}
document.querySelectorAll('.diff button').forEach(function(b){b.addEventListener('click',function(){try{localStorage.setItem(DIFF_KEY,b.dataset.mult)}catch(x){}applyDiff()})});
applyDiff();
document.querySelectorAll('.xp').forEach(function(xp){var data=JSON.parse(xp.parentNode.querySelector('.xp-data').textContent),
st=[0,0,0],variant=null,out=xp.querySelector('.xp-out');
function e(s){return String(s==null?'–':s).replace(/[&<>"']/g,function(c){return'&#'+c.charCodeAt(0)+';'})}
function f(v){if(v==null)return'–';if(typeof v==='number')return(Math.round(v*1e4)/1e4).toLocaleString('ru-RU');return e(v)}
function key(){return st.join('')}
function fix(changed){if(data[key()])return;for(var i=0;i<3;i++){if(i===changed)continue;while(st[i]>0&&!data[key()])st[i]--}
if(!data[key()]){for(var j=0;j<3;j++)if(j!==changed)st[j]=0}}
function draw(){var k=variant||key(),d=data[k];xp.querySelectorAll('.xp-row[data-path]').forEach(function(r){var p=+r.dataset.path;
r.querySelectorAll('button').forEach(function(b){b.classList.toggle('on',!variant&&+b.dataset.tier===st[p])})});
xp.querySelectorAll('[data-variant]').forEach(function(b){b.classList.toggle('on',b.dataset.variant===variant)});
if(!d){out.innerHTML='<p class="note">Нет данных для '+e(k)+'.</p>';return}
var h='<div class="stats"><div class="stat"><b class="cost" data-parts="'+d.parts.join(',')+'">$'+f(d.cost)+'</b><small>цена '+e(k)+'</small></div><div class="stat"><b>'+f(d.range)+'</b><small>дальность</small></div></div>';
d.attacks.forEach(function(a,ai){h+='<h3>'+e(a.name)+' <span class="id">дальность '+f(a.range)+'</span></h3><div class="wrap"><table><thead><tr><th>Оружие</th><th>Перезарядка, с</th><th>Атак/с</th><th>Снаряд</th><th>Кол-во</th><th>Урон</th><th>Пробив.</th><th>Модификаторы и эффекты</th></tr></thead><tbody>';
a.weapons.forEach(function(w,wi){var n=Math.max(1,w.proj.length);w.proj.forEach(function(p,pi){h+='<tr>'+(pi===0?'<td rowspan="'+n+'">'+(wi+1)+(w.emission?' <span class="id">'+e(w.emission)+'</span>':'')+'</td><td class="n" rowspan="'+n+'">'+f(w.rate)+'</td><td class="n" rowspan="'+n+'">'+(w.rate?f(1/w.rate):'–')+'</td>':'')
+'<td style="padding-left:'+(10+p.depth*16)+'px">'+(p.depth?'↳ ':'')+e(p.label)+'</td><td class="n">'+f(p.count)+'</td><td class="n">'+f(p.damage)+'</td><td class="n">'+f(p.pierce)+'</td><td>'
+p.mods.concat(p.effects).map(function(m){return'<span class="chip">'+e(m)+'</span>'}).join(' ')+'</td></tr>'});
if(!w.proj.length)h+='<tr><td>'+(wi+1)+'</td><td class="n">'+f(w.rate)+'</td><td class="n">'+(w.rate?f(1/w.rate):'–')+'</td><td colspan="5">–</td></tr>'});
h+='</tbody></table></div>'});
if(d.abilities.length)h+='<h3>Способности</h3><div class="chips">'+d.abilities.map(function(a){return'<span class="chip">'+e(a.name)+', перезарядка '+f(a.cooldown)+' с</span>'}).join('')+'</div>';
if(d.other.length)h+='<h3>Прочие поведения</h3><div class="chips">'+d.other.map(function(o){return'<span class="chip">'+e(o)+'</span>'}).join('')+'</div>';
out.innerHTML=h;applyDiff()}
xp.querySelectorAll('.xp-row[data-path] button').forEach(function(b){b.addEventListener('click',function(){var p=+b.parentNode.dataset.path;variant=null;st[p]=+b.dataset.tier;fix(p);draw()})});
xp.querySelectorAll('[data-variant]').forEach(function(b){b.addEventListener('click',function(){variant=b.dataset.variant;draw()})});
draw()});
function openTarget(){var id=decodeURIComponent(location.hash.slice(1));if(!id)return;var el=document.getElementById(id);if(!el)return;var d=el.closest('details');if(d&&!d.open){d.open=true;el.scrollIntoView()}}
window.addEventListener('hashchange',openTarget);openTarget();
})();
"""

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
GAME_JSON = DATA / "KnowledgeLayout" / "game.json"
GAME = load(GAME_JSON) if GAME_JSON.exists() else {}
VERSION = (f"{GAME['version']} (дамп {datetime.date.fromtimestamp(GAME_JSON.stat().st_mtime)})" if GAME
           else (DATA / "VERSION.txt").read_text(encoding="utf-8").strip())

# Languages: Russian is written in the code; other languages translate the finished HTML with a phrase
# dictionary (i18n_<lang>.json) and take game names/descriptions from data/textTable.<lang>.json.
LANGS = {"ru": "textTable.json", "en": "textTable.en.json"}
LANG, OUT, TEXT, PHRASES = "ru", SITE, {}, None


def set_lang(lang):
    global LANG, OUT, TEXT, PHRASES
    LANG = lang
    OUT = SITE if lang == "ru" else SITE / lang
    table = DATA / LANGS[lang]
    if not table.exists():
        print(f"warning: {table.name} missing, {lang} uses Russian game text", file=sys.stderr)
        table = DATA / LANGS["ru"]
    TEXT = load(table)
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
            return value.strip()
    return fallback


def esc(x):
    return html.escape(str(x))


def short_type(obj):
    full = obj.get("$type", "") if isinstance(obj, dict) else ""
    return full.split(",")[0].split(".")[-1] if full else ""


def label(type_name):
    if type_name in TYPE_LABELS:
        return TYPE_LABELS[type_name]
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
        return f"{value:,.6g}".replace(",", " ")
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
    other = ("en/" if LANG == "ru" else "../") + file
    switch = f"<a class='lang' href='{other}' aria-label='Язык'>{'EN' if LANG == 'ru' else 'RU'}</a>"
    toc_html = ("<div class='toc'><h4>На странице</h4>" + "".join(
        f"<a href='#{esc(a)}'>{esc(n)}</a>" for a, n in toc) + "</div>") if toc else ""
    head = (f"<meta charset=\"utf-8\"><title>{'BTD6 Tech Wiki' if file == 'index.html' else esc(title) + ' · BTD6 Tech Wiki'}</title>"
            "<meta name=\"claude:viewport-fit-sides\" content=\"cover\">"
            "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400"
            "&family=Roboto+Mono&display=swap\">"
            f"<style>{CSS}</style>")
    content = (
        "<header class='top'><a class='brand' href='index.html'>BTD6 Tech Wiki<span>"
        f"{esc(VERSION.split(' ')[0])}</span></a>"
        "<div class='search'><input id='q' type='search' placeholder='Поиск: босс, режим, знание, сила…  ( / )' "
        "autocomplete='off' aria-label='Поиск по вики'><div class='results' id='qr' hidden></div></div>"
        f"{switch}</header>"
        f"<div class='layout'><aside class='side'><h4>Разделы</h4><nav>{side}</nav>{toc_html}</aside>"
        f"<main class='page-{file.removesuffix('.html')}'><h1>{esc(title)}</h1><p class='lead'>{lead}</p><p class='ver'>Данные: {esc(VERSION)}</p>"
        f"{body}<footer class='foot'>Неофициальная фанатская вики, без монетизации. Данные, названия, тексты и изображения "
        "принадлежат <a href='https://ninjakiwi.com' rel='noopener'>Ninja Kiwi</a>. Данные выгружены через "
        "<a href='https://github.com/gurrenm3/BTD-Mod-Helper' rel='noopener'>BTD6 Mod Helper</a>, иконки взяты из "
        "<a href='https://www.bloonswiki.com' rel='noopener'>Blooncyclopedia</a> (CC BY-NC-SA 4.0). "
        "<a href='https://github.com/Antonzlo/btd6-tech-wiki' rel='noopener'>Исходный код</a>.</footer>"
        f"</main></div><script src='search.js?v={JS_VER}'></script>")
    if file == "index.html" and LANG == "ru":  # the artifact page itself; the host adds the skeleton
        doc = head + content
    else:
        doc = (f"<!doctype html><html lang=\"{LANG}\"><head>"
               f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
               f"{head}</head><body>{content}</body></html>")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / file).write_text(translate(doc), encoding="utf-8")


def json_files(folder):
    return sorted((DATA / folder).rglob("*.json"))


# ---------- pages ----------

def build_paragon():
    d = load(DATA / "paragonDegreeData.json")
    req = d["powerDegreeRequirements"]
    top = req[-1]
    # line chart: power needed per degree
    w, h, pad = 640, 220, 36
    pts = " ".join(f"{pad + (w - 2 * pad) * i / (len(req) - 1):.1f},{h - pad - (h - 2 * pad) * p / top:.1f}"
                   for i, p in enumerate(req))
    ticks = "".join(
        f"<text x='{pad + (w - 2 * pad) * (deg - 1) / (len(req) - 1):.1f}' y='{h - pad + 16}' text-anchor='middle'>{deg}</text>"
        for deg in (1, 25, 50, 75, 100))
    yt = "".join(f"<text x='{pad - 6}' y='{h - pad - (h - 2 * pad) * v / top + 4:.1f}' text-anchor='end'>{v // 1000}k</text>"
                 for v in (0, top // 2, top))
    grid = "".join(f"<line class='pgrid' x1='{pad}' y1='{h - pad - (h - 2 * pad) * v / top:.1f}' x2='{w - pad}' "
                   f"y2='{h - pad - (h - 2 * pad) * v / top:.1f}'/>" for v in (top // 2, top))
    # one hover target per degree, wider than the line
    step = (w - 2 * pad) / (len(req) - 1)
    hits = "".join(f"<rect class='phit' x='{pad + step * i - step / 2:.1f}' y='{pad}' width='{step:.1f}' height='{h - 2 * pad}'>"
                   f"<title>{i + 1}: {fmt(p)}</title></rect>" for i, p in enumerate(req))
    chart = (f"<div class='wrap'><svg class='pchart' viewBox='0 0 {w} {h}' width='{w}' role='img' aria-label='Сила по степеням'>"
             f"{grid}<line class='paxis' x1='{pad}' y1='{h - pad}' x2='{w - pad}' y2='{h - pad}'/>"
             f"<polyline class='pline' points='{pts}'/>{ticks}{yt}{hits}</svg></div>")

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
         "Парагон получает степень от 1 до 100 по накопленной силе. Сила собирается из лопаний, потраченных денег "
         "и пожертвованных улучшений, у каждого источника свой потолок.",
         body, toc=[("curve", "Сила на степень"), ("sources", "Параметры")])


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
         "Каждый босс есть в 5 обычных и 5 элитных тирах. Для каждого: описание из игры, HP по тирам "
         "и все числовые параметры поведений, отдельно те, что растут с тиром.",
         "".join(body), toc)


def group(gid, title, cards):
    """A titled section whose small cards sit two per row on wide screens."""
    return f"<h2 class='group' id='{esc(gid)}'>{esc(title)}</h2><div class='cards'>{''.join(cards)}</div>"


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


def param(k, v):
    """A model parameter as a two-part badge; ids that have a page here link to it."""
    href, text, pic = None, fmt(v), ""
    if k == "towerSetToLock" and v in TOWER_SETS:
        href, text = f"towers.html#set-{TOWER_SETS[v]}", esc(t(TOWER_SETS[v], fallback=TOWER_SETS[v]))
        pic = icon("ui", TOWER_SETS[v], 18)
    elif k == "towerToLock" and (DATA / "Towers" / str(v)).is_dir():
        href, text, pic = f"tower-{v}.html", esc(t(v, fallback=v)), icon("towers", v, 18)
    elif k == "roundsetName" and (DATA / "Rounds" / str(v)).is_dir():
        href = f"rounds.html#{v}"
    elif k == "bloonId":
        text, pic = esc(t(v, fallback=v)), icon("bloons", v, 18)
    inner = f"<span>{esc(k)}</span><b>{pic}{text}</b>"
    return f"<a class='badge' href='{href}'>{inner}</a>" if href else f"<span class='badge'>{inner}</span>"


def mod_table(mods):
    """Mutator models as rows: icon + readable name, then their parameters as badges."""
    rows = [(Raw(f"<span class='mod-name'>{mod_icon(short_type(m))}{esc(label(short_type(m)))}</span>"),
             " ".join(param(k, v) for k, v in flatten(m).items() if v != "") or "–") for m in mods]
    return table(["Модификатор", "Параметры"], rows) if rows else "<p class='note'>Без модификаторов.</p>"


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
            name = t(f"Mode {stem}", stem, fallback=stem)
            key = {"PrimaryOnly": "Primary", "MilitaryOnly": "Military", "MagicOnly": "Magic"}.get(stem) or (
                "mode-Deflation" if stem.startswith("CoopDeflation") else "mode-Medium" if stem.startswith("CoopStandard")
                else f"mode-{stem}")
            pic = icon("ui", key, 96, "ic mode-ic")
            desc = t(f"et_{stem.lower()}description")
            if "{0}" in desc:  # Deflation: "start at round {0} with {1} cash", values from its own modifiers
                vals = {short_type(m): m for m in mods}
                desc = desc.replace("{0}", fmt(vals.get("StartingRoundModModel", {}).get("round", "?"))).replace(
                    "{1}", fmt(vals.get("StartingCashModModel", {}).get("changeBase", "?")))
            inner = (f"<div class='hero-row'>{pic}<div>" if pic else "<div><div>") + game_text(desc) + mod_table(mods) + "</div></div>"
            cards.append(card(stem, name, inner, en_id=stem, section="Режимы"))
        if cards:
            body.append(group(gid, title, cards))
            toc.append((gid, title))
    page("modes.html", "Режимы и сложности",
         "Режим это набор модификаторов поверх обычной игры: множители денег, HP, цен, запреты. "
         "Здесь все модификаторы каждого режима с точными значениями. Кооп-режимы CoopStandardCash и "
         "CoopDeflationCash задают деньги для 2, 3 и 4 игроков.",
         "".join(body), toc)


def build_income():
    body, toc = [], []
    # the normal game first, the rest alphabetically
    for f in sorted(json_files("IncomeSets"), key=lambda f: (f.stem != "DefaultIncomeSet", f.stem)):
        d = load(f)
        rows, start = [], 1
        for th in d.get("thresholds") or []:
            rows.append((f"{start}–{th['threshold']}", th["multiplier"], f"{th['multiplier'] * 100:g}%"))
            start = th["threshold"] + 1
        final = d.get("finalMultiplier")
        rows.append((f"{start}+", final, f"{final * 100:g}%" if final is not None else "–"))
        body.append(card(f.stem, f.stem, table(["Раунды", "Множитель", "От обычного"], rows), section="Доход"))
        toc.append((f.stem, f.stem))
    page("income.html", "Доход по раундам",
         "Деньги за лопание шаров умножаются на коэффициент, который зависит от номера раунда. "
         "DefaultIncomeSet используется в обычной игре, остальные в своих режимах.",
         f"<div class='cards'>{''.join(body)}</div>", toc)




@functools.cache
def buff_towers():
    """buffIconName or buffLocsName -> towers whose models carry it (the source tower's CanBuffIndicatorModel)."""
    out = {}
    for f in (DATA / "Towers").glob("*/*.json"):
        for name in set(re.findall(r'"buff(?:Icon|Locs)Name": "([^"]+)"', f.read_text(encoding="utf-8"))):
            out.setdefault(name, set()).add(f.parent.name)
    return out


def tower_badge(tid):
    return (f"<a class='badge' href='tower-{tid}.html'><span>башня</span>"
            f"<b>{icon('towers', tid, 18)}{esc(TEXT.get(tid, tid))}</b></a>")


def tower_of(icon_name, buff_name=""):
    """Source of a buff: towers whose data carry its icon, else a guess from the icon name (BuffIconAlchemist3xx),
    else towers carrying its buff name (checked last: heroes reuse tower buff names, e.g. BiggerRadiusBuff)."""
    found = buff_towers().get(icon_name)
    if found:
        return "".join(tower_badge(tid) for tid in sorted(found, key=lambda x: SHOP_ORDER.index(x) if x in SHOP_ORDER else 99))
    rest = icon_name.removeprefix("BuffIcon")
    for end in range(len(rest), 3, -1):
        word = rest[:end]
        if word[0].isupper() and (end == len(rest) or not rest[end].islower()) and isinstance(TEXT.get(word), str):
            if (DATA / "Towers" / word).is_dir():
                return tower_badge(word)
            return f"<span class='badge'><span>источник</span><b>{esc(TEXT[word])}</b></span>"
    return "".join(tower_badge(tid) for tid in sorted(buff_towers().get(buff_name, ())))


def flag(k, v, good=True):
    """Yes/no parameter badge; green when the value is the favourable one."""
    cls = "yes" if bool(v) == good else "no"
    return f"<span class='badge {cls}'><span>{esc(k)}</span><b>{fmt(v)}</b></span>"


def build_buffs():
    rows = []
    for f in json_files("Buffs"):
        d = load(f)
        name = d.get("iconName", "")
        pic = icon("buffs", name, 32, "ic buff-ic") or "<span class='buff-ic'></span>"
        buff = (f"<span class='mod-name'>{pic}"
                f"<span><span class='id'>{esc(d.get('buffName'))}</span><br><small class='note'>{esc(name)}</small></span></span>")
        stack = "<div class='stackgrid'>" + "".join([flag("stackable", d.get("stackable")), param("maxStackSize", "∞" if (d.get("maxStackSize") or 0) >= 2**31 - 1 else d.get("maxStackSize")),
                          flag("globalRange", d.get("globalRange"))]) + "</div>"
        rows.append((Raw(tower_of(name, d.get("buffName", ""))) or "–", Raw(buff), Raw(stack)))
        INDEX.append([d.get("buffName", ""), "Баффы", "buffs.html", name])
    rows.sort(key=lambda r: (re.sub("<[^>]+>", "", r[0]), r[1]))  # by visible source name
    body = (card("table", "Все индикаторы баффов",
                 "<p class='note'>stackable показывает, складывается ли бафф с тем же именем от второго источника. "
                 "maxStackSize 0 = лимит не задан. globalRange = действует на всю карту. Источник: башня, в модели которой записана эта иконка. Для остальных (герои и прочее) угадан по имени иконки.</p>"
                 "<input class='filter' type='search' placeholder='Фильтр: башня или бафф' aria-label='Фильтр баффов' "
                 "data-filter='#buffs tbody tr'>"
                 + table(["Источник", "Бафф", "Стакинг"], rows).replace("<table>", "<table id='buffs'>", 1), section="Баффы"))
    page("buffs.html", "Баффы и стакинг",
         "Каждый бафф в игре показывается иконкой над башней. В модели иконки записано, стакается ли он "
         "и сколько раз. По этой таблице видно, какие синергии складываются.", body)


LAYOUT_DIR = DATA / "KnowledgeLayout"


def load_game_layout():
    """Positions dumped from the in-game Monkey Knowledge screen (btd6-knowledge-dumper), by set."""
    path = LAYOUT_DIR / "layout.json"
    if not path.exists():
        return {}
    out = {}
    for e in load(path):
        out.setdefault(e["set"], []).append(e)
    return out


@functools.cache
def webp_uri(f):
    """data: URI of a webp file, or "" when it is missing (pages cannot load images from other hosts)."""
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def icon_uri(kid):
    return webp_uri(LAYOUT_DIR / "icons" / f"{kid}.webp")


def kicon(kid, size, cls="ic"):
    """Knowledge icon drawn from the page's shared symbol (each image is embedded once per page)."""
    if not icon_uri(kid):
        return ""
    return (f"<svg class='{cls}' width='{size}' height='{size}' viewBox='0 0 1 1' aria-hidden='true'>"
            f"<use href='#k-{esc(kid)}'/></svg>")


def knowledge_symbols(ids):
    defs = "".join(f"<symbol id='k-{esc(k)}' viewBox='0 0 1 1'><image href='{icon_uri(k)}' width='1' height='1'/></symbol>"
                   for k in sorted(ids) if icon_uri(k))
    return f"<svg width='0' height='0' style='position:absolute' aria-hidden='true'><defs>{defs}</defs></svg>"


def knowledge_game_graph(entries, nodes):
    """The tree exactly as the game lays it out: icon buttons, stem/arrow/elbow pieces, tier bands."""
    S, pad_l, pad = 0.5, 70, 16
    boxes = [e["rect"] for e in entries] + [a["rect"] for e in entries for a in e["arrows"]]
    minx = min(r[0] - r[2] / 2 for r in boxes)
    maxx = max(r[0] + r[2] / 2 for r in boxes)
    maxy = max(r[1] + r[3] / 2 for r in boxes)
    miny = min(r[1] - r[3] / 2 for r in boxes)
    X = lambda v: pad_l + (v - minx) * S
    Y = lambda v: pad + (maxy - v) * S
    width, height = pad_l + (maxx - minx) * S + pad, (maxy - miny) * S + pad * 2

    bands = []
    for i, tier in enumerate(sorted({e["tier"] for e in entries})):
        rs = [e["rect"] for e in entries if e["tier"] == tier]
        top = Y(max(r[1] + r[3] / 2 for r in rs)) - 10
        bottom = Y(min(r[1] - r[3] / 2 for r in rs)) + 10
        bands.append(f"<rect class='band{i % 2}' x='0' y='{top:.0f}' width='{width:.0f}' height='{bottom - top:.0f}' rx='12'/>"
                     f"<text class='bandlbl' x='12' y='{top + 22:.0f}'>{tier} очк.</text>")

    pieces = []
    for e in entries:
        for a in e["arrows"]:
            cx, cy, w, h = X(a["rect"][0]), Y(a["rect"][1]), abs(a["w"]) * S, abs(a["h"]) * S
            tf = f"translate({cx:.1f},{cy:.1f}) rotate({-a['rot']:.0f}) scale({a.get('sx', 1):.0f},{a.get('sy', 1):.0f})"
            sprite = a.get("sprite") or ""
            if "Arrow" in sprite:  # head, points down in its own space
                shape = f"<path d='M{-w / 2:.1f},{-h / 2:.1f} L{w / 2:.1f},{-h / 2:.1f} L0,{h / 2:.1f} Z'/>"
            elif "Elbow" in sprite:  # corner joint where a horizontal and vertical stem meet
                shape = f"<rect x='{-w / 2:.1f}' y='{-h / 2:.1f}' width='{w:.1f}' height='{h:.1f}' rx='{min(w, h) / 3:.1f}'/>"
            else:  # stem
                shape = f"<rect x='{-w / 2:.1f}' y='{-h / 2:.1f}' width='{w:.1f}' height='{h:.1f}' rx='2'/>"
            pieces.append(f"<g class='piece' transform='{tf}'>{shape}</g>")

    btns = []
    for e in entries:
        kid, d = e["id"], nodes.get(e["id"], {})
        cx, cy, size = X(e["rect"][0]), Y(e["rect"][1]), e["rect"][2] * S
        reqs = " ".join(p for p in d.get("prerequisiteIds") or [] if p in nodes)
        uri = icon_uri(kid)
        cost = d.get("monkeyMoneyCost")
        btns.append(
            f"<a href='#{esc(kid)}' class='kn' data-id='{esc(kid)}' data-req='{esc(reqs)}' "
            f"data-name='{esc(t(kid, fallback=kid))}' data-cost='{fmt(cost)}' data-desc='{esc(t(kid + 'Description', kid + ' Description'))}'>"
            f"<circle class='ring' cx='{cx:.1f}' cy='{cy:.1f}' r='{size / 2 - 2:.1f}'/>"
            + (f"<use href='#k-{esc(kid)}' x='{cx - size / 2:.1f}' y='{cy - size / 2:.1f}' width='{size:.1f}' height='{size:.1f}'/>" if uri else
               f"<text class='nm' x='{cx:.1f}' y='{cy:.1f}' text-anchor='middle'>{esc(t(kid, fallback=kid))[:10]}</text>")
            + (f"<text class='cost' x='{cx:.1f}' y='{cy + size / 2 + 2:.1f}' text-anchor='middle'>{fmt(cost)}</text>" if cost else "")
            + "</a>")
    return (f"<div class='wrap kgraph kgame'><svg viewBox='0 0 {width:.0f} {height:.0f}' width='{width:.0f}' role='img' "
            f"aria-label='Дерево знаний как в игре'>" + "".join(bands) + "".join(pieces) + "".join(btns)
            + "</svg><div class='ktip' hidden></div></div>")


def build_knowledge():
    body, toc = [], []
    GAME_LAYOUT = load_game_layout()
    for cat in sorted(p for p in (DATA / "Knowledge").iterdir() if p.is_dir()):
        cards = []
        for f in sorted(cat.glob("*.json"), key=lambda f: load(f).get("idx", 0)):
            d = load(f)
            name = t(f.stem, fallback=f.stem)
            prereq = " ".join(f"<a class='badge' href='#{esc(p)}'><span>требует</span><b>"
                              f"{kicon(p, 18)}{esc(t(p, fallback=p))}</b></a>"
                              for p in d.get("prerequisiteIds") or [])
            inner = ("<div class='split'><div><div class='hero-row'>"
                     + kicon(f.stem, 84, "ic kicon")
                     + "<div>" + game_text(t(f"{f.stem}Description", f"{f.stem} Description"))
                     + stats([("Monkey Money", Raw(icon("ui", "mm", 22) + fmt(d.get("monkeyMoneyCost")))),
                              ("вложено в ветку", Raw(icon("ui", "knowledge", 22) + fmt(d.get("investmentRequired"))))])
                     + (f"<div class='chips'>{prereq}</div>" if prereq else "")
                     + "</div></div></div><div>" + mod_table((d.get("mod") or {}).get("mutatorMods") or []) + "</div></div>")
            cards.append(card(f.stem, name, inner, en_id=f.stem, section=f"Знания · {cat.name}"))
        nodes = {f.stem: load(f) for f in cat.glob("*.json")}
        body.append(f"<h2 id='{esc(cat.name)}' style='margin-top:32px'>{esc(t(cat.name, fallback=cat.name))}</h2>"
                    + (knowledge_game_graph(GAME_LAYOUT[cat.name], nodes) if cat.name in GAME_LAYOUT else "<p class='note'>Нет раскладки: запустите KnowledgeDumper (F6).</p>")
                    + "".join(cards))
        toc.append((cat.name, t(cat.name, fallback=cat.name)))
    page("knowledge.html", t("Monkey Knowledge", fallback="Monkey Knowledge"),
         "Пассивные улучшения за Monkey Money. Каждая ветка нарисована деревом: полосы это ряды, которые "
         "открываются после N купленных знаний ветки, стрелки ведут от требуемого знания к следующему. "
         "Наведите на узел, чтобы подсветить всю цепочку, нажмите, чтобы открыть карточку с числами. "
         "Число в углу узла это цена в Monkey Money.",
         knowledge_symbols({p.stem for p in (DATA / "Knowledge").rglob("*.json")}) + "".join(body), toc)


def build_powers():
    labels = {"cost": "цена, MM", "quantity": "за покупку", "startCount": "в начале"}
    groups = {"powers": [], "pro": []}
    for f in json_files("Powers"):
        d = load(f)
        name = t(f.stem, fallback=f.stem)
        fl = flatten(d)
        nums = [(k, v) for k, v in fl.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        pic = icon("ui", f"power-{f.stem}", 84, "ic kicon")
        inner = ((f"<div class='hero-row'>{pic}<div>" if pic else "<div><div>")
                 + game_text(t(f"{f.stem} Description", f"{f.stem}Description"))
                 + stats([(labels[k], Raw(icon("ui", "mm", 22) + fmt(d[k])) if k == "cost" else d[k]) for k in labels if k in d])
                 + f"<details><summary>Все числовые параметры ({len(nums)})</summary>{kv_table(nums)}</details></div></div>")
        groups["pro" if "Pro" in f.stem else "powers"].append(card(f.stem, name, inner, en_id=f.stem, section="Силы"))
    page("powers.html", "Силы",
         "Силы (Powers) и Powers Pro. Описание из игры и все числовые параметры модели: урон, длительности, "
         "радиусы, перезарядки.",
         group("powers", "Силы", groups["powers"]) + group("pro", "Powers Pro", groups["pro"]),
         [("powers", "Силы"), ("pro", "Powers Pro")])


def build_index():
    tiles = "".join(f"<a class='tile page-tile' href='{f}'>{page_icon(f, 56)}<span><b>{esc(t(n, fallback=n))}</b><small>{esc(s)}</small></span></a>" for f, n, s in PAGES[1:])
    page("index.html", "BTD6 Tech Wiki",
         "Точные числа Bloons TD 6 прямо из моделей игры: HP боссов по тирам, модификаторы режимов, "
         "множители дохода, стакинг баффов, формула парагона. Названия и описания взяты из текстов игры, "
         "числа без округлений. Поиск по всему сайту: клавиша /.",
         f"<div class='grid home-grid'>{tiles}</div>"
         "<p class='note'>Источник: выгрузка Export Game Data из BTD6 Mod Helper. Подписи к полям, которых нет в "
         "текстах игры, сделаны по названиям полей.</p>")


# ---------- icons (from tools/fetch_icons.py, resized to data/icons/web/*.webp) ----------

ICONS = load(DATA / "icons" / "manifest.json") if (DATA / "icons" / "manifest.json").exists() else {}


def data_uri(kind, oid):
    rel = ICONS.get(kind, {}).get(oid)
    # icons made here (tools/compose_icons.sh) are not in the download manifest
    return webp_uri(DATA / "icons" / "web" / (f"{rel}.webp" if rel else f"{kind}/{oid}.webp"))


def icon(kind, oid, size, cls="ic"):
    """Inline <img> for an icon, or "" when there is none."""
    uri = data_uri(kind, oid)
    return f"<img class='{cls}' src='{uri}' width='{size}' height='{size}' alt='' loading='lazy'>" if uri else ""


PAGE_ICONS = {"paragon.html": ("ui", "paragon"), "bosses.html": ("ui", "boss-Bloonarius"), "modes.html": ("ui", "mode-Clicks"),
              "income.html": ("ui", "coin"), "buffs.html": ("towers", "MonkeyVillage"), "knowledge.html": ("ui", "knowledge"),
              "powers.html": ("ui", "powers"), "towers.html": ("towers", "DartMonkey"), "rounds.html": ("ui", "startround"),
              "bloons.html": ("bloons", "Red")}


def page_icon(file, size):
    spec = PAGE_ICONS.get(file)
    return icon(spec[0], spec[1], size) if spec else ""


def bloon_css(b):
    return re.sub(r"[^A-Za-z0-9]", "", b)


def bloon_icon_style(ids):
    """One CSS class per bloon icon, so a page with hundreds of chips embeds each image once."""
    rules = "".join(f".bi-{bloon_css(b)}{{background-image:url({data_uri('bloons', b)})}}" for b in sorted(ids) if data_uri("bloons", b))
    return f"<style>{rules}</style>"


# ---------- towers ----------

TOWER_SETS = {1: "Primary", 2: "Military", 4: "Magic", 8: "Support"}
# shop order: GameModel.towerSet from game.json; the list below is the fallback until the dump exists.
# Unknown towers go last by cost.
SHOP_ORDER = [t["id"] for t in sorted(GAME.get("towerSet") or [], key=lambda t: t["index"])] or ["DartMonkey", "BoomerangMonkey", "BombShooter", "TackShooter", "IceMonkey", "GlueGunner", "Desperado",
              "SniperMonkey", "MonkeySub", "MonkeyBuccaneer", "MonkeyAce", "HeliPilot", "MortarMonkey", "DartlingGunner",
              "WizardMonkey", "SuperMonkey", "NinjaMonkey", "Alchemist", "Druid", "Mermonkey", "Skywarden",
              "BananaFarm", "SpikeFactory", "MonkeyVillage", "EngineerMonkey", "BeastHandler"]
EFFECT_WORDS = ("Slow", "Freeze", "Stun", "Knockback", "Wind", "DamageOverTime", "AddBehaviorToBloon", "Bleed", "Burn")


def num(v):
    return round(v, 4) if isinstance(v, float) else v


def proj_summary(p, lbl, count, depth, out):
    beh = [b for b in p.get("behaviors") or [] if isinstance(b, dict)]
    dmg = next((b for b in beh if short_type(b) == "DamageModel"), None)
    mods, effects = [], []
    for b in beh:
        st = short_type(b)
        if "DamageModifier" in st:
            fields = {k: v for k, v in b.items() if scalar(v) and k not in ("$type", "name", "collisionPass") and v not in (0, 0.0, False, "")}
            mods.append(label_mod(st) + ": " + ", ".join(f"{k} {fmt(v)}" for k, v in fields.items()))
        elif any(w in st for w in EFFECT_WORDS):
            effects.append(label(st))
    out.append({"label": lbl, "depth": depth, "count": count,
                "damage": num(dmg["damage"]) if dmg else None, "pierce": num(p.get("pierce")),
                "mods": mods, "effects": sorted(set(effects))})
    for b in beh:
        for k, v in b.items():
            if isinstance(v, dict) and "ProjectileModel" in v.get("$type", ""):
                em = b.get("emission") or {}
                proj_summary(v, label(short_type(b)), em.get("count") or 1, depth + 1, out)


def label_mod(st):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", st.replace("DamageModifierFor", "").replace("Model", "")) or st


def tower_summary(d, upgrade_costs):
    attacks, abilities, other = [], [], []
    for b in d.get("behaviors") or []:
        if not isinstance(b, dict) or skipped(b):
            continue
        st = short_type(b)
        if st.startswith("AttackModel") or st.endswith("AttackModel"):
            weapons = []
            for w in b.get("weapons") or []:
                projs = []
                em = w.get("emission") or {}
                if isinstance(w.get("projectile"), dict):
                    proj_summary(w["projectile"], "Снаряд", em.get("count") or 1, 0, projs)
                weapons.append({"rate": num(w.get("rate")), "count": em.get("count") or 1,
                                "emission": label(short_type(em)) if em else "", "proj": projs})
            attacks.append({"name": label(st), "range": num(b.get("range")), "weapons": weapons})
        elif st == "AbilityModel":
            abilities.append({"name": t(b.get("displayName") or "", fallback=b.get("displayName") or b.get("name", "")),
                              "cooldown": num(b.get("cooldown"))})
        elif not any(s in st for s in ("Sound", "Effect", "Display")):
            other.append(label(st))
    parts = [d.get("cost", 0)] + [upgrade_costs.get(u, 0) for u in d.get("appliedUpgrades") or []]
    return {"cost": sum(parts), "parts": parts, "range": num(d.get("range")), "attacks": attacks, "abilities": abilities,
            "other": sorted(set(other))}


def build_towers():
    global current_file
    upgrades = {load(f).get("name"): load(f) for f in json_files("Upgrades")}
    ucost = {k: v.get("cost", 0) for k, v in upgrades.items()}
    diffs = {}
    for mode in ("Easy", "Medium", "Hard", "Impoppable"):
        f = DATA / "Mods" / f"{mode}.json"
        mult = next((m.get("multiplier") for m in (load(f).get("mutatorMods") or [])
                     if short_type(m) == "GlobalCostModModel"), None) if f.exists() else None
        diffs[t(mode, fallback=mode)] = mult if mult is not None else 1.0
    # Impoppable is a mode played on Hard, so both cost multipliers apply (1.08 * 1.12 = 1.2096)
    diffs[t("Impoppable", fallback="Impoppable")] = round(diffs[t("Impoppable", fallback="Impoppable")] * diffs[t("Hard", fallback="Hard")], 6)
    # difficulty switch: every .cost element is recomputed in the browser from its Medium parts
    selector = ("<div class='diff' role='group' aria-label='Сложность'><span>Сложность</span>" + "".join(
        f"<button type='button' data-mult='{m}'{' class=on' if m == 1 else ''}>{esc(n)}</button>" for n, m in diffs.items())
        + "</div><p class='note'>Цены пересчитаны по множителю цены режима и округлены до 5 $, "
          "каждая покупка отдельно.</p>")

    def price(parts, cls="cost"):
        return Raw(f"<span class='{cls}' data-parts='{','.join(str(p) for p in parts)}'>${fmt(sum(parts))}</span>")

    tiles = {}
    for folder in sorted(p for p in (DATA / "Towers").iterdir() if p.is_dir()):
        tid = folder.name
        base = load(folder / f"{tid}.json")
        variants = {}
        for f in folder.glob(f"{tid}-*.json"):
            suffix = f.stem.split("-", 1)[1]
            variants[suffix] = tower_summary(load(f), ucost)
        variants["000"] = tower_summary(base, ucost)
        # upgrade paths from the max-tier files of each single path
        paths = []
        for i in range(3):
            key = "".join("5" if j == i else "0" for j in range(3))
            top = load(folder / f"{tid}-{key}.json") if (folder / f"{tid}-{key}.json").exists() else {}
            paths.append(top.get("appliedUpgrades") or [])
        name = t(tid, fallback=tid)
        file = f"tower-{tid}.html"
        current_file = file
        cols = []
        for i, path in enumerate(paths):
            done, rows = [], []
            for tier, u in enumerate(path, 1):
                c = ucost.get(u, 0)
                done.append(c)
                rows.append(f"<li>{icon('upgrades', u, 56, 'ic up-ic')}<div><div class='up-head'><b>{tier}. {esc(t(u, fallback=u))}</b>"
                            f"<span class='price'>{price([c], 'cost big')}<small>всего {price(done)}</small></span></div>"
                            f"<p>{esc(t(u + ' Description'))}</p></div></li>")
            cols.append(f"<div class='path'><h3>Путь {i + 1}</h3><ol>{''.join(rows)}</ol></div>")
        para = ""
        if (folder / f"{tid}-Paragon.json").exists():
            u = (load(folder / f"{tid}-Paragon.json").get("appliedUpgrades") or [""])[-1]
            para = (f"<div class='paragon'><h3>Парагон</h3><ol><li>{icon('upgrades', u, 72, 'ic up-ic para-ic')}<div>"
                    f"<div class='up-head'><b>{esc(t(u, fallback=u))}</b><span class='price'>{price([ucost.get(u, 0)], 'cost big')}</span></div>"
                    f"<p>{esc(t(u + ' Description'))}</p></div></li></ol></div>")
        picker = "".join(
            f"<div class='xp-row' data-path='{i}'><span>Путь {i + 1}</span>"
            + "".join(f"<button type='button' data-tier='{n}'>{n}</button>" for n in range(6)) + "</div>"
            for i in range(3))
        extra = [k for k in variants if not k.isdigit()]
        body = (
            selector
            + card("about", name,
                 "<div class='hero-row'>" + icon('towers', tid, 120, 'ic portrait') + "<div>" + game_text(t(f"{tid} Description", f"{tid}Description"))
                 + stats([("цена", price([base.get("cost", 0)])), ("дальность", base.get("range")),
                          ("радиус места", base.get("radius")), ("категория", t(TOWER_SETS.get(base.get("towerSet")), fallback=""))])
                 + "</div></div>",
                 en_id=tid, section="Башни")
            + card("upgrades", "Улучшения", f"<div class='paths'>{''.join(cols)}</div>{para}", section=name)
            + card("crosspath", "Кроссапгрейд",
                   "<p class='note'>Выберите тиры путей, как в игре. Показаны цена со всеми улучшениями, "
                   "атаки, перезарядка, урон и пробивание каждого снаряда, включая вложенные (взрывы, осколки).</p>"
                   f"<div class='xp' data-tower='{esc(tid)}'>{picker}"
                   + (f"<div class='xp-row'><span>Особые</span>" + "".join(
                       f"<button type='button' data-variant='{esc(k)}'>{esc(k)}</button>" for k in sorted(extra)) + "</div>" if extra else "")
                   + "<div class='xp-out'></div></div>"
                   f"<script type='application/json' class='xp-data'>{json.dumps(variants, ensure_ascii=False).replace('</', '<\\/')}</script>",
                   section=name))
        page(file, name, f"{esc(t(TOWER_SETS.get(base.get('towerSet')), fallback=''))}. Все числа из моделей башни.",
             body, toc=[("about", "Описание"), ("upgrades", "Улучшения"), ("crosspath", "Кроссапгрейд")])
        tiles.setdefault(base.get("towerSet"), []).append((tid, name, base.get("cost")))
    current_file = "towers.html"
    body = []
    for ts in sorted(tiles):
        grid = "".join(f"<a class='tile tower-tile' href='tower-{esc(tid)}.html'>{icon('towers', tid, 72)}<span><b>{esc(n)}</b>{price([c], 'cost tile-price')}</span></a>"
                       for tid, n, c in sorted(tiles[ts], key=lambda x: (SHOP_ORDER.index(x[0]) if x[0] in SHOP_ORDER else 99, x[2])))
        body.append(f"<h2 class='group' id='set-{TOWER_SETS.get(ts)}'>{esc(t(TOWER_SETS.get(ts), fallback=''))}</h2><div class='grid'>{grid}</div>")
        for tid, n, c in tiles[ts]:
            INDEX.append([n, "Башни", f"tower-{tid}.html", tid])
    page("towers.html", "Башни",
         "Все основные башни. На странице башни: описание, улучшения с ценами и выбор кроссапгрейда "
         "с точными числами атак.", selector + "".join(body))


# ---------- rounds ----------

# ---------- bloons (shared by the bloons and rounds pages) ----------

BLOONS = {f.stem: load(f) for f in (DATA / "Bloons").rglob("*.json")}


def children(b):
    out = []
    for beh in BLOONS[b].get("behaviors") or []:
        if isinstance(beh, dict) and short_type(beh) == "SpawnChildrenModel":
            out += beh.get("children") or []
    return out


@functools.cache
def rbe(b):
    """Total HP of every layer."""
    return BLOONS[b].get("maxHealth", 1) + sum(rbe(c) for c in children(b))


@functools.cache
def pops(b):
    """Layers popped, one $ each."""
    return 1 + sum(pops(c) for c in children(b))


def bloon_name(b):
    m = BLOONS[b]
    parts = [t(m.get("baseId"), fallback=m.get("baseId"))]
    if m.get("isFortified"):
        parts.append("укрепл.")
    if m.get("isGrow"):
        parts.append(t("Regrow").lower())
    if m.get("isCamo"):
        parts.append(t("Camo").lower())
    return " ".join(parts)


BLOON_GROUPS = [
    ("regular", "Обычные шары", ["Red", "Blue", "Green", "Yellow", "Pink", "Black", "White", "Purple", "Lead", "Zebra",
                                 "Rainbow", "Ceramic"]),
    ("moab", "MOAB-класс", ["Moab", "Bfb", "Zomg", "Ddt", "Bad"]),
    ("golden", "Золотые", ["Golden", "GoldenLead", "GoldenLeadPurple", "GoldenLeadPurpleZebra"]),
    ("special", "Особые", ["AuraBloon", "DoshBloon", "GlassBloon", "DynamiteBloon", "RetributionBloon", "RingleaderBloon",
                           "DiamondBloon"]),
    ("undead", "Нежить", ["UndeadMoab", "UndeadBfb", "UndeadZomg"]),
]
# BloonProperties flags from the game code
BLOON_PROPS = [(1, "Свинец"), (2, "Чёрный"), (4, "Белый"), (8, "Фиолетовый"), (16, "Заморожен"), (32, "Неуязвим"), (64, "Стекло")]


PROP_INFO = {
    1: "Не лопается острыми атаками.", 2: "Невосприимчив к взрывам.", 4: "Невосприимчив к холоду и заморозке.",
    8: "Невосприимчив к огню, энергии и плазме.", 16: "Состояние замороженного шара: острые атаки его не лопают.",
    32: "Временно не получает урон.", 64: "Свойство шаров режима Frontier.",
}


def damage_masks(obj, out):
    """immuneBloonProperties of every DamageModel inside a tower model."""
    if isinstance(obj, dict):
        if short_type(obj) == "DamageModel":
            out.append(obj.get("immuneBloonProperties") or 0)
        for v in obj.values():
            damage_masks(v, out)
    elif isinstance(obj, list):
        for v in obj:
            damage_masks(v, out)
    return out


def properties_card():
    """What each bloon property means and which base towers (000) cannot damage it at all."""
    masks = {p.name: damage_masks(load(p / f"{p.name}.json"), []) for p in sorted((DATA / "Towers").iterdir()) if p.is_dir()}
    rows = []
    for bit, name in BLOON_PROPS:
        blocked = [tid for tid in SHOP_ORDER if masks.get(tid) and all(m & bit for m in masks[tid])]
        towers = " ".join(f"<a class='badge' href='tower-{tid}.html'><span>000</span><b>{icon('towers', tid, 18)}"
                          f"{esc(t(tid, fallback=tid))}</b></a>" for tid in blocked)
        rows.append(f"<div class='prop-row' id='prop-{bit}'><span class='badge no'><span>свойство</span><b>{esc(name)}</b></span>"
                    f"<div><p>{esc(PROP_INFO.get(bit, ''))}</p>"
                    + (f"<p class='note'>Не наносят урона базовой атакой:</p><div class='chips'>{towers}</div>" if towers else "")
                    + "</div></div>")
    return card("props", "Свойства", "<details class='fold'><summary>Что значит каждое свойство и какие башни его не лопают</summary>"
                "<p class='note'>Список башен посчитан по immuneBloonProperties урона их снарядов "
                "в базовой модели (000). Улучшения часто снимают ограничение.</p>" + "".join(rows) + "</details>", section="Шары")


def build_bloons():
    body, toc = [properties_card()], [("props", "Свойства")]
    for gid, title, members in BLOON_GROUPS:
        cards = []
        for b in members:
            if b not in BLOONS:
                continue
            m = BLOONS[b]
            name = t(b, fallback=b)
            props = " ".join(f"<a class='badge no' href='#prop-{bit}'><span>свойство</span><b>{esc(p)}</b></a>"
                             for bit, p in BLOON_PROPS if (m.get("bloonProperties") or 0) & bit)
            kids = collections.Counter(children(b))
            kid_badges = " ".join(
                f"<a class='badge' href='#{esc(BLOONS[c].get('baseId', c))}'><span>дети</span>"
                f"<b>{icon('bloons', c, 18)}{n}× {esc(bloon_name(c))}</b></a>" for c, n in kids.items() if c in BLOONS)
            variants = sorted((f.stem for f in (DATA / "Bloons" / b).glob("*.json") if f.stem != b),
                              key=lambda v: (rbe(v), v))
            vrows = [(Raw(f"<span class='mod-name'>{icon('bloons', v, 22) or '<span class=mod-ic></span>'}{esc(bloon_name(v))}</span>"),
                      BLOONS[v].get("maxHealth"), rbe(v), BLOONS[v].get("speed")) for v in variants]
            beh = sorted({label(short_type(x)) for x in m.get("behaviors") or [] if isinstance(x, dict) and not skipped(x)})
            pic = icon("bloons", b, 72, "ic kicon")
            inner = ("<div class='hero-row'>" + pic + "<div>"
                     + game_text(t(f"{b}Desc"))
                     + stats([("HP слоя", m.get("maxHealth")), ("RBE", rbe(b)), ("$ за лопание", pops(b)),
                              ("скорость", m.get("speed")), ("урон слоя при утечке", m.get("leakDamage"))])
                     + (f"<div class='chips'>{props} {kid_badges}</div>" if props or kid_badges else "")
                     + "</div></div>"
                     + (f"<h3>Варианты ({len(vrows)})</h3>" + table(["Вариант", "HP слоя", "RBE", "Скорость"], vrows) if vrows else "")
                     + (f"<h3>Поведения</h3><div class='chips'>{''.join(f'<span class=chip>{esc(x)}</span>' for x in beh)}</div>" if beh else ""))
            cards.append(card(b, name, inner, en_id=b, section="Шары"))
        if cards:
            body.append(group(gid, title, cards))
            toc.append((gid, title))
    page("bloons.html", "Шары",
         "Все шары из моделей игры: HP слоя, RBE (сумма HP всех слоёв), деньги за полное лопание, скорость, "
         "свойства и из чего шар состоит. Свойство блокирует урон тех башен, у которых оно указано в "
         "immuneBloonProperties снаряда: например, свинец у обычных дротиков.",
         "".join(body), toc)


def build_rounds():
    bloons = BLOONS

    income = load(DATA / "IncomeSets" / "DefaultIncomeSet.json")

    def income_mult(r):
        for th in income.get("thresholds") or []:
            if r <= th["threshold"]:
                return th["multiplier"]
        return income.get("finalMultiplier", 1)

    def tags(b):
        m = bloons[b]
        return {k for k, on in (("camo", m.get("isCamo")), ("regrow", m.get("isGrow")), ("fortified", m.get("isFortified")),
                                ("lead", m.get("baseId") == "Lead"), ("ceramic", m.get("baseId") == "Ceramic"),
                                ("moab", m.get("isMoab"))) if on}

    prop_names = {"camo": t("Camo"), "regrow": t("Regrow"), "fortified": "Укреплённые"}
    filters = [("", "Все"), ("new", "С новым"), ("camo", t("Camo")), ("regrow", t("Regrow")), ("fortified", "Укреплённые"),
               ("lead", t("Lead")), ("ceramic", t("Ceramic")), ("moab", "MOAB-класс")]

    # end of round bonus from the Medium mode model (BonusCashPerRoundModModel: baseCash + round * roundMultiple)
    bonus_mod = next((m for m in load(DATA / "Mods" / "Medium.json").get("mutatorMods") or []
                      if short_type(m) == "BonusCashPerRoundModModel"), {})
    bonus_base, bonus_per_round = bonus_mod.get("baseCash", 100), bonus_mod.get("roundMultiple", 1)
    sections, toc = [], []
    for rs, title in (("DefaultRoundSet", "Обычные раунды"), ("AlternateRoundSet", "Альтернативные раунды (ABR)")):
        folder = DATA / "Rounds" / rs
        rows, total, seen = [], 0, set()
        for f in sorted(folder.glob("*.json"), key=lambda f: int(f.stem)):
            r = int(f.stem)
            groups = load(f).get("groups") or []
            chips = "".join(f"<span class='chip bchip'><i class='bi bi-{bloon_css(g["bloon"])}'></i>{g['count']}× {esc(bloon_name(g['bloon']))}</span>" for g in groups)
            r_rbe = sum(g["count"] * rbe(g["bloon"]) for g in groups)
            r_pops = sum(g["count"] * pops(g["bloon"]) for g in groups)
            cash = r_pops * income_mult(r)
            bonus = bonus_base + r * bonus_per_round
            total += cash + bonus
            dur = max((g["end"] for g in groups), default=0) / 60
            # first appearance of a bloon type or a property (camo, regrow, fortified)
            row_tags = set().union(*(tags(g["bloon"]) for g in groups)) if groups else set()
            feats = [bloons[g["bloon"]].get("baseId") for g in groups] + [p for p in ("camo", "regrow", "fortified") if p in row_tags]
            new = list(dict.fromkeys(x for x in feats if x not in seen))
            seen.update(new)
            badges = "".join(f"<span class='chip new'>{esc(prop_names.get(x) or t(x, fallback=x))}</span>" for x in new)
            if new:
                row_tags.add("new")
            cells = [r, Raw(f"<div class='chips'>{chips}</div>"), Raw(f"<div class='chips'>{badges}</div>"), r_rbe,
                     round(cash, 1), bonus, round(total, 1), round(dur, 2)]
            rows.append(f"<tr data-tags='{' '.join(sorted(row_tags))}'{' class=newrow' if new else ''}>" + "".join(
                f"<td class='n'>{fmt(c)}</td>" if isinstance(c, (int, float)) else f"<td>{c}</td>" for c in cells) + "</tr>")
        head = "".join(f"<th>{h}</th>" for h in ("Раунд", "Шары", "Впервые", "RBE", "$ за лопание", "$ бонус", "$ всего с 1-го", "Длит., с"))
        bar = (f"<div class='tagbar' data-target='#{rs}-t'>"
               + "".join(f"<button type='button' data-tag='{k}'{' class=on' if not k else ''}>{esc(n)}</button>" for k, n in filters)
               + "</div>")
        INDEX.append([title, "Раунды", f"rounds.html#{rs}", rs])
        sections.append(card(rs, title,
                             (f"<div class='chips'><a class='badge' href='modes.html#AlternateBloonsRounds'><span>режим</span><b>{icon('ui', 'mode-AlternateBloonsRounds', 18)}{esc(t('Mode AlternateBloonsRounds', fallback='ABR'))}</b></a></div>" if rs == "AlternateRoundSet" else "") + bar + "<input class='filter' type='search' placeholder='Фильтр: номер или шар' aria-label='Фильтр раундов' "
                             f"data-filter='#{rs}-t tbody tr'>"
                             f"<div class='wrap'><table id='{rs}-t'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
                             section="Раунды"))
        toc.append((rs, title))
    page("rounds.html", "Раунды",
         "Состав каждого раунда и посчитанные по моделям шаров величины. RBE это сумма HP всех слоёв. "
         "$ за лопание посчитан как 1 $ за каждый лопнутый слой, умноженный на множитель дохода раунда "
         "(DefaultIncomeSet). Бонус за раунд 100 + номер раунда (BonusCashPerRoundModModel). "
         "HP MOAB-класса в поздних раундах растёт, здесь показаны базовые значения.",
         bloon_icon_style(set(bloons)) + "".join(sections), toc)


def main():
    global current_file, INDEX
    for lang in LANGS:
        set_lang(lang)
        INDEX = []
        for file, build in (("paragon.html", build_paragon), ("bosses.html", build_bosses), ("modes.html", build_modes),
                            ("income.html", build_income), ("buffs.html", build_buffs),
                            ("knowledge.html", build_knowledge), ("powers.html", build_powers),
                            ("towers.html", build_towers), ("bloons.html", build_bloons), ("rounds.html", build_rounds),
                            ("index.html", build_index)):
            current_file = file
            build()
        (OUT / "search.js").write_text(
            translate("var WIKI_INDEX=" + json.dumps(INDEX, ensure_ascii=False) + ";" + SEARCH_JS), encoding="utf-8")
        left = sorted(set(re.findall(r"[А-Яа-яЁё][А-Яа-яЁё .,:()/-]*", "".join(
            f.read_text(encoding="utf-8") for f in OUT.glob("*.html"))))) if lang != "ru" else []
        print(f"{lang}: {len(INDEX)} search entries into {OUT}"
              + (f", untranslated: {left[:15]}" if left else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
