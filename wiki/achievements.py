"""Achievements page: goal, rewards, hidden and co-op flags from achievements.json (knowledge dumper),
names and descriptions from textTable. What completes an achievement is game code, the description says it."""
import re
from wiki import core
from wiki.core import DATA, INDEX, card, esc, fmt, icon, load, page, t, table


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
    groups = {False: [], True: []}
    for a in achievements:
        n = a["id"]
        name = t(f"Achievement {n} Name", fallback=a["type"])
        desc = re.sub(r"</?[a-z]+[^>]*>", "", t(f"Achievement {n} Description", fallback="")).replace("{0}", fmt(a["goal"]))
        INDEX.append([name, "Достижения", f"{core.current_file}#a{n}", a["type"]])
        flags = "".join(f" <span class='badge'><b>{label}</b></span>" for on, label in
                        ((a["hidden"], "скрытое"), (a["coop"], "кооператив")) if on)
        rewards = "".join(f"<div class='reward'>{reward(p)}</div>" for p in (a["loot"] or "").split("#") if p.strip())
        title = f"<div class='ach'>{icon('achievements', str(n), 40)}<span><b id='a{n}'>{esc(name)}</b>{flags}</span></div>"
        groups[a["hidden"]].append((title, esc(desc), rewards))
    heads = ["Достижение", "Условие", "Награда"]
    page("achievements.html", "Достижения",
         "Все достижения: условие, награда. Скрытые в игре показаны как ???, здесь они открыты.",
         card("visible", "Обычные", table(heads, groups[False]), section="Достижения")
         + card("hidden", "Скрытые", table(heads, groups[True]), section="Достижения"),
         [("visible", "Обычные"), ("hidden", "Скрытые")])
