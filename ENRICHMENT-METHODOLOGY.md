# Event Enrichment Methodology

## Overview

Session V4 enriched 25 of 28 curated events, improving data coverage from:
- **ticketUrl:** 4/28 (14%) → 26/28 (93%)
- **imageUrl:** 8/28 (29%) → 24/28 (86%)
- **officialUrl:** 19/28 (68%) → 28/28 (100%)

---

## Pipeline Architecture

```
data.js → export_events.py → events.json
                                  ↓
                        enrich_events.py --audit
                                  ↓
                        enrichment_config.json (gap report)
                                  ↓
                        enrich_events.py --fetch
                          ├── Phase 1: Free events (instant)
                          ├── Phase 2: og:image from officialUrl (urllib)
                          ├── Phase 3: Ticket links from officialUrl (html.parser)
                          └── Phase 4: YouTube thumbnail fallback
                                  ↓
                        enrichment_results.json (partial)
                                  ↓
                        Firecrawl agents (parallel search)
                          ├── Batch 1: Music events (6 events)
                          └── Batch 2: Family/activity events (12 events)
                                  ↓
                        firecrawl_batch1.json + firecrawl_batch2.json
                                  ↓
                        Merge → enrichment_results.json (complete)
                                  ↓
                        Download external images to images/
                                  ↓
                        enrich_events.py --apply
                                  ↓
                        data.js (patched) → export_events.py → events.json
```

---

## Phase Details

### Phase 1: Free Events (Instant, +6 ticketUrls)

For events marked `free: true` that have an `officialUrl` but no `ticketUrl`, set `ticketUrl = officialUrl`. Rationale: free events don't have a separate ticket platform — the official page IS where you go.

**Events fixed:** Inman Park Festival, High Museum Second Sunday, Atlanta Jazz Festival, Atlanta Streets Alive x3

### Phase 2: og:image Extraction (+6 images)

For events with `officialUrl` but no `imageUrl`, fetch the page via `urllib.request` and parse `<meta property="og:image" content="...">` using Python's `html.parser.HTMLParser`.

**Technical details:**
- `OGImageParser` class extends `HTMLParser`, captures `og:image` content attribute
- Pages fetched with `urlopen(req, timeout=15)` using SSL context with `verify_mode=CERT_NONE` (some event sites have expired certs)
- Max 500KB read per page to avoid memory issues
- 0.5s delay between requests

**Success rate:** 6/15 pages had og:image (puppet.org, soldancemovement.com, high.org, dadsgarage.com x2, coolrivertubing.com)
**Common failures:** Sites using JavaScript-rendered content (atlantabg.org, fernbankmuseum.org), missing og:image tags (jaemorfarms.com), DNS resolution failures (atlstreetsalive.com, shakykneesmusic.com)

### Phase 3: Ticket Link Extraction (+3 ticketUrls)

For events with `officialUrl` but no `ticketUrl`, scan the page HTML for `<a>` tags whose `href` or text contains ticket-related keywords.

**Technical details:**
- `TicketLinkParser` class extends `HTMLParser`, tracks `<a>` tags
- Keyword regex: `ticket|buy|book|register|rsvp|eventbrite|axs.com|ticketmaster|dice.fm|seetickets|tixr|universe.com|showclix|etix|simpletix`
- Priority: external ticket platform links ranked above self-hosted links
- Facebook links filtered out post-fetch (not real ticket platforms)

**Quality control applied:**
- Removed Facebook page links (not ticket URLs): Sol Dance, Strawberry Picking, Fernbank, Cool River Tubing
- Fixed puppet.org group tickets → general visit page
- Cleaned Dad's Garage URL fragment (`#/` suffix)

### Phase 4: YouTube Thumbnail Fallback (0 new)

For events with `youtubeId` but no `imageUrl`, try `https://img.youtube.com/vi/{id}/maxresdefault.jpg`. No new images this phase — all YouTube events already had images.

### Phase 5: Firecrawl Search (+16 tickets, +11 images, +9 officialUrls)

For events with no `officialUrl` at all, used `npx firecrawl-cli search` (v1.15.2) to find event pages on the open web.

**Two parallel agent batches:**

**Batch 1 — Music Events (6 events):**
Searched `"[artist] [venue] Atlanta tickets 2026"` and scraped promising results.

| Event | Platform Found | Method |
|-------|---------------|--------|
| Patrick Topping | Eventbrite via districtatlanta.com | search → scrape venue page |
| Vintage Culture | Eventbrite via districtatlanta.com | search → scrape venue page |
| Disclosure DJ Set | Eventbrite via districtatlanta.com | search → scrape venue page |
| Supertask | Ticketmaster + AXS | search → both platforms listed |
| Chet Faker | Ticketmaster via masqueradeatlanta.com | search → scrape venue page |
| Empire of the Sun | Ticketmaster via livenation.com | search → direct listing |

**Batch 2 — Family/Activity Events (12 events):**

| Event | Finding | Method |
|-------|---------|--------|
| Shake the Lake | beatsonthelake.com + FB event (only ticket source) | search → scrape |
| Dino Fest | stonemountainpark.com event page + tickets page | search → scrape |
| Lake Claire Drum Circle | lcclt.org event page | search |
| Strawberry Picking | jaemorfarms.com/u-pick-strawberries + image | search → scrape |
| Fernbank After Dark | fernbankmuseum.org/visit/get-tickets/ | search → scrape |
| Peachtree Road Race | atlantatrackclub.org → letsdothis.com registration | search → scrape |
| Shaky Knees | Official 2026 poster image from CDN | search |
| Atlanta Jazz Festival | 2026 graphic from atljazzfest.com | search |
| Atlanta Streets Alive | Cloudfront action photo | search |
| Sol Dance | momence.com booking platform | search → scrape |
| ABG Summer Nights | atlantabg.org lantern parade photo | search |
| Cool River Tubing | fareharbor.com booking embed | search → scrape |

