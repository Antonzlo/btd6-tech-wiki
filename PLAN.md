# Plan

From the site audit of 2026-11-05. Done items move to the git history.

## 1. Search engines (owner)
- [ ] Verify the domain in Google Search Console and submit https://zlobinanton.ovh/btd6-tech-wiki/sitemap.xml.
- [ ] The domain root `robots.txt` comes from the `antonzlo.github.io` repo: its `Sitemap:` line points at
      `http://antonzlo.github.io/sitemap.xml`. Add `Sitemap: https://zlobinanton.ovh/btd6-tech-wiki/sitemap.xml` there
      (a `robots.txt` inside /btd6-tech-wiki/ is ignored by crawlers).

## 3. New sections from the Mod Helper export (data not used yet)
- [ ] Achievements from the export (`Achievements/`, same data as the dumper, rewards included); the dumper then
      only adds icons.
- [ ] Skins (`Skins/`, 52), Trophy Store (`TrophyStoreItems/`, 439).
- [ ] Legends: Rogue and Frontier (`Artifacts/` 573, `rogueData.json`, `frontierData.json`).

## Small
- [ ] Google Fonts is an external request; self-host or system fonts.
