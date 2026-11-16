# Plan

From the site audit of 2026-11-05 and the gap list of 2026-11-16. Done items move to the git history.
Order: what the data already has (sections 2 to 4), then what needs the dumper (5), Legends last (6).

## 1. Search engines (owner)
- [ ] Verify the domain in Google Search Console and submit https://zlobinanton.ovh/btd6-tech-wiki/sitemap.xml.
- [ ] The domain root `robots.txt` comes from the `antonzlo.github.io` repo: its `Sitemap:` line points at
      `http://antonzlo.github.io/sitemap.xml`. Add `Sitemap: https://zlobinanton.ovh/btd6-tech-wiki/sitemap.xml` there
      (a `robots.txt` inside /btd6-tech-wiki/ is ignored by crawlers).

## 2. Game code findings not on the wiki yet (`../coop-xp-evidence.md`, GameAssembly.dll 57.4)
Checked against the dump on 2026-11-16: starting cash bases, round bonus, mode end rounds and the round XP formula
(`data/KnowledgeLayout/xp.json`) all match. The native addresses were not re-checked.

Co-op cash: on the wiki since 2026-11-16 (picked-up cash to the tower's owner, Bloon Trap, a player leaving, income
multiplier by spawn round).

XP (new page, only hero XP is on the wiki now):
- [ ] Round XP: `20*(r+2+max(0,r-19)) + 50*max(0,r-49)` with `r = round - 1`, times the map difficulty scale
      (both already in `xp.json`).
- [ ] Freeplay: x0.30 after the mode's last round, x0.10 after round 100 with a cap of 3000.
- [ ] Sub-game scales: Rush x0.2, BossBloonChallenge x3.0 (names from the enum, not checked in game).
- [ ] Account XP in co-op: every player gets the full round XP, no division by the player count.
- [ ] Tower XP: round XP times the tower's share of the team's spending on non-hero towers, then the tower's own
      XP bonuses. Free and insta towers add no weight. Fractions are kept, not rounded.
- [ ] Knowledge XP bonuses multiply: Monkey Education 1.08 x Elite Military Training 1.05 = 1.134.

Open in the notes themselves (needs more reading of the code or a test in game):
- [ ] A dropped connection before the player is formally removed.
- [ ] The ordinary pop cash for a bloon caught by the trap.
- [ ] The doubling branch in `AddSharedCash` (double cash).
- [ ] Who gets the extra dollar when starting cash does not divide evenly.
- [ ] Challenge types that give no XP (candidate names only).
- [ ] Cash path of the sources shown as "not checked": bank, IMF loan, `GiveCashOnPop`, cash zones,
      `CashModel` without a `PickupModel`.

## 3. In `data/` already, not shown
- [ ] `xpCost` of tower upgrades (`data/Upgrades/`): only the hero pages read it.

## 4. In the Mod Helper export, not copied into `data/` yet
- [ ] Round sets (`Rounds/`, 47, the wiki has 2): Accelerated, Endurance, MOABMadness, FastUpgrades, MasteryMode,
      DefaultSkipEveryOddRound, then the 16 hero trial sets and the quest sets (BattleCat, BouncyDarts, HeMan,
      Scoops, Skeletor, Mermonkey). One page per set or the rounds page gets too heavy.
- [ ] Achievements from the export (`Achievements/`, same data as the dumper, rewards included); the dumper then
      only adds icons.
- [ ] Skins (`Skins/`, 18 heroes), Trophy Store (`TrophyStoreItems/`: Bloons, Coop, GameUI, Heroes, Monkeys).
- [ ] Bloon status overlays (`BloonOverlays/`, 59): mostly visuals, low value.
- [ ] Map editor content (`MapEditor_ContentData/`, 17 entries): look at what it holds first.
- Sub-towers (Sentry, Phoenix, Marine, UAV, pets, totems) need no copy: they sit inside the tower models and
  `combat_stats` already reads them. `resources.json` is a GUID to prefab path table, not needed.

## 5. Not in the export: needs the dumper or the game code
Checked only by the absence of any mention in `wiki/`.
- [ ] Freeplay rules: bloon HP and speed growth by round.
- [ ] Account level and veteran level XP tables.
- [ ] Odyssey, Race, Contested Territory and boss events as modes.
- [ ] Insta monkey and collection event chances.
- [ ] Standard starting cash 650 is hardcoded in `wiki/heroes.py` (`START_CASH`).
- [ ] Which difficulty each mode is played on (`MODE_BASE` in `wiki/modes.py` is written by hand).

## 6. Legends, later
- [ ] Rogue Legends: `Artifacts/` (573), `rogueData.json` (rarity chances, XP per tile, shop, starter kits, CHIMPS
      rules, bloon modifiers), 7 Rogue round sets, `RogueIncomeSet`.
- [ ] Frontier: `frontierData.json` (stamina, saloon, traits, loot, chests, fishing, difficulties, encounters,
      feats), 7 Frontier round sets.

## 7. Design: less of a generated look
From screenshots of the home, tower and co-op pages on 2026-11-16. The game HUD idea (ink outline, hard shadow,
gold titles) is the site's own and stays. What reads as a template is that one treatment sits on everything.
- [ ] Outline and hard shadow only on things you press (tiles, buttons, search), like buttons in the game. Content
      cards become quiet panels: no shadow, thin rule or none. Now every card, tile, button, badge and input has
      the same 2 to 3px border and drop shadow.
- [ ] Home page: 15 identical tiles in two wide columns. Group them the way `PAGES` already orders them (your
      side, the enemy, match rules, account extras) with a heading per group, and make the tiles narrower.
- [ ] Stat pills (big number over a small label) on tower, hero and bloon cards: replace with one compact row of
      "label value" pairs.
- [ ] Game text boxes (`.game`): a tinted, bordered, rounded box around every description, also inside table rows
      (knowledge tables). Plain text, or a left rule where it must stand apart from wiki text.
- [ ] Pastel pill chips and the two-part badges with a monospace label: keep colour only where it encodes
      something (cannot pop, stackable, link kind), plain text elsewhere. Monospace only for real ids.
- [ ] Tables stretch to the full 1760px card (co-op rules: three columns far apart). Size tables to their content.
- [ ] Footer: drop "Сделано с ♥".
- [ ] Fonts: Rubik for both titles and text, loaded from Google Fonts. Self-host Rubik for titles, system font for
      text (also closes the external request).
