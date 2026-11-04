"""Build the BTD6 tech wiki (static HTML) from a Mod Helper "Export Game Data" dump.

Usage: python3 -I build.py            (reads ./data, writes ./site)
Refresh data: copy Bosses Bloons Mods IncomeSets Buffs Knowledge Powers
paragonDegreeData.json textTable.json from the export folder into ./data
and the KnowledgeLayout folder written by btd6-knowledge-dumper (F6 in game, gives game.json too).
"""
import html
import base64
import collections
import functools
import json
import math
import re
import shutil
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
document.querySelectorAll('.tagbar:not(.sortbar)').forEach(function(bar){var rows=document.querySelectorAll(bar.dataset.target+' tbody tr');bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){bar.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});var tag=b.dataset.tag;rows.forEach(function(r){r.dataset.gh=tag&&(' '+r.dataset.tags+' ').indexOf(' '+tag+' ')<0?'1':'';r.hidden=!!(r.dataset.th||r.dataset.gh)})})})});
function hcalc(c){var reqs=JSON.parse(c.dataset.reqs),cash=JSON.parse(c.dataset.cash),map=+c.querySelector('select').value,
start=Math.max(1,Math.min(140,+c.querySelector('input').value||1)),xp=0,r=start-1,h='<div class="chips">';
reqs.forEach(function(q,i){while(xp<q&&r<500){r++;xp+=Math.round((r<=20?20*r+20:r<=50?40*r-380:90*r-2880)*map)}
h+='<span class="chip">ур. '+(i+2)+': раунд '+r+'</span>'});c.querySelector('.hcalc-out').innerHTML=h+'</div>';
var m=curMult(),cost=m===1?+c.dataset.cost:Math.round(c.dataset.cost*m/5)*5,have=+c.dataset.start,ok=1;
while(have<cost&&ok<=cash.length){have+=cash[ok-1];ok++}
c.querySelector('.hcalc-cash').textContent=ok>cash.length?'':'Денег хватит к началу раунда '+ok+' ($'+cost+', старт $'+c.dataset.start+', без других трат).'}
document.querySelectorAll('.hcalc').forEach(function(c){var go=function(){hcalc(c)};c.querySelector('select').addEventListener('change',go);
c.querySelector('input').addEventListener('input',go);go()});
document.querySelectorAll('.sortbar').forEach(function(bar){var g=document.getElementById(bar.dataset.grid);bar.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){var k=b.dataset.sort;Array.prototype.slice.call(g.children).sort(function(x,y){return x.dataset[k]-y.dataset[k]}).forEach(function(c){g.appendChild(c)});g.classList.toggle('cols3',k==='order');bar.querySelectorAll('button').forEach(function(o){o.classList.toggle('on',o===b)})})})});
document.querySelectorAll('table').forEach(function(t){var tb=t.tBodies[0];if(!tb||!t.tHead||t.querySelector('[rowspan]'))return;var ths=t.tHead.rows[0].cells;
Array.prototype.forEach.call(ths,function(th,ci){th.classList.add('sortable');th.addEventListener('click',function(){var dir=th.dataset.dir==='1'?-1:1;Array.prototype.forEach.call(ths,function(x){delete x.dataset.dir});th.dataset.dir=dir===1?'1':'-1';
var val=function(r){var s=r.cells[ci]?r.cells[ci].textContent.trim():'';var n=parseFloat(s.replace(/[   $]/g,'').replace(',','.'));return isNaN(n)?s:n};
Array.prototype.slice.call(tb.rows).sort(function(a,b){var x=val(a),y=val(b);return(typeof x==='number'&&typeof y==='number'?x-y:String(x).localeCompare(String(y)))*dir}).forEach(function(r){tb.appendChild(r)})})})});
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
el.textContent='$'+s.toLocaleString('ru-RU')});document.querySelectorAll('.hcalc').forEach(hcalc)}
document.querySelectorAll('.diff button').forEach(function(b){b.addEventListener('click',function(){try{localStorage.setItem(DIFF_KEY,b.dataset.mult)}catch(x){}applyDiff()})});
applyDiff();
(function(){var top=document.querySelector('.top');if(!top)return;function h(){document.documentElement.style.setProperty('--top-h',top.offsetHeight+'px')}h();if(window.ResizeObserver)new ResizeObserver(h).observe(top)})();
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
d.attacks.forEach(function(a,ai){h+='<h3>'+e(a.name)+' <span class="id">дальность '+f(a.range)+'</span></h3><div class="wrap"><table><thead><tr><th>Оружие</th><th>Перезарядка, с</th><th>Атак/с</th><th>Снаряд</th><th>Кол-во</th><th>Урон</th><th>Урон за выстрел</th><th>Пробив.</th><th>Примерный DPS</th><th>Модификаторы и эффекты</th><th>Не лопает</th></tr></thead><tbody>';
a.weapons.forEach(function(w,wi){var n=Math.max(1,w.proj.length);w.proj.forEach(function(p,pi){h+='<tr>'+(pi===0?'<td rowspan="'+n+'">'+(wi+1)+(w.emission?' <span class="id">'+e(w.emission)+'</span>':'')+'</td><td class="n" rowspan="'+n+'">'+f(p.rate)+'</td><td class="n" rowspan="'+n+'">'+(p.rate?f(1/p.rate):'–')+'</td>':'')
+'<td style="padding-left:'+(10+p.depth*16)+'px">'+(p.depth?'↳ ':'')+e(p.projectile)+'</td><td class="n">'+f(p.count)+'</td><td class="n">'+f(p.damage)+'</td><td class="n">'+f(p.shotDamage)+'</td><td class="n">'+f(p.pierce)+'</td><td class="n">'+f(p.dps)+'</td><td>'
 +p.mods.concat(p.effects).map(function(m){return'<span class="chip">'+e(m)+'</span>'}).join(' ')+'</td><td>'+((p.immune||[]).length?p.immune.map(function(x){return'<a class="chip no" href="bloons.html#prop-'+x[0]+'">'+e(x[1])+'</a>'}).join(' '):'–')+'</td></tr>'});
if(!w.proj.length)h+='<tr><td>'+(wi+1)+'</td><td class="n">'+f(w.rate)+'</td><td class="n">'+(w.rate?f(1/w.rate):'–')+'</td><td colspan="8">–</td></tr>'});
h+='</tbody></table></div>'});if(d.attacks.length)h+='<p class="note">Примерный DPS: урон за выстрел / перезарядка. Без учёта баффов, пробивания и множителей режима.</p>';
if(d.abilities.length)h+='<h3>Способности</h3><div class="chips">'+d.abilities.map(function(a){return'<a class="chip" href="#abilities">'+e(a.name)+', перезарядка '+f(a.cooldown)+' с</a>'}).join('')+'</div>';
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
    global LANG, OUT, TEXT, PHRASES
    LANG = lang
    OUT = SITE if lang == MAIN_LANG else SITE / lang
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


