"""Download tower portraits, upgrade icons and bloon icons from Blooncyclopedia (bloonswiki.com).

The artifact page cannot load images from other hosts, so build.py embeds these files.
Files already on disk are skipped; requests are spaced out to be polite to the wiki.

Usage: python3 -I tools/fetch_icons.py      (writes data/icons/raw/... and data/icons/manifest.json)
"""
import difflib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "icons" / "raw"
API = "https://www.bloonswiki.com/api.php"
UA = "btd6-tech-wiki/0.1 (personal static site build script)"
DELAY = 0.4
# wiki spelling of some tower ids
ALIASES = {"WizardMonkey": ["Wizard", "WIzard"], "Skywarden": ["SkyWarden"], "DartlingGunner": ["DartlingMonkey"],
           "Druid": ["DruidMonkey"]}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def list_images(prefix):
    """All wiki image names (with URLs) starting with prefix."""
    out, cont = {}, {}
    while True:
        q = {"action": "query", "list": "allimages", "aiprefix": prefix, "ailimit": "500",
             "aiprop": "url", "format": "json", **cont}
        d = json.loads(get(API + "?" + urllib.parse.urlencode(q)))
        for i in d["query"]["allimages"]:
            out[i["name"]] = i["url"]
        time.sleep(DELAY)
        if "continue" not in d:
            return out
        cont = {"aicontinue": d["continue"]["aicontinue"]}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    wanted = {}  # (kind, our id) -> url

    # bloons used in rounds; MOAB-class files carry an "Icon" suffix on the wiki
    bloon_ids = {g["bloon"] for f in (DATA / "Rounds").rglob("*.json") for g in load(f).get("groups") or []}
    bloon_files = list_images("BTD6_bloon_")
    for b in sorted(bloon_ids):
        for name in (f"BTD6_bloon_{b}.png", f"BTD6_bloon_{b}Icon.png", f"BTD6_bloon_{b.replace('Camo', '')}Icon.png"):
            if name in bloon_files:
                wanted[("bloons", b)] = bloon_files[name]
                break

    # buff indicator icons: the wiki keeps the game's icon name (BTD6_BuffIconAlchemist3xx.png)
    buff_files = list_images("BTD6_BuffIcon")
    for f in (DATA / "Buffs").glob("*.json"):
        name = load(f).get("iconName") or ""
        if f"BTD6_{name}.png" in buff_files:
            wanted[("buffs", name)] = buff_files[f"BTD6_{name}.png"]

    # tower portraits (base) and upgrade icons
    unmatched = {}
    en_text = load(DATA / "textTable.en.json") if (DATA / "textTable.en.json").exists() else {}
    portraits = list_images("BTD6_000-")
    for folder in sorted(p for p in (DATA / "Towers").iterdir() if p.is_dir()):
        tid = folder.name
        names = [tid] + ALIASES.get(tid, [])
        for n in names:
            if f"BTD6_000-{n}.png" in portraits:
                wanted[("towers", tid)] = portraits[f"BTD6_000-{n}.png"]
                break
        icons = {}
        for n in names:
            for name, url in list_images(f"BTD6_{n}_").items():
                m = re.match(rf"BTD6_{re.escape(n)}_(.+?)(?:UpgradeIcon)?\.(?:png|webp)$", name)
                if m:
                    icons[norm(m.group(1))] = url
        for i in range(3):
            key = "".join("5" if j == i else "0" for j in range(3))
            f = folder / f"{tid}-{key}.json"
            for tier, up in enumerate((load(f).get("appliedUpgrades") or []) if f.exists() else [], 1):
                code = "".join(str(tier) if j == i else "0" for j in range(3))
                plain = norm(up.split("-", 1)[-1]).removeprefix(norm(tid))  # "Alchemist Faster Throwing", "Buccaneer-Destroyer"
                close = difflib.get_close_matches(plain, list(icons), n=1, cutoff=0.8)  # data typos: "Bionc"
                hit = next((k for k in (norm(up), plain, code) if k in icons), close[0] if close else None)
                if hit:
                    wanted[("upgrades", up)] = icons[hit]
                else:
                    unmatched.setdefault(tid, []).append(up)
        # paragon: the data id is "<Tower> Paragon", the wiki file uses the English name ("Apex Plasma Master")
        pf = folder / f"{tid}-Paragon.json"
        if pf.exists():
            up = (load(pf).get("appliedUpgrades") or [""])[-1]
            hit = norm(en_text.get(up, ""))
            if hit in icons:
                wanted[("upgrades", up)] = icons[hit]
            else:
                unmatched.setdefault(tid, []).append(up)
        if tid in unmatched:
            unmatched[tid + " (wiki)"] = sorted(icons)

    # interface icons for mode modifiers and tower categories, by exact wiki file name
    ui = {"coin": "BTD6_CoinIcon.png", "lives": "BTD6_LivesIcon.png", "mm": "BTD6_ArtifactTokenMonkeyMoney.png",
          "nosell": "BTD6_SellingDisabledIcon.png", "knowledge": "BTD6_KnowledgeIcon.png", "speed": "BTD6_FastForwardBtn.png",
          "Primary": "BTD6_PrimaryBtn.png", "Military": "BTD6_MilitaryBtn.png", "Magic": "BTD6_MagicBtn.png",
          "Support": "BTD6_SupportBtn.png",
          "startcash": "BTD6_StartingCash.png", "startround": "BTD6_StartRoundIcon.png", "endround": "BTD6_EndRoundIcon.png",
          "nocontinue": "BTD6_NoContinuesIcon.png", "roundset": "BTD6_CustomRoundIcon.png",
          # mode buttons (find more names with tools/find_images.py)
          "mode-Easy": "BTD6_ModeSelectEasyBtn.png", "mode-Medium": "BTD6_ModeSelectMediumBtn.png",
          "mode-Hard": "BTD6_ModeSelectHardBtn.png", "mode-Impoppable": "BTD6_ImpoppableBtn.png",
          "mode-Clicks": "BTD6_ClicksBtn.png", "mode-AlternateBloonsRounds": "BTD6_AlternateBloonsBtn.png",
          "mode-Apopalypse": "BTD6_ApopalypseBtn.png", "mode-Deflation": "BTD6_DeflationBtn.png",
          "mode-HalfCash": "BTD6_HalfMoneyBtn.png", "mode-Reverse": "BTD6_ReverseBtn.png",
          "mode-DoubleMoabHealth": "BTD6_DoubleHpMoabsBtn.png", "mode-Sandbox": "BTD6_SandboxBtn.png",
          "paragon": "BTD6_tutorial_ParagonIcon.png", "powers": "BTD6_PowersIcon.png",
          **{f"boss-{b}": f"BTD6_{b}Btn.png" for b in
             ("Bloonarius", "Lych", "Vortex", "Dreadbloon", "Phayze", "Blastapopoulos", "Diamondback")},
          # powers: id in data/Powers -> wiki file
          **{f"power-{p}": f"BTD6_{f}.png" for p, f in {
              "BananaFarmer": "BananaFarmerIcon", "BananaFarmerProPower": "BananaFarmerProIcon", "BattleCat": "BattleCatIcon",
              "CamoTrap": "CamoTrapIcon", "CashDrop": "CashDropIcon", "CaveMonkey": "CaveMonkeyIcon", "DartTime": "DartTimeIcon",
              "EnergisingTotem": "EnergisingTotemIcon", "GlueTrap": "GlueTrapIcon", "HealthPotion": "HealthPotionStoreIcon",
              "MoabMine": "MoabMineIcon", "MonkeyBoost": "MonkeyBoostIcon", "MonkeyBoostProPower": "MonkeyBoostProIcon",
              "Pontoon": "PontoonIcon", "PortableLake": "PortableLakeIcon", "PortableLakeProPower": "PortableLakeProIcon",
              "SheRa": "SheRaPowerIcon", "Skeletor": "SkeletorPowerIcon", "StaminaPotion": "StaminaPotionStoreIcon",
              "SuperMonkeyBeaconPower": "SuperMonkeyBeaconIcon", "SuperMonkeyStorm": "SuperMonkeyStormIcon",
              "SwordOfPower": "SwordOfPowerIcon", "TechBot": "TechbotIcon", "TechBotPrimePower": "TechbotProIcon",
              "Thrive": "ThriveIcon"}.items()}}
    names, urls = list(ui.values()), {}
    for i in range(0, len(names), 50):  # the API takes at most 50 titles per request
        q = {"action": "query", "prop": "imageinfo", "iiprop": "url", "format": "json",
             "titles": "|".join("File:" + n for n in names[i:i + 50])}
        for p in json.loads(get(API + "?" + urllib.parse.urlencode(q)))["query"]["pages"].values():
            if "imageinfo" in p:
                urls[p["title"].removeprefix("File:").replace(" ", "_")] = p["imageinfo"][0]["url"]
        time.sleep(DELAY)
    for key, name in ui.items():
        if name in urls:
            wanted[("ui", key)] = urls[name]

    manifest = {}
    for (kind, oid), url in sorted(wanted.items()):
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", oid)
        path = RAW / kind / f"{safe}.png"
        manifest.setdefault(kind, {})[oid] = f"{kind}/{safe}"
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(url))
        time.sleep(DELAY)
    (DATA / "icons" / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    missing_b = sorted(bloon_ids - set(manifest.get("bloons", {})))
    print({k: len(v) for k, v in manifest.items()}, "bloons without icon:", missing_b)
    (DATA / "icons" / "unmatched.json").write_text(json.dumps(unmatched, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
