# Game coverage map

What BTD6 has, where each fact can come from, and what the wiki shows. Game version 57.4, written 2026-11-19.
Read this before starting work on a new topic. If a row says the value is not in any local source, do not search
the decomp for it again: write the dumper call or plan an in-game test instead.

## 1. Sources, and what each one can and cannot give

| Source | Where | Gives | Does not give |
| --- | --- | --- | --- |
| **Export** (Mod Helper "Export Game Data") | `<prefix>/AppData/LocalLow/Ninja Kiwi/BloonsTD6/`, part copied to `data/` | Serialized models: every field value of towers, upgrades, heroes, bloons, bosses, rounds, mods, buffs, knowledge, powers, maps, income sets, Rogue, Frontier, achievements, skins, trophy store | Anything computed in code, static class fields, server data, profile data |
| **Dumper** (`../btd6-knowledge-dumper`, `KnowledgeLayout/*.json`) | Runs inside the game, calls game functions and reads static fields | Values the code computes or keeps in statics: knowledge tree layout, shop order, property bits, hero XP per round, map XP scales, rank XP table, map geometry, achievements with rewards, freeplay scaling (written, not run yet) | Logic itself, only the values of the calls we chose to make |
| **Decomp** (`../btd6-decomp/Assembly-CSharp.decompiled.cs`, 128 MB) | Il2CppInterop proxy assembly | Class, field and method **names and signatures** (13k classes). Tells which function or static to call from the dumper | **No method bodies and no values.** Every method is a `NativeMethodInfoPtr` stub. A number is never found here |
| **Native** (`GameAssembly.dll` via `objdump`) | Game folder | The real logic: formulas, branches, who gets the cash. Used for `../coop-xp-evidence.md` | Slow to read. Constants inside code are found, constants in data tables are not |
| **Test in game** | Sandbox or a real match | Confirms behaviour, co-op splits, timing | Repeatability: record the setup and the result |
| **Server** | Ninja Kiwi backend | Daily and advanced challenges, Odyssey and boss event schedules, races, Contested Territory, trophy store rotation, sale prices | Nothing offline. Out of scope unless captured live |

Rule of thumb: export for numbers in models, dumper for numbers in code statics or function results, native for the
formula, game test for confirmation. The decomp only names the thing to call.

## 2. Status codes

- **WIKI**: shown on the site, built from `data/`.
- **DATA**: in `data/`, not shown yet.
- **EXPORT**: in the export folder, not copied into `data/`.
- **DUMPER**: needs a dumper call. "written" means the code exists and was not run.
- **NATIVE**: only in native code. Read with objdump, or call the function from the dumper.
- **TEST**: needs an in-game check.
- **SERVER**: not in any local file.
- **HAND**: on the wiki, but the value is written by hand in `wiki/*.py`. Should move to a dump.

## 3. Coverage by area