# ---------- pages ----------

def line_chart(ys, xticks, aria, ylabel=fmt, tip=lambda x, y: f"{x}: {fmt(y)}"):
    """One-series line chart; x is 1..len(ys), each point has a hover tooltip (tip(x, y))."""
    w, h, pad, left = 640, 220, 36, 54
    top = max(ys) or 1
    x = lambda i: left + (w - left - pad) * i / (len(ys) - 1)
    y = lambda v: h - pad - (h - 2 * pad) * v / top
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(ys))
    ticks = "".join(f"<text x='{x(n - 1):.1f}' y='{h - pad + 16}' text-anchor='middle'>{n}</text>" for n in xticks)
    yt = "".join(f"<text x='{left - 6}' y='{y(v) + 4:.1f}' text-anchor='end'>{ylabel(v)}</text>" for v in (0, top / 2, top))
    grid = "".join(f"<line class='pgrid' x1='{left}' y1='{y(v):.1f}' x2='{w - pad}' y2='{y(v):.1f}'/>" for v in (top / 2, top))
    step = (w - left - pad) / (len(ys) - 1)  # hover targets wider than the line
    hits = "".join(f"<rect class='phit' x='{x(i) - step / 2:.1f}' y='{pad}' width='{step:.1f}' height='{h - 2 * pad}'>"
                   f"<title>{tip(i + 1, v)}</title></rect>" for i, v in enumerate(ys))
    return (f"<div class='wrap'><svg class='pchart' viewBox='0 0 {w} {h}' width='{w}' role='img' aria-label='{esc(aria)}'>"
            f"{grid}<line class='paxis' x1='{left}' y1='{h - pad}' x2='{w - pad}' y2='{h - pad}'/>"
            f"<polyline class='pline' points='{pts}'/>{ticks}{yt}{hits}</svg></div>")


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
         "5 обычных и 5 элитных тиров. HP по тирам и параметры, которые растут с тиром.",
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
         "Модификаторы каждого режима: деньги, HP, цены, запреты. CoopStandardCash и CoopDeflationCash "
         "задают деньги для 2, 3 и 4 игроков в коопе.",
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
    cash = [p + b for p, b in round_cash().values()]
    total = [sum(cash[:i + 1]) for i in range(len(cash))]
    ticks = (1, 20, 40, 60, 80, 100, 120, len(cash))
    k = lambda v: f"{round(v / 1000, 1):g}k" if v >= 1000 else fmt(round(v))
    charts = card("cash", "Деньги по раундам",
                  "<h3>За раунд (лопание и бонус)</h3>"
                  + line_chart(cash, ticks, "Деньги за раунд", k, lambda r, v: f"раунд {r}: ${fmt(round(v))}")
                  + "<h3>Всего с 1-го раунда</h3>"
                  + line_chart(total, ticks, "Деньги с 1-го раунда", k, lambda r, v: f"раунд {r}: ${fmt(round(v))}"),
                  section="Доход")
    page("income.html", "Доход по раундам",
         "Деньги за лопание умножаются на коэффициент раунда. DefaultIncomeSet работает в обычной игре, "
         "остальные в своих режимах.",
         charts + f"<div class='cards'>{''.join(body)}</div>", [("cash", "Деньги по раундам")] + toc)




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


@functools.cache
def buff_icon_owners():
    """Buff icon name -> heroes and powers whose models carry it: {(kind, id)}."""
    out = {}
    files = [("hero", f.parent.name, f) for f in (DATA / "Heroes").glob("*/*.json")] + \
            [("power", f.stem, f) for f in (DATA / "Powers").glob("*.json")]
    for kind, oid, f in files:
        for name in set(re.findall(r'"(?:buff|)(?:Icon|Locs|icon)Name": "([^"]+)"', f.read_text(encoding="utf-8"))):
            out.setdefault(name, set()).add((kind, oid))
    return out


