"""Build the BTD6 tech wiki (static HTML) from a Mod Helper "Export Game Data" dump.

Usage: python3 -I build.py            (reads ./data, writes ./site)
Refresh data: copy Bosses Bloons Mods IncomeSets Buffs Knowledge Powers
paragonDegreeData.json textTable.json from the export folder into ./data
and the KnowledgeLayout folder written by btd6-knowledge-dumper (F6 in game, gives game.json too).
Code: wiki/core.py holds shared helpers and state, one wiki/<section>.py module per group of pages.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python3 -I leaves the script folder off sys.path

from wiki import core  # noqa: E402
from wiki.core import INDEX, LANGS, SEARCH_JS, SITE, set_lang, translate
from wiki.paragon import build_bosses, build_paragon
from wiki.modes import build_income, build_modes
from wiki.buffs import build_buffs
from wiki.knowledge import build_knowledge, build_powers
from wiki.achievements import build_achievements
from wiki.heroes import build_heroes
from wiki.links import build_index, build_links
from wiki.towers import build_towers
from wiki.bloons import build_bloons, build_rounds


def main():
    shutil.rmtree(SITE, ignore_errors=True)  # no stale pages from an older layout
    for lang in LANGS:
        set_lang(lang)
        INDEX.clear()
        for file, build in (("paragon.html", build_paragon), ("bosses.html", build_bosses), ("modes.html", build_modes),
                            ("income.html", build_income), ("buffs.html", build_buffs),
                            ("knowledge.html", build_knowledge), ("powers.html", build_powers), ("achievements.html", build_achievements),
                            ("towers.html", build_towers), ("heroes.html", build_heroes), ("bloons.html", build_bloons),
                            ("rounds.html", build_rounds),
                            ("links.html", build_links), ("index.html", build_index)):
            core.current_file = file
            build()
        INDEX[:] = list({(e[0], e[2]): e for e in INDEX if e[0]}.values())  # same title and link once
        (core.OUT / "search.js").write_text(
            translate("var WIKI_INDEX=" + json.dumps(INDEX, ensure_ascii=False) + ";" + SEARCH_JS), encoding="utf-8")
        left = sorted(set(re.findall(r"[А-Яа-яЁё][А-Яа-яЁё .,:()/-]*", "".join(
            f.read_text(encoding="utf-8") for f in core.OUT.glob("*.html"))))) if lang != "ru" else []
        print(f"{lang}: {len(INDEX)} search entries into {core.OUT}"
              + (f", untranslated: {left[:15]}" if left else ""), file=sys.stderr)
    # every page in every language; submit https://zlobinanton.ovh/btd6-tech-wiki/sitemap.xml in Search Console
    urls = "".join(f"<url><loc>{core.page_url(lang, f.name)}</loc></url>"
                   for lang in LANGS for f in sorted(SITE.glob("*.html")))
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>'
                                      f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                                      encoding="utf-8")


if __name__ == "__main__":
    main()