### Your side

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Towers | 26 main towers, 3 paths, 5 tiers, crosspaths | Export `Towers/` (26 main of 97 folders), `Upgrades/` (794) | WIKI | `tower-*.html`. Sub-towers (Sentry, Phoenix, Marine, UAV, pets, totems) live inside the tower models and are read by `combat_stats` |
| Tower prices by difficulty | Price multiplier per difficulty | Export `Mods/` | WIKI | |
| Tower XP to unlock upgrades | XP cost per upgrade | Export `Upgrades/` (`xpCost`) | WIKI | `tower-*.html#upgrades` shows the XP cost for each tier and each Paragon with an exported tower model |
| Paragons | Paragon upgrades (15 files in `Upgrades/`), degrees 1 to 100, power from pops, cash, upgrades, totems | Export paragon tiers in `Towers/`, `paragonDegreeData.json` | WIKI | `paragon.html`. Paragon XP weight of sacrificed worth: NATIVE, open in the evidence notes |
| Heroes | 18 heroes, levels 1 to 20 | Export `Towers/<Hero>` copied to `data/Heroes/` | WIKI | Hero XP per round from dumper `xp.json` |
| Hero skins | Skins per hero, some with changed stats or visuals only | Export `Skins/` (18 heroes) | EXPORT | PLAN section 4 |
| Geraldo shop items | 19 items | Export `GeraldoItems/` | WIKI | On the Geraldo hero page |
| Corvus spells | Spellbook | Export, inside Corvus models | WIKI | Through the hero page. Not checked in detail |
| Buffs and stacking | Village, Alchemist, hero and knowledge buffs | Export `Buffs/` (102) | WIKI | `buffs.html` |
| Monkey Knowledge | 6 trees, prices, effects | Export `Knowledge/`, dumper `layout.json` | WIKI | Which players' knowledge applies in co-op: NATIVE, open |
| Powers | 28 powers incl. Pro powers and event powers | Export `Powers/` | WIKI | `powers.html` |
| Insta Monkeys | Placed as fixed-tier towers | Tower models are the same as normal towers | WIKI (indirect) | Drop chances and sources: SERVER or NATIVE, not found |
| Starting cash | 650 standard | Export `Mods/` Easy, Medium, Hard, `StartingCashModModel.changeBase` | WIKI | `START_CASH` in `wiki/heroes.py` reads `Medium.json` |

### The enemy

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Bloons | Red to BAD, properties, children, fortified, camo, regrow | Export `Bloons/` (55), dumper property bits in `game.json` | WIKI | `bloons.html` |
| Bloon status overlays | Visual effects | Export `BloonOverlays/` (59) | EXPORT | Low value |
| Rounds | Default, ABR, mode sets, quest sets | Export `Rounds/` | WIKI | `rounds.html` and `rounds-*.html` |
| Rogue and Frontier round sets | 7 Rogue, 7 Frontier | Export `Rounds/Rogue*`, `Frontier*` | WIKI | `rounds.html` links all 14 sets. Each shows its wave composition, base RBE and timing. Per-encounter cash and round bonuses still need verification |
| Freeplay scaling | HP and speed growth after round 80, stun resistance, super ceramics | `ProgressiveDifficultyManager` statics and `GetHealthMultiplier` / `GetSpeedMultiplier` / `GetStunResistance` | DATA | The 57.4 dump is in `data/KnowledgeLayout/freeplay.json` and covers rounds 1 to 1000. Wiki presentation is pending |
| Bosses | 7 bosses, 5 tiers plus Elite | Export `Bosses/` and bloon models | WIKI | `bosses.html` |
| Boss events as a mode | Rules, tier timing, leaderboard | SERVER for schedules, rules in export Mods for some | SERVER | |

### Match rules

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Difficulties and modes | Easy to Impoppable, CHIMPS, Deflation, Apopalypse, Reverse, Half Cash, Double HP MOABs, Alternate Bloons, Primary, Military, Magic only, Sandbox | Export `Mods/` (25) | WIKI | `modes.html`. Which base difficulty each mode uses: dumper `game.json` `modeDifficulty`, from `ModeScreen.easyModes/mediumModes/hardModes` |
| Mode end rounds | 40, 60, 80, 100 | Export Mods | WIKI | |
| Income | Pop cash multiplier by round, end-of-round bonus | Export `IncomeSets/` | WIKI | `income.html` includes multiplier tables for Rogue, Frontier and Frontier Reduced. The standard-wave income charts cover the other sets |
| Farm and bank income, Double Cash, IMF | | Export tower models, native for payouts | WIKI | Since 2026-11-17 |
| Co-op cash | Starting cash per player, pop cash split, transfers | Export `Mods/Coop*`, native | WIKI | `coop.html`. Open items in PLAN section 2: dropped connection, trap pop cash, uneven starting cash remainder, `GiveCashOnPop`, cash zones |
| Account XP and tower XP | Round XP formula, map scale, co-op split | Dumper `xp.json`, `rank-xp.json`, native | WIKI | `xp.html`. `selectedDifficultyRating` values: DUMPER (field known, values not dumped) |
| Monkey Money rewards | Per map difficulty and mode | Not found | NATIVE or SERVER | Not checked |