def source_badge(kind, oid):
    """Link badge to a buff source: tower page, hero card or power card."""
    if kind == "tower":
        return tower_badge(oid)
    href, pic = (f"hero-{oid}.html", icon("heroes", oid, 18)) if kind == "hero" else \
                (f"powers.html#{oid}", icon("ui", f"power-{oid}", 18))
    return (f"<a class='badge' href='{href}'><span>{'герой' if kind == 'hero' else 'сила'}</span>"
            f"<b>{pic}{esc(t(oid, fallback=oid))}</b></a>")


def tower_of(icon_name, buff_name=""):
    """Source of a buff: towers, then heroes and powers whose data carry its icon; else a guess from the icon name
    (BuffIconAlchemist3xx); else towers carrying its buff name (last: heroes reuse tower buff names, BiggerRadiusBuff)."""
    found = buff_towers().get(icon_name)
    if found:
        return "".join(tower_badge(tid) for tid in sorted(found, key=lambda x: SHOP_ORDER.index(x) if x in SHOP_ORDER else 99))
    owners = buff_icon_owners().get(icon_name)
    if owners:
        return "".join(source_badge(k, o) for k, o in sorted(owners))
    rest = icon_name.removeprefix("BuffIcon")
    for end in range(len(rest), 3, -1):
        word = rest[:end]
        if word[0].isupper() and (end == len(rest) or not rest[end].islower()) and isinstance(TEXT.get(word), str):
            word_tower = {"Gyrfalcon": "BeastHandler", "Microraptor": "BeastHandler", "Piranha": "BeastHandler",
                          "Sheriff": "Desperado"}.get(word, word)  # pets and the old Desperado id
            if (DATA / "Towers" / word_tower).is_dir():
                return tower_badge(word_tower)
            if (DATA / "Powers" / f"{word}.json").exists():
                return source_badge("power", word)
            if (DATA / "Heroes" / word).is_dir():
                return source_badge("hero", word)
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
         "Баффы, которые видно иконкой над башней: откуда бафф, стакается ли и до скольки раз.", body)


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
         "Деревья знаний как в игре. Наведите на знание, чтобы подсветить цепочку, нажмите, чтобы открыть "
         "его карточку. Число в углу знания это цена в Monkey Money.",
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
         "Силы и Powers Pro: урон, длительность, радиус, перезарядка.",
         group("powers", "Силы", groups["powers"]) + group("pro", "Powers Pro", groups["pro"]),
         [("powers", "Силы"), ("pro", "Powers Pro")])


def hero_level_rows(folder, base, ucost):
    """Attack numbers per hero level: level 1 is the base model, level N the "<Hero> N.json" model."""
    rows, prev = [], None
    for lvl in range(1, 21):
        f = folder / f"{folder.name} {lvl}.json"
        if lvl > 1 and not f.exists():
            continue
        s = tier_stats(combat_stats(base if lvl == 1 else load(f), ucost))
        rows.append((lvl, s, prev))
        prev = s
    return rows


START_CASH = 650  # standard starting cash; not in the export (the game model default, not a mode modifier)


def hero_calc(totals, cost):
    """Hero calculator: round each level is reached for a placement round and map difficulty, and the round the
    hero becomes affordable. totals = cumulative XP for levels 2..20. The XP per round is the game's formula
    (not in the export, see Blooncyclopedia "Hero XP"): 20r+20 up to round 20, 40r-380 up to 50, 90r-2880 after,
    times the map difficulty, rounded half up each round. hcalc() in search.js does the math."""
    cash = [round(p + b) for p, b in round_cash().values()]
    maps = [("Beginner", 1), ("Intermediate", 1.1), ("Advanced", 1.2), ("Expert", 1.3)]
    return (f"<div class='hcalc' data-reqs='{json.dumps(totals)}' data-cost='{cost}' data-start='{START_CASH}' "
            f"data-cash='{json.dumps(cash)}'><div class='hcalc-in'>"
            "<label>Карта <select>" + "".join(f"<option value='{m}'>{esc(t(n, fallback=n))}</option>" for n, m in maps)
            + "</select></label><label>Ставлю на раунде <input type='number' min='1' max='140' value='1'></label></div>"
            "<p class='hcalc-cash'></p><div class='hcalc-out'></div></div>")


