# ATL Events Intelligence Site — Agent Rules

**Project:** ATL Radar / ATL Events
**Live:** https://atlradar.vercel.app
**GitHub:** https://github.com/WhatWouldDimaDo/atl-events (public)
**Deploy:** `/opt/homebrew/bin/vercel --prod` from this directory

## Session Startup
```bash
grep -n "TODAY" data.js   # ALWAYS check — site hides past events if stale
# Fix if needed: const TODAY = new Date('YYYY-MM-DD');
```

## Bootstrap

1. **Read `HANDOFF.md`** in this directory first — it has the current state, data coverage, open items, and deploy history.
2. **Read `ENRICHMENT-METHODOLOGY.md`** before running any enrichment or data pipeline work.
3. **Read `VENUE-REFRESH-GUIDE.md`** before adding new events from venue calendars.

## Skills

| Skill | When to load |
|-------|-------------|
| `atl-events-builder` | Building/modifying the site, adding events, deploying, running pipeline scripts |
| `atl-events` | Event knowledge base — scoring, friends matrix, recurring events, memberships |
| `alice` | Social planning — "what should I do this weekend?", friend recommendations |
| `frontend-design` | UI/CSS work on the site |

## File Architecture

### Code (site root)
| File | Purpose |
|------|---------|
| `index.html` | HTML structure, links external files |
| `app.js` | Wizard logic, filters, calendar, Leaflet map, drawers, radar charts, bottom sheet |
| `style.css` | All CSS, mobile-first responsive |
| `data.js` | EVENTS array + EVERGREEN array (the data layer) |
| `about.html` | About page |
| `vercel.json` | Static site config, security headers, cache control |

### Scripts (`scripts/`)
| Script | Purpose | Usage |
|--------|---------|-------|
| `export_events.py` | Export EVENTS array from data.js to JSON | `python3 scripts/export_events.py` |
| `enrich_events.py` | Fill ticket URLs and images for events | `--audit` (find gaps), `--fetch` (fill gaps), `--apply` (patch data.js) |
| `expand_concerts.py` | Mine Master CSV + batch JSONs for new concert candidates | `python3 scripts/expand_concerts.py` |
| `social_scan.py` | Weekly social momentum brief — inner circles, slot matching, group text drafts | `python3 scripts/social_scan.py` |
| `fetch_images.py` | Download event images (stdlib only, no pip) | `python3 scripts/fetch_images.py` |
| `fetch_evergreen_images.py` | og:image + venue logo downloader for evergreen entries | `python3 scripts/fetch_evergreen_images.py` |
| `fix_urls.py` | Patch missing URLs in existing evergreen entries | `python3 scripts/fix_urls.py` |
| `patch_evergreen_images.py` | Patch EVERGREEN entries in data.js with imageUrl from results JSON | `python3 scripts/patch_evergreen_images.py` |

### Docs (project root)
| File | Purpose |
|------|---------|
| `HANDOFF.md` | Living state doc — current data, deploys, open items |
| `ENRICHMENT-METHODOLOGY.md` | Pipeline architecture, phase-by-phase enrichment workflow |
| `VENUE-REFRESH-GUIDE.md` | 4-tier monthly venue monitoring with URLs and scrape methods |
| `PLAN.md` | V2 build plan |
| `V3-PLAN.md` | V3 feature backlog |

## Prior Work

| Project | Path | Reusable |
|---------|------|----------|
| V1 Event List (Jan 2026) | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/` | Master.csv (517 events, 63 venues), venue_branding.json, taste_matcher_v2.py, 259 event images, TASTE_PROFILE.md |
| Archived pre-V1 | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/` | Calendar exports, early CSVs — mostly superseded |

## Technical Constraints

- **stdlib-only Python** — PEP 668 blocks pip install on Python 3.14. All scripts use urllib, html.parser, json, re.
- **Git push to main blocked** — Repo policy requires feature branch. Use `npx vercel --prod` for direct deploy.
- **No friend names on site** — Site is public/shareable. Friend matching lives only in social_scan.py output.
- **SSL cert disabled in enrichment** — Some event sites have cert issues; scripts disable verification.
- **Firecrawl CLI** (v1.15.2) — Used for events with no officialUrl: `npx firecrawl-cli search/scrape`
- **AXS blocks scraping** (403) — Use Songkick artist page og:image instead: `http://images.sk-static.com/images/media/img/col4/TIMESTAMP-ID.jpg`
- **Eventbrite og:image is relative** — Decode URL param to get real CDN URL: `https://cdn.evbuc.com/images/[id]/...`
- **data.js events are NOT in ID order** — Regex patching with DOTALL can misfire. Use block-scoped `patch_event_field()` from ENRICHMENT-METHODOLOGY.md.
- **Facebook Events** — Use `claude-in-chrome` skill → navigate share URL → `get_page_text` to extract event details including lat/lng.

## Session Logs

| Date | Log | Summary |
|------|-----|---------|
| 2026-01-07 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-01-07_atl-event-list-remediation.md` | V1 pipeline: taste_matcher_v2, venue branding, gap fill |
| 2026-04-20 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-20_ATL-Events-V2-Skill-Architecture.md` | Skills written: atl-events v3, atl-events-builder v1, alice v1 |
| 2026-04-21 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-21_ATL-Events-Site-Build.md` | V2 full build + deploy, 13 events, GitHub + Vercel |
