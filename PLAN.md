# Plan

From the site audit of 2026-11-05. Done items move to the git history.

## 1. Search engines
- [ ] `robots.txt` and `sitemap.xml` in the site (every page, both languages).
- [ ] `<head>`: `description`, `canonical`, `hreflang` pairs RU/EN plus `x-default`, `og:` tags, favicon.
- [ ] Drop the stray `claude:viewport-fit-sides` meta tag.
- [ ] Owner: verify the domain in Google Search Console and submit the sitemap. The domain root `robots.txt`
      comes from the `antonzlo.github.io` repo and lists only that repo's sitemap.

## 2. Page weight
- [ ] Icons as files (`site/icons/<kind>/<id>.webp`) instead of inline base64: one download, cached across pages.
      Before: site 88 MB, gzip per page up to 2.5 MB (rounds), 2.1 MB (bloons, achievements), 1.3 MB (knowledge).

## 3. New sections from the Mod Helper export (data not used yet)
- [ ] Maps (`Maps/`, 91): difficulty, water, co-op split, unlock.
- [ ] Geraldo shop (`GeraldoItems/`, 16): cost, unlock level, restock.
- [ ] Achievements from the export (`Achievements/`, same data as the dumper, rewards included); the dumper then
      only adds icons.
- [ ] Skins (`Skins/`, 52), Trophy Store (`TrophyStoreItems/`, 439).
- [ ] Legends: Rogue and Frontier (`Artifacts/` 573, `rogueData.json`, `frontierData.json`).

## Small
- [ ] Google Fonts is an external request; self-host or system fonts.
