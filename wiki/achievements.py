"""Achievements page: goal, rewards, hidden and co-op flags from achievements.json (knowledge dumper),
names and descriptions from textTable. What completes an achievement is game code, the description says it."""
import re
from wiki import core
from wiki.core import DATA, INDEX, card, esc, fmt, icon, load, page, t


def reward(part):
    """One reward of a loot string: Kind:arg,count (MonkeyMoney:250, Power:MoabMine,3, InstaMonkey:BombShooter,000)."""
    kind, _, arg = part.partition(":")
    kind, args = kind.strip(), [a.strip() for a in arg.split(",")] if arg else []
    if kind == "MonkeyMoney":
        return icon("ui", "mm", 20) + fmt(int(args[0]))
    if kind == "KnowledgePoints":
        return icon("ui", "knowledge", 20) + f"{args[0]} очков знаний"
    if kind == "Power":
        return (icon("ui", f"power-{args[0]}", 20) + esc(t(args[0], fallback=args[0]))
                + (f" ×{args[1]}" if len(args) > 1 else ""))
    if kind == "InstaMonkey":
        return f"{icon('towers', args[0], 20)}инста {esc(t(args[0], fallback=args[0]))} {'-'.join(args[1])}"
    if kind == "RandomInstaMonkey":
        # ponytail: read as tier, count[, tower] from the values (tiers 0-5, small counts); not confirmed in game code
        tier, count, *tower = args
        who = esc(t(tower[0], fallback=tower[0])) if tower else "случайной башни"
        return f"инста {who} тира {tier} ×{count}"
    if kind == "Trophy":
        return f"{args[0]} трофеев"
    return esc(t(kind, fallback=kind))  # game mode unlocks such as BigBloonsMode


def build_achievements():
    achievements = load(DATA / "KnowledgeLayout" / "achievements.json")
    # reward kind of a loot part -> filter tag
    kinds = {"MonkeyMoney": "mm", "Power": "power", "InstaMonkey": "insta", "RandomInstaMonkey": "insta",
             "KnowledgePoints": "knowledge", "Trophy": "trophy"}
    rows = []
    for a in achievements:
        n = a["id"]
        name = t(f"Achievement {n} Name", fallback=a["type"])
        desc = re.sub(r"</?[a-z]+[^>]*>", "", t(f"Achievement {n} Description", fallback="")).replace("{0}", fmt(a["goal"]))
        INDEX.append([name, "Достижения", f"{core.current_file}#a{n}", a["type"]])
        parts = [p for p in (a["loot"] or "").split("#") if p.strip()]
        tags = {kinds.get(p.split(":")[0].strip(), "mode") for p in parts}
        tags |= {tag for on, tag in ((a["hidden"], "hidden"), (a["coop"], "coop")) if on}
        flags = "".join(f" <span class='badge'><b>{label}</b></span>" for on, label in
                        ((a["hidden"], "скрытое"), (a["coop"], "кооператив")) if on)
        # a hidden achievement is blurred like a spoiler until clicked (or "show hidden" is on); its flags stay readable
        blur = " class='spoil'" if a["hidden"] else ""
        cells = (f"<div class='ach'><span{blur}>{icon('achievements', str(n), 40)}</span>"
                 f"<span><b id='a{n}'{blur}>{esc(name)}</b>{flags}</span></div>",
                 f"<span{blur}>{esc(desc)}</span>",
                 f"<div{blur}>" + "".join(f"<div class='reward'>{reward(p)}</div>" for p in parts) + "</div>")
        rows.append(f"<tr data-tags='{' '.join(sorted(tags))}'{' class=spoiler' if a['hidden'] else ''}>"
                    + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    filters = [("", "Все"), ("hidden", "Скрытые"), ("coop", "Кооператив"), ("power", "Силы"), ("insta", "Инсты"),
               ("knowledge", "Очки знаний"), ("trophy", "Трофеи"), ("mode", "Режимы")]
    bar = ("<div class='tagbar' data-target='#ach-t'>"
           + "".join(f"<button type='button' data-tag='{k}'{' class=on' if not k else ''}>{esc(label)}</button>"
                     for k, label in filters) + "</div>")
    head = "".join(f"<th>{h}</th>" for h in ("Достижение", "Условие", "Награда"))
    body = (bar + "<input class='filter' type='search' placeholder='Фильтр: название, условие или награда' "
            "aria-label='Фильтр достижений' data-filter='#ach-t tbody tr'>"
            "<label class='reveal'><input type='checkbox' data-reveal='#ach-t'> Показать скрытые</label>"
            f"<div class='wrap'><table id='ach-t'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    hidden = sum(a["hidden"] for a in achievements)
    page("achievements.html", "Достижения",
         f"Все {len(achievements)} достижений: условие и награда. {hidden} скрытых в игре показаны как ???, "
         "здесь они размыты: нажмите на строку, чтобы открыть.",
         card("all", "Достижения", body, section="Достижения"), [("all", "Достижения")])
