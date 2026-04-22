# ATL Events Site — Session Handoff
**Date:** 2026-04-21
**Session:** V4 — Event Enrichment Pipeline + Social Scan Algorithm
**Status:** Deployed to production

---

## What Was Built This Session

### Social Scan Algorithm (scripts/social_scan.py)
1. **Inner Circle concept** — Hardcoded always-invite crew per social group (Concert Squad 7, Kids Crew 8, Couples Dinner 4, Close By 4) vs. broader CRM groups
2. **Slot diversity** — Per-slot event selection (GROUP_NIGHT:4, DATE_NIGHT:2, FAMILY_OUT:3, SOLO_RESET:2) instead of global top-10-by-score
3. **Two-tier friend matching** — "inner" (always-invite, never capped) vs. "outreach" (overdue non-inner, capped at 4)
4. **target_slot parameter** — Restricts best_friends_for_event() to match only the specific slot type, preventing group bleed
5. **Outreach deduplication** — `used_outreach` set tracks names across events
6. **Group text drafts** — Copy-paste-ready texts for inner circle invites

### Event Enrichment Pipeline (scripts/enrich_events.py)
7. **Three-mode script** — `--audit` (identify gaps), `--fetch` (og:image + ticket extraction), `--apply` (patch data.js)
8. **Phase 1: Free events** — Set ticketUrl = officialUrl for 6 free events (instant)
9. **Phase 2: og:image extraction** — stdlib urllib + html.parser, extracted from officialUrl pages (+6 images)
10. **Phase 3: Ticket link extraction** — TicketLinkParser finds ticket platform links on event pages
11. **Phase 4: Firecrawl search** — Parallel agents searched Eventbrite, Ticketmaster, AXS, Dice, venue sites for remaining events (+16 tickets, +10 images)
12. **17 new event images downloaded** — Total now 24/28 events with images

### /social-scan Command Updated
13. **Step 2** reads SAE file as primary friend source (with CRM JSON fallback)
14. **Step 3** reads events.json from ATL-Events-Site/scripts/ (with Brain vault fallback)

---

## Data Coverage: Before → After

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| ticketUrl | 4/28 (14%) | 26/28 (93%) | +22 |
| imageUrl | 8/28 (29%) | 24/28 (86%) | +16 |
| officialUrl | 19/28 (68%) | 28/28 (100%) | +9 |

### Remaining Gaps
- **ticketUrl missing:** Lake Claire Drum Circle (free, no platform), Strawberry Picking (walk-up/seasonal)
- **imageUrl missing:** Supertask (only 205x115 placeholder), Atlanta Streets Alive x2 (duplicate entries), Peachtree Road Race

---

## Deployed

```
Production: https://atl-events.vercel.app
Internal:   https://atl-events.vercel.app/?mode=internal
Commit:     51934d2
Deploy:     dpl_3whHkxzY8Cci2NU9j4zeRkGyLM8Z
```

---

## Files Modified/Created

| File | Changes |
|---|---|
| `data.js` | 47 fields patched: ticketUrl, imageUrl, officialUrl across 25 events |
| `scripts/enrich_events.py` | New — three-mode enrichment pipeline (audit/fetch/apply), stdlib-only |
| `scripts/enrichment_config.json` | New — audit output identifying all data gaps |
| `scripts/enrichment_results.json` | New — fetch results with all discovered URLs |
| `scripts/firecrawl_batch1.json` | New — Firecrawl search results for music events |
| `scripts/firecrawl_batch2.json` | New — Firecrawl search results for family/activity events |
| `scripts/events.json` | Re-exported with enriched data |
| `scripts/social_scan.py` | Inner circle, slot diversity, group text drafts, outreach dedup |
| `scripts/export_events.py` | Existing — data.js → events.json converter |
| `images/` | +17 new images (total 25 files) |

---

## New Images This Session

