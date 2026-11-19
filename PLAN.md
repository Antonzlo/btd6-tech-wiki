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
multiplier by spawn round). Bank, IMF Loan payout and repayment, tower sale and Double Cash since 2026-11-17.
XP page (`xp.html`) since 2026-11-17: round XP, freeplay, BossRush x0.2 and Rogue x3.0, co-op split, no-XP gates,
account ranks from `rank-xp.json`.

Open in the notes themselves (needs more reading of the code or a test in game):
- [ ] A dropped connection before the player is formally removed.
- [ ] The ordinary pop cash for a bloon caught by the trap.
- [ ] Who gets the extra dollar when starting cash does not divide evenly.
- [ ] Which players' knowledge the co-op lobby applies (tower XP bonuses).
- [ ] `selectedDifficultyRating` values (multiplies round XP, not in the dump).
- [ ] Cash path of the sources shown as "not checked": `GiveCashOnPop`, cash zones, `CashModel` without a
      `PickupModel`.

## 3. In `data/` already, not shown

## 4. In the Mod Helper export, not copied into `data/` yet
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
- [ ] Odyssey, Race, Contested Territory and boss events as modes.
- [ ] Insta monkey and collection event chances.

## 6. Legends, later
- [ ] Rogue Legends: `Artifacts/` (573), `rogueData.json` (rarity chances, XP per tile, shop, starter kits, CHIMPS
      rules, bloon modifiers), 7 Rogue round sets, `RogueIncomeSet`.
- [ ] Frontier: `frontierData.json` (stamina, saloon, traits, loot, chests, fishing, difficulties, encounters,
      feats), 7 Frontier round sets.

## 7. Design: less of a generated look
From screenshots of the home, tower and co-op pages on 2026-11-16. The game HUD idea (ink outline, hard shadow,
gold titles) is the site's own and stays. What reads as a template is that one treatment sits on everything.
- [ ] Check badges (`.badge`) and other non-pressable bordered elements: outline and hard shadow only on things you press.
      Content cards are quiet panels already.
- [ ] Pastel pill chips and the two-part badges with a monospace label: keep colour only where it encodes
      something (cannot pop, stackable, link kind), plain text elsewhere. Monospace only for real ids.
