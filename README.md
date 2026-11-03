# BTD6 Tech Wiki

A static wiki of exact Bloons TD 6 numbers taken from the game's own models: bosses by tier, modes,
income, buff stacking, paragon, Monkey Knowledge, powers, towers with crosspaths, and rounds. Russian and
English.

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
3. For English game text, switch the game to English, export again, and copy `textTable.json` to
   `data/textTable.en.json`.
4. Monkey Knowledge layout: with the `KnowledgeDumper` mod (`../btd6-knowledge-dumper`) open the Monkey
   Knowledge screen and press F6, then copy `<game>/KnowledgeLayout/` into `data/KnowledgeLayout/`
   (icons converted to 96px webp). F6 also writes `game.json`: game version, shop order of towers and
   bloon property bits. Without it the build falls back to `data/VERSION.txt` and a built-in tower order.
5. Icons for towers, upgrades and bloons: `python3 -I tools/fetch_icons.py`, then convert
   `data/icons/raw/*` to webp in `data/icons/web/` (see the script header).

## Files

- `build.py` the generator, `style.css` the styles, `i18n_en.json` English phrases for the interface.
- `data/` the game export the site is built from.

Game data, names, descriptions and images belong to Ninja Kiwi. Icons come from
[Blooncyclopedia](https://www.bloonswiki.com) (CC BY-NC-SA).