def build_heroes():
    upgrades = {f.stem: load(f) for f in json_files("Upgrades")}
    ucost = {u.get("name"): u.get("cost", 0) for u in upgrades.values()}
    heroes = []
    for folder in sorted(p for p in (DATA / "Heroes").iterdir() if p.is_dir()):
        hid = folder.name
        base = load(folder / f"{hid}.json")
        # level N comes from the upgrade's tier (N - 1); xpCost is the XP from level N-1 to N, hero XP scale included
        top = load(folder / f"{hid} 20.json")
        levels = sorted(((upgrades[u].get("tier", 0) + 1, upgrades[u].get("xpCost", 0))
                         for u in top.get("appliedUpgrades") or [] if u in upgrades))
        heroes.append((base.get("cost", 0), t(hid, fallback=hid), hid, base, levels, abilities_of([(None, top)]), top))
    global current_file
    selector = diff_selector()
    heroes.sort(key=lambda h: h[:3])
    for cost, name, hid, base, levels, abils, top in heroes:
        current_file = f"hero-{hid}.html"
        # ability icon on the level that unlocks it (level upgrades have no icons of their own)
        pics = {upgrades[b["addedViaUpgrade"]].get("tier", 0) + 1: icon("abilities", (b.get("icon") or {}).get("guidRef") or "", 32)
                for b in abils.values() if b.get("addedViaUpgrade") in upgrades}

        def lvl_text(n):
            text = esc(re.sub(r"</?(sup|sub|b|i|u)>|</?color[^>]*>", "", t(f"{hid} Level {n} Description", fallback="")))
            return f"<span class='mod-name'>{pics[n]}<span>{text}</span></span>" if pics.get(n) else text
        total, rows = 0, [(1, "–", 0, lvl_text(1))]
        for lvl, xp in levels:
            total += xp
            rows.append((lvl, xp, total, lvl_text(lvl)))
        lvl_rows = hero_level_rows(DATA / "Heroes" / hid, base, ucost)
        about = ("<div class='hero-row'>" + icon("heroes", hid, 120, "ic portrait") + "<div>"
                 + game_text(t(f"{hid} Description"))
                 + stats([("цена", price([cost])), ("дальность", num(base.get("range"))), ("XP до 20 уровня", total)])
                 + "</div></div>")
        numbers = (levels_table(lvl_rows, first_col="Уровень", only_changed=True)
                   + (f"<details><summary>Все уровни</summary>" + levels_table(lvl_rows, first_col="Уровень") + "</details>"
                      if len(lvl_rows) > 2 else ""))
        body = (selector
                + card("about", name, about, en_id=hid, section="Герои")
                + card("levels", "Уровни и опыт", table(["Уровень", "XP до уровня", "XP всего", "Что даёт"],
                                                        [(a, b, c, Raw(d)) for a, b, c, d in rows]), section=name)
                + card("calc", "Калькулятор", hero_calc([r[2] for r in rows[1:]], cost), section=name)
                + card("numbers", "Числа по уровням", numbers, section=name)
                + (card("abilities", "Способности", abilities_table(
                    abils, lambda up: f"уровень {upgrades[up].get('tier', 0) + 1}" if up in upgrades else esc(up)), section=name)
                   if abils else ""))
        page(current_file, name, esc(t(f"{hid} Short Description", fallback="")), body,
             toc=[("about", "Описание"), ("levels", "Уровни и опыт"), ("calc", "Калькулятор"), ("numbers", "Числа по уровням")]
             + ([("abilities", "Способности")] if abils else []))
    current_file = "heroes.html"
    # hero select screen order from game.json (btd6-knowledge-dumper F6 on that screen); heroSet index, then cost, as fallbacks
    order = {hid: i for i, hid in enumerate(GAME.get("heroScreen") or [])} or {h["id"]: h["index"] for h in GAME.get("heroSet") or []}
    heroes.sort(key=lambda h: (order.get(h[2], 99), h[:3]))
    grid = "".join(f"<a class='tile tower-tile' href='hero-{esc(hid)}.html' data-order='{i}' data-cost='{cost}' "
                   f"data-xp='{sum(xp for _, xp in levels)}'>{icon('heroes', hid, 72)}"
                   f"<span><b>{esc(name)}</b>{price([cost], 'cost tile-price')}</span></a>"
                   for i, (cost, name, hid, base, levels, *_) in enumerate(heroes))
    page("heroes.html", "Герои", "",
         selector + sort_bar("hero-grid", [("order", "Как в игре"), ("cost", "По цене"), ("xp", "По XP до 20 уровня")])
         + f"<div class='grid cols3' id='hero-grid'>{grid}</div>")


LINKS = [  # (title, url, what it is)
    ("Blooncyclopedia", "https://www.bloonswiki.com", "Большая вики по всем играм Bloons: тексты, история изменений, стратегии."),
    ("r/btd6", "https://www.reddit.com/r/btd6/", "Сообщество игры на Reddit."),
    ("Ninja Kiwi", "https://ninjakiwi.com", "Разработчики игры: новости и патчноуты."),
    ("BTD6 Mod Helper", "https://github.com/gurrenm3/BTD-Mod-Helper", "Библиотека для модов, через неё выгружены данные этого сайта."),
    ("BTD6 Tech Wiki", "https://github.com/Antonzlo/btd6-tech-wiki", "Исходный код этого сайта."),
]


def build_links():
    rows = [(Raw(f"<a href='{u}' rel='noopener'><b>{esc(n)}</b></a>"), d) for n, u, d in LINKS]
    page("links.html", "Ссылки", "", table(["Сайт", "Что там"], rows))


def sort_bar(grid_id, options):
    """Buttons that reorder the tiles of #grid_id by a numeric data-<key>; the first option is the initial order.
    The "order" key also lays the grid out in 3 columns, like the game's hero select screen."""
    return (f"<div class='tagbar sortbar' data-grid='{grid_id}'>"
            + "".join(f"<button type='button' data-sort='{k}'{' class=on' if i == 0 else ''}>{esc(n)}</button>"
                      for i, (k, n) in enumerate(options)) + "</div>")


def build_index():
    tiles = "".join(f"<a class='tile page-tile' href='{f}'>{page_icon(f, 56)}<span><b>{esc(t(n, fallback=n))}</b><small>{esc(s)}</small></span></a>" for f, n, s in PAGES[1:])
    page("index.html", "BTD6 Tech Wiki",
         "Точные числа Bloons TD 6 из файлов игры: урон и цены башен, уровни героев, HP боссов, "
         "режимы, доход, баффы. Поиск по сайту: клавиша /.",
         f"<div class='grid home-grid'>{tiles}</div>")


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