| Event | id | Image File |
|---|---|---|
| Shake the Lake | 2 | `shake_the_lake.png` (341KB) |
| Dino Fest | 4 | `dino_fest.png` (910KB) |
| Vintage Culture | 7 | `vintage_culture.jpg` (70KB) |
| Atlanta Jazz Festival | 10 | `atlanta_jazz_festival.jpg` (117KB) |
| Atlanta Streets Alive | 11 | `atlanta_streets_alive.jpg` (484KB) |
| Supertask | 14 | `supertask.jpg` (7KB) |
| Center for Puppetry Arts | 16 | `center_for_puppetry_arts.gif` (9350KB) |
| Sol Dance | 17 | `sol_dance_ecstatic_dance.jpg` (366KB) |
| High Museum | 18 | `high_museum_second_sunday.jpg` (411KB) |
| Dad's Garage: Adventure | 19 | `dad_s_garage_adventure_playhouse.png` (43KB) |
| Lake Claire Drum Circle | 20 | `lake_claire_full_moon_drum_circle.jpg` (209KB) |
| Strawberry Picking | 21 | `strawberry_picking.jpg` (209KB) |
| Fernbank After Dark | 22 | `fernbank_after_dark.jpg` (253KB) |
| Chattahoochee Tubing | 24 | `chattahoochee_tubing.png` (60KB) |
| ABG Summer Nights | 26 | `abg_summer_nights.jpg` (170KB) |
| Shaky Knees 2026 | 28 | `shaky_knees_2026.png` (77KB) |
| Dad's Garage: ROAD TRIP! | 30 | `dad_s_garage_road_trip.png` (43KB) |

---

## Ticket URL Sources

| Event | Platform | Source |
|---|---|---|
| Patrick Topping | Eventbrite | districtatlanta.com |
| Shake the Lake | Facebook Event | beatsonthelake.com |
| Dino Fest | Stone Mountain | stonemountainpark.com |
| Vintage Culture | Eventbrite | districtatlanta.com |
| Chet Faker | Ticketmaster | masqueradeatlanta.com |
| Supertask | Ticketmaster | axs.com |
| Disclosure DJ Set | Eventbrite | districtatlanta.com |
| Center for Puppetry Arts | puppet.org | Direct |
| Sol Dance | Momence | soldancemovement.com |
| Dad's Garage x2 | Salesforce/PatronTicket | dadsgarage.com |
| Fernbank After Dark | fernbankmuseum.org | Direct |
| Chattahoochee Tubing | FareHarbor | coolrivertubing.com |
| Peachtree Road Race | LetDoThis | atlantatrackclub.org |
| ABG Summer Nights | atlantabg.org | Direct |
| Empire of the Sun | Ticketmaster | livenation.com |
| Free events x6 | officialUrl | Direct |

---

## Enrichment Pipeline Usage

```bash
# 1. Audit gaps
python3 scripts/enrich_events.py --audit

# 2. Fetch og:images + ticket links from officialUrls
python3 scripts/enrich_events.py --fetch

# 3. Apply results to data.js + re-export events.json
python3 scripts/enrich_events.py --apply

# For events without officialUrl, use firecrawl manually:
npx firecrawl-cli search "[artist] [venue] Atlanta tickets 2026"
```

---

## Next Session

### Track A: Remaining Data Gaps
- Replace Supertask placeholder with better image
- Find images for Atlanta Streets Alive (ids 23, 29) and Peachtree Road Race
- Add `add_event.py` — "Drop a URL, get a data.js entry" workflow

### Track B: Communication Intelligence (planned, not built)
- `personal-crm/tools/comm_scan.py` — auto-update last_contact from iMessage/calls
- Availability signal detection ("out of town" → suppress from suggestions)
- See plan: `~/.claude/plans/breezy-sprouting-nest.md` Track B

### Track C: CRM Completeness (planned, not built)
- Expand SAE from 55 to 80+ people
- Add ATL location filtering
- See plan: Track C

### Track D: Site Social Layer (planned, not built)
- Show "who to invite" in event drawers
- Pre-drafted texts and calendar download
- See plan: Track D

---

## Plan Location

See roadmap: `~/.claude/plans/breezy-sprouting-nest.md`
