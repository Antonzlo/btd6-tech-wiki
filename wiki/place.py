"""Data for trying placements on map pages: every tower tier and hero level with its range and the buffs it gives
other towers, written to place.js next to search.js and loaded by map pages only."""
import hashlib
import json
import re

from wiki import core
from wiki.core import DATA, load, short_type, t
from wiki.buffs import effect_line

# support models that reach other towers by range (or the whole map); projectile-applied buffs (Alchemist brews) and
# the marker on a receiving tower are not here
SUPPORT_END = ("SupportModel", "SupportZoneModel", "ZoneModel")


def tier_key(f):
    """Alchemist-300 -> "300", Alchemist -> "000", Alchemist-Paragon -> "Paragon", "Adora 3" -> "3", Adora -> "1"."""
    m = re.search(r"-(\d{3}|Paragon)$", f.stem) or re.search(r" (\d+)$", f.stem)
    return m.group(1) if m else ("1" if f.parent.parent.name == "Heroes" else "000")


def supports(model):
    """Buffs a tower model gives: each as a dict the page checks against a target tower."""
    out = []

    def walk(o, ability):
        if isinstance(o, dict):
            k = short_type(o)
            # "Bloon" in the type or an overlay: acts on bloons (camo removal zones), not on towers
            if k.endswith(SUPPORT_END) and "Bloon" not in k and "overlayType" not in o and ("buffIconName" in o or "filters" in o):
                fl = o.get("filters") or []
                kinds = {short_type(x): x for x in fl}
                b = {"t": effect_line(o), "g": bool(o.get("isGlobal") or o.get("isGlobalRange")),
                     "self": bool(o.get("appliesToOwningTower") or o.get("canEffectThisTower") or o.get("affectSelf")),
                     "u": o.get("mutatorId") if o.get("isUnique") else None, "ab": ability,
                     "i": o.get("buffIconName") if o.get("showBuffIcon", True) else None}
                if o.get("isCustomRadius"):
                    b["r"] = o.get("customRadius")
                elif isinstance(o.get("range"), (int, float)) and o["range"] < 9e6 and k.startswith("Activate"):
                    b["r"] = o["range"]
                if "FilterInSetModel" in kinds:
                    x = kinds["FilterInSetModel"]
                    b["sets"] = x.get("towerSets") or [x.get("towerSet")]
                if "FilterInBaseTowerIdModel" in kinds:
                    b["ids"] = kinds["FilterInBaseTowerIdModel"].get("baseIds") or []
                if "FilterParagonModel" in kinds:
                    b["para"] = bool(kinds["FilterParagonModel"].get("inclusive"))
                if o.get("onlyAffectParagon"):
                    b["para"] = True
                other = [core.label(x) for x in kinds if x not in ("FilterInSetModel", "FilterInBaseTowerIdModel", "FilterParagonModel")]
                if other:
                    b["c"] = other  # conditions the page does not check, shown with the buff
                out.append(b)
            for key, v in o.items():
                walk(v, ability or key == "abilities")
        elif isinstance(o, list):
            for v in o:
                walk(v, ability)
    walk(model.get("behaviors"), False)
    uniq = {json.dumps(b, sort_keys=True): b for b in out}  # one model per tower set is repeated often
    return list(uniq.values())


def place_data():
    """{"B": [unique buffs], "T": {base id: {"set": tower set bit, "tiers": {tier: [range, [buff indexes]]}}}} for
    towers and heroes; buffs repeat across tiers, so each is stored once."""
    out, buffs, index = {}, [], {}

    def ref(b):
        key = json.dumps(b, sort_keys=True)
        if key not in index:
            index[key] = len(buffs)
            buffs.append(b)
        return index[key]
    for folder in ("Towers", "Heroes"):
        for d in sorted(p for p in (DATA / folder).iterdir() if p.is_dir()):
            tiers = {}
            tower_set = None
            for f in sorted(d.glob("*.json")):
                m = load(f)
                tower_set = tower_set or m.get("towerSet")
                tiers[tier_key(f)] = [m.get("range"), [ref(b) for b in supports(m)]]
            out[d.name] = {"set": tower_set, "tiers": tiers}
    # icon urls: the tower or hero portrait, and each buff icon the game shows above a buffed tower
    icons = {tid: core.data_uri("heroes" if (DATA / "Heroes" / tid).is_dir() else "towers", tid) for tid in out}
    buff_icons = {b["i"]: core.data_uri("buffs", b["i"]) for b in buffs if b.get("i")}
    return {"B": buffs, "T": out, "I": {k: v for k, v in icons.items() if v}, "BI": {k: v for k, v in buff_icons.items() if v}}


def write_place_js():
    """place.js for the current language; returns its cache-busting version."""
    js = "var PLACE=" + json.dumps(place_data(), ensure_ascii=False, separators=(",", ":")) + ";"
    js = core.translate(js, html=False)
    core.OUT.mkdir(parents=True, exist_ok=True)
    (core.OUT / "place.js").write_text(js, encoding="utf-8")
    return hashlib.md5(js.encode()).hexdigest()[:8]