# ---------- towers ----------

TOWER_SETS = {1: "Primary", 2: "Military", 4: "Magic", 8: "Support"}
# shop order: GameModel.towerSet from game.json. Towers missing from data/Towers are skipped by the pages.
SHOP_ORDER = [t["id"] for t in sorted(GAME["towerSet"], key=lambda t: t["index"])]
EFFECT_WORDS = ("Slow", "Freeze", "Stun", "Knockback", "Wind", "DamageOverTime", "AddBehaviorToBloon", "Bleed", "Burn")


def num(v):
    return round(v, 4) if isinstance(v, float) else v


def mod_text(b):
    """A damage-modifier or effect behavior as text: kind + its numeric fields."""
    st = short_type(b)
    if "DamageModifier" in st:
        fields = {k: v for k, v in b.items() if scalar(v) and k not in ("$type", "name", "collisionPass") and v not in (0, 0.0, False, "")}
        return label_mod(st) + ": " + ", ".join(f"{k} {fmt(v)}" for k, v in fields.items())
    if any(w in st for w in EFFECT_WORDS):
        nums = {k: v for k, v in b.items() if scalar(v) and not k.startswith("$") and k not in ("name",)}
        return ", ".join([label(st)] + [f"{k} {fmt(v)}" for k, v in nums.items() if v not in (None, 0, 0.0, False, "")])
    return label(st)


def label_mod(st):
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", st.replace("DamageModifierFor", "").replace("Model", "")) or st


def nested_towers(x, root=True):
    """TowerModels inside a model (not descending into them; combat_stats recurses on its own)."""
    if isinstance(x, dict):
        if not root and short_type(x) == "TowerModel":
            yield x
            return
        for v in x.values():
            yield from nested_towers(v, False)
    elif isinstance(x, list):
        for v in x:
            yield from nested_towers(v, False)


def combat_stats(d, upgrade_costs):
    """Combat numbers of a tower (or sub-tower / hero) model as a flat list: attack -> projectile ->
    damage, pierce, attack rate, projectile count, range; each row also gets the damage per shot
    (damage x count) and the simplified DPS (shot damage / reload), plus effects with numbers and the
    bloon properties the projectile cannot pop (immuneBloonProperties)."""
    attacks, projectiles, abilities, other = [], [], [], []
    for b in d.get("behaviors") or []:
        if not isinstance(b, dict) or skipped(b):
            continue
        st = short_type(b)
        if st.startswith("AttackModel") or st.endswith("AttackModel") or st == "AttackAirUnitModel":  # Ace, Heli fly their attacks
            weapons = []
            for w in b.get("weapons") or []:
                em = w.get("emission") or {}
                rate, count = num(w.get("rate")), em.get("count") or 1
                projs = []
                if isinstance(w.get("projectile"), dict):
                    projs = []
                    stack = [(w["projectile"], "Снаряд", count, 0, rate, num(b.get("range")), projs)]
                    while stack:
                        p, lbl, cnt, depth, rt, rg, acc = stack.pop()
                        beh = [x for x in p.get("behaviors") or [] if isinstance(x, dict)]
                        mods, effects = [], []
                        for x in beh:
                            xs = short_type(x)
                            if "DamageModifier" in xs:
                                mods.append(mod_text(x))
                            elif any(w2 in xs for w2 in EFFECT_WORDS):
                                effects.append(mod_text(x))
                        dmg = next((x for x in beh if short_type(x) == "DamageModel"), None)
                        damage = num(dmg["damage"]) if dmg else None
                        pierce = num(p.get("pierce"))
                        mask = (dmg or {}).get("immuneBloonProperties") or 0
                        shot = None if damage is None else damage * cnt
                        acc.append({"attack": label(st), "weapon": len(weapons) + 1, "projectile": lbl, "depth": depth,
                                    "count": cnt, "damage": damage, "pierce": pierce, "rate": rt, "range": rg,
                                    "immune": [[bit, name] for bit, name in BLOON_PROPS if mask & bit],
                                    "shotDamage": shot, "dps": None if (shot is None or not rt) else shot / rt,
                                    "mods": mods, "effects": sorted(set(effects))})
                        kids = [(v, label(short_type(x)), (x.get("emission") or {}).get("count") or 1, depth + 1, rt, rg, acc)
                                for x in beh for v in x.values() if isinstance(v, dict) and "ProjectileModel" in v.get("$type", "")]
                        stack.extend(reversed(kids))  # popped in model order, children right after their parent
                projectiles.extend(projs)
                weapons.append({"rate": rate, "count": count, "emission": label(short_type(em)) if em else "", "proj": projs})
            attacks.append({"name": label(st), "range": num(b.get("range")), "weapons": weapons})
        elif st == "AbilityModel":
            abilities.append({"name": t(b.get("displayName") or "", fallback=b.get("displayName") or b.get("name", "")),
                              "cooldown": num(b.get("cooldown"))})
        elif not any(s in st for s in ("Sound", "Effect", "Display")):
            other.append(label(st))
    # sub-towers (sentries, drones, pets, totems) sit inside the model as whole TowerModels: their attacks
    # join this tower's, prefixed with the sub-tower name
    seen = set()
    for sub in nested_towers(d):
        sid = sub.get("baseId") or sub.get("name") or ""
        if sid in seen:
            continue
        seen.add(sid)
        s = combat_stats(sub, {})
        for a in s["attacks"]:
            a["name"] = f"{t(sid, fallback=sid)}: {a['name']}"
        attacks.extend(s["attacks"])
        projectiles.extend(s["projectiles"])
    parts = [d.get("cost", 0)] + [upgrade_costs.get(u, 0) for u in d.get("appliedUpgrades") or []]
    return {"cost": sum(parts), "parts": parts, "range": num(d.get("range")), "attacks": attacks,
            "projectiles": projectiles, "abilities": abilities, "other": sorted(set(other))}


