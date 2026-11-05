# BTD6 Tech Wiki

A static wiki of exact Bloons TD 6 numbers taken from the game's own models: bosses by tier, modes,
income, buff stacking, paragon, Monkey Knowledge, powers, towers with crosspaths, and rounds.
English (`/`) and Russian (`/ru/`).

Live: https://zlobinanton.ovh/btd6-tech-wiki/ (GitHub Pages, deployed by `.github/workflows/pages.yml` on every push to `main`).

Python standard library only, no dependencies.

## Build

```sh
python3 -I build.py          # writes site/ (Russian) and site/en/
```

## Refresh after a game patch

1. In game, Mod Helper settings, press **Export Game Data**. The export lands in
   `<Proton prefix>/drive_c/users/steamuser/AppData/LocalLow/Ninja Kiwi/BloonsTD6/`.
2. Copy `Bosses Bloons Mods IncomeSets Buffs Knowledge Powers Upgrades paragonDegreeData.json textTable.json`,
   the 26 main tower folders from `Towers/`, and `Rounds/DefaultRoundSet`, `Rounds/AlternateRoundSet` into `data/`.
   For each hero (towerSet 16 with 20 levels) copy `<Hero>.json` and `<Hero> 2.json` … `<Hero> 20.json` into `data/Heroes/<Hero>/`.
3. For English game text, switch the game to English, export again, and copy `textTable.json` to
   `data/textTable.en.json`.
4. Monkey Knowledge layout: with the `KnowledgeDumper` mod (`../btd6-knowledge-dumper`) open the Monkey
   Knowledge screen and press F6, then copy `<game>/KnowledgeLayout/` into `data/KnowledgeLayout/`
   (icons converted to 96px webp). F6 also writes `game.json`: game version, shop order of towers and
   bloon property bits (required). Keep `data/VERSION.txt` at the export version; the build warns when the game is newer.
5. Icons: press F7 in game with the dumper (main menu, mode select, inside a game: each screen adds the sprites
   it has loaded), then `sh tools/game_icons.sh` writes `data/icons/web/`. UI icon names are in `tools/ui_sprites.txt`.
   `sh tools/compose_icons.sh` makes the ban icons.

## Files

- `build.py` the entry point, `wiki/` the generator (`core.py` shared helpers, one module per page group), `site.js` the client script, `style.css` the styles, `i18n_en.json` English phrases for the interface.
- `data/` the game export the site is built from.

Game data, names, descriptions and images (icons are the game sprites) belong to Ninja Kiwi.