### Image Download

All external image URLs from Phases 2 and 5 were downloaded to local `images/` directory using `urllib.request`:
- SSL verification disabled for CDN compatibility
- Minimum 1KB file size filter (rejects placeholders)
- Filenames slugified from event titles
- 0.3s delay between downloads

**17 images downloaded**, 1 rejected (Supertask 205x115px — too small for hero treatment)

### Apply Phase

Regex-based patching of `data.js` (JavaScript object literal, not JSON):
1. Find event block by `id: N,` pattern
2. Within that block, match `fieldName: null` or `fieldName: 'old value'`
3. Replace with `fieldName: 'new value'`
4. 47/47 fields patched, 0 failures

---

## Data Sources by Reliability

| Source | Type | Reliability | Notes |
|--------|------|------------|-------|
| Venue websites (districtatlanta.com, etc.) | Scrape | High | Official event pages with ticket links |
| Eventbrite | Search | High | Platform-verified ticket listings |
| Ticketmaster/LiveNation | Search | High | Major platform listings |
| og:image meta tags | Parse | Medium | Some sites use generic images |
| AXS | Search | High | Venue-specific ticketing |
| FareHarbor/Momence | Search | Medium | Niche booking platforms |
| Facebook Events | Search | Low | Not a real ticket platform, filtered out |
| YouTube thumbnails | Direct | Medium | Good quality but not event-specific |

---

## Rerunning the Pipeline

```bash
# Full pipeline
cd /Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site

# 1. Export current data.js to JSON
python3 scripts/export_events.py

# 2. Audit gaps
python3 scripts/enrich_events.py --audit

# 3. Auto-fetch what we can (og:image, ticket links)
python3 scripts/enrich_events.py --fetch

# 4. For events still missing data, use firecrawl manually:
npx firecrawl-cli search "[event] [venue] Atlanta tickets 2026"
npx firecrawl-cli scrape "[url]"

# 5. Add results to enrichment_results.json manually, then:
python3 scripts/enrich_events.py --apply

# 6. Deploy
npx vercel --prod --yes
```

---

## Scripts Reference

| Script | Purpose | Deps |
|--------|---------|------|
| `scripts/export_events.py` | data.js → events.json | stdlib |
| `scripts/enrich_events.py` | Audit + fetch + apply enrichment | stdlib |
| `scripts/fetch_images.py` | Original image downloader (image_sources.json) | stdlib |
| `npx firecrawl-cli` | Web search and scraping | npm (v1.15.2) |

---

## Proven Playbooks & Prior Art

These archived files contain battle-tested strategies for event data gathering, venue discovery, and refresh workflows:

### Event Scraping & Data Sources
| File | Path | What It Contains |
|------|------|-----------------|
| ALTERNATIVE_DATA_SOURCES.md | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/` | Source strategy with status: 19hz.info (works with WebFetch), AXS/Ticketmaster/RA/Bandsintown/EDMTrain (need browser). Ranked by reliability. |
| REFRESH_WORKFLOW.md | same | Weekly 60-min refresh cycle. Priority venue list. Step-by-step for keeping events current. |
| BROWSER_AUTOMATION_GUIDE.md | same | Selenium/Playwright patterns for sites that block simple scraping |
| firecrawl-batch.sh | `~/Documents/Coding/Projects/2025-11-06_brain-scripts/` | Batch scraping with rate limiting, title extraction, metadata injection |

### Venue Discovery & Scoring
| File | Path | What It Contains |
|------|------|-----------------|
| Atlanta_Events_Guide.md | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/` | Full venue directory with calendar URLs for 30+ venues |
| TASTE_PROFILE.md | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/planning/` | Genre scoring (1-5), venue preferences, artist history |
| venue_branding.json | same | 10+ venues with logo_url, primary_color, vibe keywords |
| REFRESH_PLAN_JAN_AUG_2026.md | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/planning/` | Venue batches with calendar URLs by priority tier |

### Evergreen & Family Activities
| File | Path | What It Contains |
|------|------|-----------------|
| ATL_Date_Night_Guide.md | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/` | Date night experiences by category: cabaret, escape rooms, workshops, dining |
| EXPERIENCE_LIST.md | same | Curated repeatable experiences by category (family, solo, social, seasonal) |
| KIDS_ATL_GUIDE.md | same | Monthly family calendar with recurring annual festivals |
| JOY_MAP_ANALYSIS_V4.md | same | Personal energy matrix, neighborhood hubs, what energizes vs drains |

### Proven Scraping Scripts (from prior project)
| Script | Path | Pattern |
|--------|------|---------|
| fetch_assets.py | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/` | Image download with skip-if-exists, requests-based |
| consolidate_scrape.py | same | Batch JSON merge + dedup on (Event_Name, Venue, Date) |
| taste_matcher_v2.py | same | Two-mode: `--prepare` exports undistilled, `--apply` merges enriched results |
| ATL Event List Master.csv | same | 162KB consolidated event database (historical reference) |

### Firecrawl Escalation Pattern
From `~/.claude/skills/firecrawl-cli/SKILL.md`:
1. **search** — find URLs for an event/venue
2. **scrape** — extract structured data from a URL
3. **map+scrape** — discover all pages on a site, then scrape selectively
4. **crawl** — full site crawl for comprehensive data
5. **browser** — JavaScript-rendered sites that block simple scraping