def abilities_of(models):
    """Abilities across (upgrade, model) pairs, first appearance wins: {display name: AbilityModel}.
    The upgrade of the first model that has it replaces addedViaUpgrade, which keeps the old name when a
    tier 5 swaps the ability (Plasma Monkey Fan Club says "Super Monkey Fan Club")."""
    out = {}
    for up, d in models:
        for b in d.get("behaviors") or []:
            if isinstance(b, dict) and short_type(b) == "AbilityModel" and not b.get("isHidden") and b.get("displayName"):
                out.setdefault(b["displayName"], {**b, "addedViaUpgrade": up or b.get("addedViaUpgrade")})
    return out


def ability_effect(b):
    """Effect numbers of an AbilityModel: speed-up, damage, radius from its sub-behaviors."""
    bits = []
    for sub in b.get("behaviors") or []:
        if not isinstance(sub, dict):
            continue
        st = short_type(sub)
        if st == "TurboModel":
            bits.append(f"ускорение ×{fmt(sub.get('multiplier'))}")
        elif st == "ActivateAttackModel":
            for atk in sub.get("attacks") or []:
                for w in atk.get("weapons") or []:
                    proj = w.get("projectile") or {}
                    radius = proj.get("radius")
                    if radius is not None:
                        bits.append(f"радиус {fmt(radius)}")
                    for pbeh in proj.get("behaviors") or []:
                        if isinstance(pbeh, dict) and short_type(pbeh) == "DamageModel":
                            bits.append(f"урон {fmt(pbeh.get('damage'))}")
    return "; ".join(bits) if bits else "–"


def abilities_table(abils, source):
    """Table of abilities: icon, name, where it comes from (source(upgrade name)), cooldown, effect, game text."""
    rows = []
    for key, b in abils.items():
        pic = icon("abilities", (b.get("icon") or {}).get("guidRef") or "", 40) or "<span class='mod-ic'></span>"
        text = t(f"{key} Ability Description", fallback=b.get("description") or "")
        rows.append((Raw(f"<span class='mod-name'>{pic}<b>{esc(t(f'{key} Ability', key, fallback=key))}</b></span>"),
                     Raw(source(b.get("addedViaUpgrade") or "")), Raw(f"{fmt(num(b.get('cooldown')))}&nbsp;с"),
                     Raw(ability_effect(b)),
                     re.sub(r"</?(sup|sub|b|i|u)>|</?color[^>]*>", "", text)))
    return table(["Способность", "Откуда", "Перезарядка", "Эффект", "Описание"], rows) if rows else ""


TIER_ROW_KEYS = ["000"]
for _i in range(3):
    for _t in range(1, 6):
        TIER_ROW_KEYS.append(("0" * _i) + str(_t) + ("0" * (2 - _i)))
TIER_ROW_KEYS.append("Paragon")


def tier_stats(d):
    """Numbers of one tier model for its main projectile (highest simplified DPS over all attacks):
    range, cooldown, damage per shot (× projectile count), pierce, DPS, properties it cannot pop."""
    d = d or {}
    projs = [p for p in d.get("projectiles") or [] if p.get("damage") is not None]
    p = max(projs, key=lambda p: p.get("dps") or 0, default={})
    return {"range": num(d.get("range")), "rate": p.get("rate"), "damage": p.get("shotDamage"), "pierce": p.get("pierce"),
            "dps": num(p.get("dps")), "immune": p.get("immune") or []}


def levels_table(rows, first_col="Тир", only_changed=False):
    """Attack numbers per row: (label, stats, previous stats or None). Cells that differ from the previous
    row's are highlighted; with only_changed, rows where nothing changed are left out."""
    head = f"<tr><th>{first_col}</th><th>Дальность</th><th>Перезарядка, с</th><th>Урон за выстрел</th><th>Пробив.</th><th>Примерный DPS</th><th>Не лопает</th></tr>"
    keys = ("range", "rate", "damage", "pierce", "dps", "immune")
    body = ""
    for label, s, prev in rows:
        diff = {k for k in keys if prev is not None and s[k] != prev[k]}
        if only_changed and prev is not None and not diff:
            continue
        immune = "".join(f"<a class='chip no' href='bloons.html#prop-{bit}'>{esc(n)}</a> " for bit, n in s["immune"]) or "\u2013"
        cells = "".join(f"<td class='n{' chg' if k in diff else ''}'>{fmt(s[k])}</td>" for k in keys[:-1])
        body += (f"<tr><td>{esc(label)}</td>{cells}"
                 f"<td{' class=chg' if 'immune' in diff else ''}>{immune}</td></tr>")
    return f"<div class='wrap'><table><thead>{head}</thead><tbody>{body}</tbody></table></div>"


