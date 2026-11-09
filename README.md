# BTD6 Tech Wiki

A static wiki of exact Bloons TD 6 numbers taken from the game's own models: towers with crosspaths, heroes,
paragon, bosses by tier, bloons, rounds, modes, income, buff stacking, Monkey Knowledge, powers, achievements,
and maps, each map with a layout of its paths, areas, obstacles and map events. English (`/`) and Russian (`/ru/`).

Live: https://zlobinanton.ovh/btd6-tech-wiki/ (GitHub Pages, deployed by `.github/workflows/pages.yml` on every push to `main`).

Python standard library only, no dependencies.

## Build

```sh
python3 -I build.py --pages  # writes site/ (English) and site/ru/, icons as files: what GitHub Pages serves
python3 -I build.py          # the same with icons inline, for the single-file artifact
python3 -I dev.py            # preview at http://127.0.0.1:8765/, rebuilds with --pages on changes (settings at the top of dev.py)
```

## Refresh after a game patch

1. In game, Mod Helper settings, press **Export Game Data**. The export lands in
   `<Proton prefix>/drive_c/users/steamuser/AppData/LocalLow/Ninja Kiwi/BloonsTD6/`.
2. Copy `Bosses Bloons Mods IncomeSets Buffs Knowledge Powers Upgrades Maps GeraldoItems paragonDegreeData.json textTable.json`,
   the 26 main tower folders from `Towers/`, and `Rounds/DefaultRoundSet`, `Rounds/AlternateRoundSet` into `data/`.
   For each hero (towerSet 16 with 20 levels) copy `<Hero>.json` and `<Hero> 2.json` … `<Hero> 20.json` into `data/Heroes/<Hero>/`.
3. For English game text, switch the game to English, export again, and copy `textTable.json` to
   `data/textTable.en.json`.
4. Game facts the export lacks, with the `KnowledgeDumper` mod (`../btd6-knowledge-dumper`): in the main menu press
   Ctrl+Shift+F6. It opens the Monkey Knowledge tree, the hero screen and a sandbox match, and writes
   `layout.json` (knowledge tree), `game.json` (game version, shop order of towers and heroes, bloon property and
   tower set bits), `achievements.json` (goals and rewards) and `xp.json` (hero XP per round and map difficulty XP
   scales, from the game's own functions). Copy `<game>/KnowledgeLayout/` into `data/KnowledgeLayout/` (icons
   converted to 96px webp). Ctrl+Shift+F7 prints the current menu and its data. Keep `data/VERSION.txt` at the export
   version; the build warns when the game is newer.
5. Maps, with the same mod: Ctrl+Shift+F9 in the main menu loads every map in a sandbox match (browser-only maps
   are skipped) and writes `maps.json` (path lengths, obstacle costs, map behaviours) and `maps_geo.json` (path
   points, areas, line of sight blockers, obstacles, the spawner with its splitters, map events with their settings,
   click targets). It skips maps already in both files, so a stopped run continues where it left off; delete
   `maps_geo.json` to dump everything again. Pressing the keys again stops after the current map. Plain F9 inside a
   match dumps only that map, with the towers standing on it: the map page draws them and checks each against its
   placement rule (pink: the game placed it, the rule would not). Copy both files into `data/KnowledgeLayout/`. The map pages build without them and
   show "–" for what is missing.
6. Icons: press F7 in game with the dumper (main menu, mode select, inside a game: each screen adds the sprites
   it has loaded), then `sh tools/game_icons.sh` writes `data/icons/web/`. UI icon names are in `tools/ui_sprites.txt`.
   `sh tools/compose_icons.sh` makes the ban icons.
7. `sh tools/diff_build.sh` lists the pages that differ from the last commit's build. Commit and push: the
   workflow publishes the site.

## Files

- `build.py` the entry point, `wiki/` the generator (`core.py` shared helpers, one module per page group), `site.js` the client script, `style.css` the styles, `i18n_en.json` English phrases for the interface.
- `dev.py` the local preview server, `tools/` icon and build-diff scripts.
- `data/` the game export the site is built from.

Game data, names, descriptions and images (icons are the game sprites) belong to Ninja Kiwi.