### Maps

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Maps | 88 maps in `maps.json`, 4 difficulties | Export `Maps/`, dumper `maps.json`, `maps_geo.json` | WIKI | Paths, areas, obstacles, events, placement check |
| Map editor content | Props and templates | Export `MapEditor_ContentData/` (17) | EXPORT | Look at it first, unknown value |
| Browser-only maps | Community maps | SERVER | SERVER | Skipped by the dumper |

### Account and meta

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Achievements | Goals, rewards, hidden ones | Dumper `achievements.json`, export `Achievements/` (165) | WIKI | Export holds the same data |
| Account ranks | XP per rank, veteran ranks | Dumper `rank-xp.json` | WIKI | |
| Trophy Store | Cosmetics: bloons, co-op, UI, heroes, monkeys | Export `TrophyStoreItems/` | EXPORT | Rotation and prices on sale: SERVER |
| Quests and hero trials | Quest round sets | Export rounds | WIKI (rounds only) | Quest rules and rewards: not checked |
| Collection event | Crate chances | Not found | NATIVE or SERVER | `Unity.CollectionEvent` classes exist in the decomp, names only |
| Odyssey, Race, Contested Territory, daily challenges | Event modes | SERVER, classes in decomp | SERVER | Not reachable offline. Skip unless captured live |
| Monkey Teams, social seasons, season perks, feats, badges, accolades, emotes, avatars | Profile and social | Decomp names only | SERVER or not checked | Low value for a numbers wiki |

### Legends

| Area | In the game | Source | Status | Notes |
| --- | --- | --- | --- | --- |
| Rogue Legends | Artifacts, tiles, shop, starter kits, CHIMPS rules, bloon modifiers | Export `Artifacts/` (573), `rogueData.json` | EXPORT | Wave sets and pop-cash multipliers are covered in the rows above |
| Frontier Legends | Stamina, saloon, traits, loot, chests, fishing, encounters, feats | Export `frontierData.json` (2.9 MB) | EXPORT | Wave sets and pop-cash multipliers are covered in the rows above |

## 4. Not reachable offline at all

- Event schedules and rewards: Odyssey, boss events, races, Contested Territory, daily and advanced challenges.
- Trophy store rotation and sale prices, store prices.
- Insta Monkey and collection crate drop chances, unless a static table turns up in native code.
- Browser and community maps.

These need a live capture (the dumper reading the downloaded event model in a running game) or are out of scope.

## 5. Open checks from the native analysis

Kept in `../coop-xp-evidence.md` and PLAN section 2. All are TEST or NATIVE:

- Ordinary pop cash for a bloon caught by an Engineer trap.
- Staged cash recovery when its tower is destroyed before the flush.
- Sacrificed worth into Paragon XP weight.
- Profile XP after a reconnect, AWOL timer settings.
- Who gets the extra dollar when starting cash does not divide evenly.

## 6. Rules for agents, to stop going in circles

1. Looking for a number? Check the export first (`grep -r` the field name in the export folder, not only `data/`).
2. Not in the export? Find the class in the decomp to learn the **name** of the static field or function. Stop
   there. Do not read further for a value: there is none.
3. Write a dumper call that reads that static or calls that function, run it once, copy the JSON to
   `data/KnowledgeLayout/`. Values come from the game, never from memory or a fan wiki.
4. Need the formula, not just the values? Read native code with objdump and record the finding with its address in
   the evidence notes. One function at a time.
5. Behaviour still unclear after that? Write a TEST item with the exact setup, and leave it for the owner.
6. Anything marked SERVER: do not try. Say it is server data.
7. When a row in this file changes status, update the row in the same commit.