def tier_table(variants):
    """Static per-tier numbers: base tower, then every tier of each upgrade path, then the paragon.
    Each tier is compared with the tier below it on the same path (100 with 000, 200 with 100)."""
    stats_of = {k: tier_stats(variants[k]) for k in TIER_ROW_KEYS if variants.get(k)}
    below = lambda k: None if k in ("000", "Paragon") else re.sub(r"[1-5]", lambda m: str(int(m.group()) - 1), k)
    return levels_table([(k, s, stats_of.get(below(k))) for k, s in stats_of.items()], first_col="Тир")


def diff_selector():
    """Difficulty switch. Every price() on the page is recomputed in the browser (applyDiff in search.js)."""
    diffs = {}
    for mode in ("Easy", "Medium", "Hard", "Impoppable"):
        mult = next((m.get("multiplier") for m in load(DATA / "Mods" / f"{mode}.json").get("mutatorMods") or []
                     if short_type(m) == "GlobalCostModModel"), None)
        diffs[mode] = mult if mult is not None else 1.0
    # Impoppable is a mode played on Hard: the two cost bonuses add up (1 + 0.08 + 0.12 = 1.2; Quincy $650,
    # Super Monkey $3000; multiplying them would give $655 and $3025)
    diffs["Impoppable"] = round(diffs["Impoppable"] + diffs["Hard"] - 1, 6)
    return ("<div class='diff' role='group' aria-label='Сложность'><span>Сложность</span>" + "".join(
        f"<button type='button' data-mult='{m}'{' class=on' if m == 1 else ''}>{icon('ui', f'mode-{n}', 22)}{esc(t(n, fallback=n))}</button>"
        for n, m in diffs.items()) + "</div>")


def price(parts, cls="cost"):
    """A price shown at Medium; diff_selector() on the page switches it, each part (purchase) rounded on its own."""
    return Raw(f"<span class='{cls}' data-parts='{','.join(str(p) for p in parts)}'>${fmt(sum(parts))}</span>")


def build_towers():
    global current_file
    upgrades = {load(f).get("name"): load(f) for f in json_files("Upgrades")}
    ucost = {k: v.get("cost", 0) for k, v in upgrades.items()}
    selector = diff_selector()
    tiles = {}
    for folder in sorted(p for p in (DATA / "Towers").iterdir() if p.is_dir()):
        tid = folder.name
        base = load(folder / f"{tid}.json")
        variants = {}
        for f in folder.glob(f"{tid}-*.json"):
            suffix = f.stem.split("-", 1)[1]
            variants[suffix] = combat_stats(load(f), ucost)
        variants["000"] = combat_stats(base, ucost)
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
        # abilities from the single-path models, tier by tier, then the paragon
        codes = ["".join(str(n) if j == i else "0" for j in range(3)) for n in range(1, 6) for i in range(3)] + ["Paragon"]
        models = [load(folder / f"{tid}-{c}.json") for c in codes if (folder / f"{tid}-{c}.json").exists()]
        abils = abilities_of(((m.get("appliedUpgrades") or [None])[-1], m) for m in models)
        where = {u: f"путь {i + 1}, {n}: {t(u, fallback=u)}" for i, path in enumerate(paths) for n, u in enumerate(path, 1)}
        if para:
            where[u] = f"{t('Paragon', fallback='Парагон')}: {t(u, fallback=u)}"
        body = (
            selector
            + card("about", name,
                 "<div class='hero-row'>" + icon('towers', tid, 120, 'ic portrait') + "<div>" + game_text(t(f"{tid} Description", f"{tid}Description"))
                 + stats([("цена", price([base.get("cost", 0)])), ("дальность", base.get("range")),
                          ("радиус места", base.get("radius")), ("категория", t(TOWER_SETS.get(base.get("towerSet")), fallback=""))])
                 + "</div></div>",
                 en_id=tid, section="Башни")
            + card("upgrades", "Улучшения", f"<div class='paths'>{''.join(cols)}</div>{para}", section=name)
            + (card("abilities", "Способности", abilities_table(abils, lambda up: esc(where.get(up, t(up, fallback=up)))),
                    section=name) if abils else "")
            + card("crosspath", "Кроссапгрейд",
                   "<p class='note'>Выберите тиры путей, как в игре. Показаны цена со всеми улучшениями, "
                   "атаки, перезарядка, урон и пробивание каждого снаряда, включая вложенные (взрывы, осколки).</p>"
                   f"<div class='xp' data-tower='{esc(tid)}'>{picker}"
                   + (f"<div class='xp-row'><span>Особые</span>" + "".join(
                       f"<button type='button' data-variant='{esc(k)}'>{esc(k)}</button>" for k in sorted(extra)) + "</div>" if extra else "")
                   + "<div class='xp-out'></div></div>"
                   f"<script type='application/json' class='xp-data'>{json.dumps(variants, ensure_ascii=False).replace('</', '<\\/')}</script>",
                   section=name)
            + card("tiers", "Числа по тирам", tier_table(variants), section=name)
        )
        page(file, name, esc(t(TOWER_SETS.get(base.get('towerSet')), fallback='')),
             body, toc=[("about", "Описание"), ("upgrades", "Улучшения")] + ([("abilities", "Способности")] if abils else [])
             + [("crosspath", "Кроссапгрейд"), ("tiers", "Числа по тирам")])
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
         "Башни по категориям, в порядке магазина.", selector + "".join(body))


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
# bits from the game enum (game.json), Russian labels by enum name
PROP_LABELS = {"Lead": "Свинец", "Black": "Чёрный", "White": "Белый", "Purple": "Фиолетовый", "Frozen": "Заморожен",
               "Immune": "Неуязвим", "Glass": "Стекло"}
BLOON_PROPS = [(bit, PROP_LABELS.get(n, n)) for n, bit in GAME["bloonProperties"].items() if bit]


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
                f"<a class='badge' href='bloons.html#{esc(BLOONS[c].get('baseId', c))}'><span>дети</span>"
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
         "HP слоя, RBE (сумма HP всех слоёв), деньги за полное лопание, скорость, свойства и дети каждого шара.",
         "".join(body), toc)


@functools.cache
def round_cash(rs="DefaultRoundSet"):
    """{round: (pop cash, end of round bonus)}: 1 $ per layer popped times the DefaultIncomeSet multiplier of the round,
    bonus from the Medium mode model (BonusCashPerRoundModModel: baseCash + round * roundMultiple)."""
    income = load(DATA / "IncomeSets" / "DefaultIncomeSet.json")

    def income_mult(r):
        return next((th["multiplier"] for th in income.get("thresholds") or [] if r <= th["threshold"]),
                    income.get("finalMultiplier", 1))
    bonus_mod = next((m for m in load(DATA / "Mods" / "Medium.json").get("mutatorMods") or []
                      if short_type(m) == "BonusCashPerRoundModModel"), {})
    out = {}
    for f in (DATA / "Rounds" / rs).glob("*.json"):
        r = int(f.stem)
        pop = sum(g["count"] * pops(g["bloon"]) for g in load(f).get("groups") or []) * income_mult(r)
        out[r] = (pop, bonus_mod.get("baseCash", 100) + r * bonus_mod.get("roundMultiple", 1))
    return dict(sorted(out.items()))


def build_rounds():
    bloons = BLOONS

    def tags(b):
        m = bloons[b]
        return {k for k, on in (("camo", m.get("isCamo")), ("regrow", m.get("isGrow")), ("fortified", m.get("isFortified")),
                                ("lead", m.get("baseId") == "Lead"), ("ceramic", m.get("baseId") == "Ceramic"),
                                ("moab", m.get("isMoab"))) if on}

    prop_names = {"camo": t("Camo"), "regrow": t("Regrow"), "fortified": "Укреплённые"}
    filters = [("", "Все"), ("new", "С новым"), ("camo", t("Camo")), ("regrow", t("Regrow")), ("fortified", "Укреплённые"),
               ("lead", t("Lead")), ("ceramic", t("Ceramic")), ("moab", "MOAB-класс")]

    sections, toc = [], []
    for rs, title in (("DefaultRoundSet", "Обычные раунды"), ("AlternateRoundSet", "Альтернативные раунды (ABR)")):
        folder = DATA / "Rounds" / rs
        rows, total, seen = [], 0, set()
        for f in sorted(folder.glob("*.json"), key=lambda f: int(f.stem)):
            r = int(f.stem)
            groups = load(f).get("groups") or []
            chips = "".join(f"<a class='chip bchip' href='bloons.html#{esc(bloons[g['bloon']].get('baseId', g['bloon']))}'>"
                            f"<i class='bi bi-{bloon_css(g["bloon"])}'></i>{g['count']}× {esc(bloon_name(g['bloon']))}</a>" for g in groups)
            r_rbe = sum(g["count"] * rbe(g["bloon"]) for g in groups)
            cash, bonus = round_cash(rs)[r]
            total += cash + bonus
            dur = max((g["end"] for g in groups), default=0) / 60
            # first appearance of a bloon type or a property (camo, regrow, fortified)
            row_tags = set().union(*(tags(g["bloon"]) for g in groups)) if groups else set()
            feats = [bloons[g["bloon"]].get("baseId") for g in groups] + [p for p in ("camo", "regrow", "fortified") if p in row_tags]
            new = list(dict.fromkeys(x for x in feats if x not in seen))
            seen.update(new)
            badges = "".join(f"<span class='chip new'>{esc(prop_names[x])}</span>" if x in prop_names
                             else f"<a class='chip new' href='bloons.html#{esc(x)}'>{esc(t(x, fallback=x))}</a>" for x in new)
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
         "Шары каждого раунда, RBE и деньги. За лопание 1 $ за слой с множителем дохода раунда, "
         "бонус за раунд 100 $ + номер раунда. HP MOAB-класса в поздних раундах растёт, здесь базовые значения.",
         bloon_icon_style(set(bloons)) + "".join(sections), toc)


def main():
    global current_file, INDEX
    shutil.rmtree(SITE, ignore_errors=True)  # no stale pages from an older layout
    for lang in LANGS:
        set_lang(lang)
        INDEX = []
        for file, build in (("paragon.html", build_paragon), ("bosses.html", build_bosses), ("modes.html", build_modes),
                            ("income.html", build_income), ("buffs.html", build_buffs),
                            ("knowledge.html", build_knowledge), ("powers.html", build_powers),
                            ("towers.html", build_towers), ("heroes.html", build_heroes), ("bloons.html", build_bloons),
                            ("rounds.html", build_rounds),
                            ("links.html", build_links), ("index.html", build_index)):
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
