# ATL Radar — Agent Handoff (Cold-Start Doc)
**Updated:** 2026-07-06 | **Session:** Mass event + image enrichment (41 → 116 events)

---

## Agent Bootstrap

| Key | Value |
|-----|-------|
| **Owner** | Dima Perkis |
| **Workspace** | `/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/` |
| **Live URL** | https://atlradar.vercel.app |
| **GitHub** | https://github.com/WhatWouldDimaDo/atl-events (public) |
| **Deploy command** | `/opt/homebrew/bin/vercel --prod --yes` from project root |
| **Verify** | Check https://atlradar.vercel.app after deploy |

---

## Skills to Load

| Skill | When |
|-------|------|
| `atl-events-builder` | Any site build, data, or deploy work |
| `atl-events` | Event scoring, friend matching, slot system knowledge |
| `alice` | Social planning — "what to do this weekend?" |
| `frontend-design` | UI/CSS work |
| `personal-crm` | CRM work — comm_scan, social_scan, SAE, contact matching. Load this when touching any CRM-related scripts |

---

## File Architecture

### Code (site root)
| File | Purpose |
|------|---------|
| `index.html` | HTML structure. Contains `#surprise-strip` div after events grid |
| `app.js` | All site logic. See function map below |
| `style.css` | All CSS. New blocks at bottom: `.surprise-strip`, `.er-axis-star`, `.btn-cal` |
| `data.js` | EVENTS array (116) + EVERGREEN array (142). `TODAY = '2026-07-06'` — **update at session start** |
| `about.html` | About page |
| `vercel.json` | Static site config, security headers, cache control |

### Key app.js Functions
| Function | Purpose |
|----------|---------|
| `renderEventCard(ev, idx)` | Renders accordion row (collapsed + peek states) |
| `togglePeek(id)` | Toggle `.peeked` class — expands accordion row |
| `openDetails(id)` | Opens bottom sheet for full detail |
| `buildBottomSheetHTML(ev)` | Full detail bottom sheet HTML — includes cal section |
| `applyEventFilters()` | Filter + sort events, calls `renderSurpriseStrip` |
| `renderSurpriseStrip(filtered)` | Renders "Outside your filter" discovery strip |
| `generateICS(evId)` | Client-side ICS download for calendar add |
| `generateGCalUrl(ev)` | Returns Google Calendar add URL |
| `copyEventShare(evId)` | Copies title + ticket URL to clipboard |
| `topScoreAxis(ev)` | Returns `★ Axis` tag if any scoreReasoning axis ≥90 |
| `updateHeroStats()` | Updates hero stat cards. Top Picks card is clickable → sort by score |

### Scripts (`scripts/`)
| Script | Purpose | Key Args |
|--------|---------|----------|
| `weekly_digest.py` | **Phase B chain** — runs comm_scan → export_events → social_scan, prepends contact activity sections, writes to Brain vault | `--dry-run` (no writes), `--no-crm` (skip scan) |
| `comm_scan.py` | iMessage + call history scanner → 3-tier matching → CRM writeback | `--dry-run` (preview, no CRM), `--write-crm` (apply) |
| `export_events.py` | Export EVENTS from data.js → events.json | (none) |
| `enrich_events.py` | Fill ticket URLs and images | `--audit`, `--fetch`, `--apply` |
| `expand_concerts.py` | Mine Master CSV + batch JSONs for concert candidates | (none) |
| `social_scan.py` | Weekly social brief — inner circles, slot matching, group texts | (none) |
| `fetch_images.py` | Download event images (stdlib only) | (none) |
| `fetch_evergreen_images.py` | og:image + venue logo downloader for evergreen | (none) |
| `fix_urls.py` | Patch missing URLs in existing evergreen entries | (none) |
| `patch_evergreen_images.py` | Patch EVERGREEN entries with imageUrl from results JSON | (none) |

### Docs (project root)
| File | Purpose |
|------|---------|
| `HANDOFF.md` | This file — cold-start doc |
| `PRD.md` | 15-section product requirements + design brief |
| `FUNCTIONAL-REQUIREMENTS.md` | Extracted functional requirements (no UX) — written Apr 30 |
| `DESIGN-REVIEW.md` | Gap analysis vs best practices, top 5 recs, quick wins — written Apr 30 |
| `CRM-FUNCTIONAL-REQUIREMENTS.md` | Full CRM automation requirements — sources, matching, SAE update, scheduler — written May 1 |
| `CRM-BEST-PRACTICES.md` | CRM best practices audit — root cause analysis, SAE silent killer, calendar gap, phase priorities — written May 1 |
| `ENRICHMENT-METHODOLOGY.md` | Pipeline architecture, phase-by-phase enrichment workflow |
| `VENUE-REFRESH-GUIDE.md` | 4-tier monthly venue monitoring with URLs and scrape methods |

---

## Current Data State

### Curated Events (116)
| Metric | Count | Notes |
|--------|-------|-------|
| ticketUrl | ~107/116 | ~92% |
| imageUrl | 111/116 | ~96% — 5 still missing after Jul 6 research (Soular Flare, Elevated Rhythms, MVMT LABS, Juneteenth, Concert for Community — only 100x100 IG profile pics found; see `scripts/image_research_results_2026-07-06.json`) |
| officialUrl | ~91/116 | ~78% |
| TODAY | `'2026-07-06'` | **Update at start of each session** |

### Evergreen Activities (142)
| Metric | Count |
|--------|-------|
| Total | 142 |
| With imageUrl | ~140/142 |
| With coordinates | 142/142 |

---

## Event Card UX (V6 — current)

3-state accordion row model:

| State | Trigger | Contents |
|-------|---------|---------|
| **Collapsed** | Default (~62px) | Thumb, title, meta, score badge, optional `★ Axis` tag, chevron |
| **Peeked** | Tap row | Tags, note (3-line clamp), RSVP (internal), Buy + Full Details |
| **Full Detail** | "Full Details →" → bottom sheet | Hero image, note, calendar add, YouTube, lineup, radar, links |

**Discovery strip:** When wizard is active, a dashed strip below the grid shows up to 3 high-scoring events (≥70) outside the current filter. Clicking opens the bottom sheet.

**Hero stats:** "Top Picks" card is clickable — jumps to events section sorted by score.

---

## CRM Automation (Phase A + GC Fix — implemented)

**Script:** `scripts/comm_scan.py`

```bash
python3 scripts/comm_scan.py --dry-run      # preview changes, no writes
python3 scripts/comm_scan.py --write-crm    # update crm_database.json
```

**3-tier contact matching:**
1. **CRM tier** (83 people in `crm_database.json` + `crm_database_batch2.json`) → data written back
2. **GC tier** (`gc_phone_index.json` — 1,014 entries at `~/Documents/Coding/Projects/personal-crm/derived/`) → tracked as `gc_known`, no writeback
3. **AddressBook tier** (832 contacts) → used only to enrich truly-unknown handle names in `new_contacts`

**Current scan output (2026-05-01):** 72 CRM matched | 250 GC-known contacts | 116 unknown handles | 8 manual-only

**What Phase A does:**
- Updates `last_contact_date`, `last_platform`, `contact_count_90d` in `crm_database.json`
- Never backdates or overwrites `in_person` with a digital platform
- GC-only contacts (in Google Contacts, not CRM) tracked in `gc_known` bucket — not written to CRM JSON
- Collects unmatched handles (3+ msgs or 1+ calls in 90d) as `new_contacts`, enriched with AddressBook names
- Supports `iMessage_handle` field in CRM for contacts with no phone number
- Logs changes to `scripts/comm_scan_log_YYYY-MM-DD.json`
- Includes `attributedBody` parser stub for Ventura+ messages (used by Phase C)

**Manual-only contacts (no trackable handle in CRM):** Emily Kritzer, Hadi Irvani, Charles, Marina, Rich, Devin, Meghan Smithgall, Ben Holst

**CRM people added this session:** Jhony Ventura, Marshall Seese, Jackie Ratner, Alisa Feldman (née Freeman, David Feldman's wife), Ben Karsai

**GC phone index:** `~/Documents/Coding/Projects/personal-crm/derived/gc_phone_index.json` — 1,014 entries — is the authoritative phone master. comm_scan.py loads this as tier 2. When editing comm_scan, always load `personal-crm` skill to understand the full data model.

**CRM databases:**
- `~/Documents/Brain/02_Areas/Friends/crm_database.json` — primary (83 people, written back by --write-crm)
- `~/Documents/Brain/02_Areas/Friends/crm_database_batch2.json` — supplemental (read-only in comm_scan)

**Automation options:**
- **launchd** (recommended): Friday 7 AM, runs offline. Plist template in `CRM-AUTOMATION-SPEC.md §4.5`
- **Manual**: Run before weekly planning session — takes ~10 seconds

**Full spec:** `~/Documents/Brain/03_Resources/Development/Claude-Code/CRM-AUTOMATION-SPEC.md`

---

## Phase B: Weekly Digest (implemented)

**Script:** `scripts/weekly_digest.py`

```bash
python3 scripts/weekly_digest.py              # full run, write to vault
python3 scripts/weekly_digest.py --dry-run    # scan + assemble, print to stdout (no vault write, no CRM update)
python3 scripts/weekly_digest.py --no-crm     # skip comm_scan, use existing results.json
```

**Output:** `~/Documents/Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md`

**What it produces:**
- Header (CRM count, GC count, unknown count, generated timestamp)
- "This Week's Contacts" — everyone contacted in last 7 days; ★ = in CRM, unlabeled = GC contact
- "New Contact Inbox" — truly unknown handles with AddressBook name enrichment
- "Manual-Only Contacts" — CRM people with no trackable handle
- Full `social_scan.py` brief (event recommendations, overdue table, draft texts)

---

## Slot & Scoring System

| Slot | Meaning |
|------|---------|
| `GROUP_NIGHT` | Friends group outing |
| `DATE_NIGHT` | Dima + Jeannie |
| `FAMILY_OUT` | Dima + Dean (+ Jeannie) |
| `SOLO_RESET` | Dima solo |
| `PAPA_DEAN` | Dean-centric activities |

Tiers: S (90+), A (80-89), B (70-79), C (<70)
Radar axes: `genreMatch`, `venueQuality`, `formatRarity`, `lineupStrength`, `valueForMoney`
Kids for FAMILY_OUT matching: Dean (b. Aug 2022), Ruby (b. 2026)

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| stdlib-only Python | PEP 668 blocks pip on Python 3.14 |
| Git push to main blocked | Repo policy requires feature branch; deploy via `vercel --prod` |
| No friend names on site | Site is public/shareable; friend data lives only in social_scan.py |
| SSL cert disabled in enrichment | Some event sites have cert issues |
| Firecrawl CLI v1.15.2 | `npx firecrawl-cli search/scrape` — used when no officialUrl |
| Regex patching of data.js | JS object literals can't be parsed as JSON |
| CRM writeback never backdates | `comm_scan.py` only advances `last_contact_date`, never overwrites in_person |
| gc_phone_index is tier 2 | 1,014 GC entries resolve named contacts that aren't in crm_database.json; tracked but no CRM writeback |
| AddressBook is last resort | Only used to enrich names for truly-unknown handles in new_contacts |
| GC-known contacts not written back | They appear in social digest `This Week's` table but don't pollute crm_database.json |

---

## Roadblocks & Learnings

| Issue | Resolution |
|-------|-----------|
| AXS blocks scraping (403) | Use Songkick artist page og:image: `http://images.sk-static.com/images/media/img/col4/TIMESTAMP-ID.jpg` |
| Eventbrite og:image is relative | Decode URL param to get real CDN URL: `https://cdn.evbuc.com/images/[id]/...` |
| data.js patch regex misfires | Events not in ID order; use block-scoped `patch_event_field()` — see ENRICHMENT-METHODOLOGY.md |
| St. Lucia image → Magic for Adults | Confirmed misfire from Jul 2026: `enrich_events.py --apply` regex jumped event boundary |
| Facebook Events extraction | `claude-in-chrome` navigate → get_page_text works; share URLs redirect to full event page with lat/lng |
| Eventbrite dates not in defuddle | Pages are JS-rendered; extract JSON-LD from raw HTML with `curl | python3 -c "re.findall..."` |
| `attributedBody` on Ventura+ | Many messages have null `text` — need plistlib decode (Phase C) |
| comm_scan context gap | Always load `personal-crm` skill when editing comm_scan/social_scan |

---

## Open Items

- [ ] Update `TODAY` in data.js each session (currently `'2026-07-06'`)
- [ ] 5 events still missing images (no real flyers exist online) — see Current Data State
- [x] Fix `enrich_events.py --apply` — **done 2026-07-06**: block-scoped patch_event_field() + mandatory post-apply validation (exports events.json, diffs all tracked URL fields, restores backup + exit 1 on any unintended change). `--audit` now also flags YouTube-thumbnail fallback images and checks ticket availability with `--check-tickets`.
- [ ] Add `iMessage_handle` or phone for: Hadi Irvani, Rich, Charles, Marina, Emily Kritzer, Devin, Meghan Smithgall, Ben Holst (enables comm_scan auto-tracking)
- [x] A6: SAE cadence writeback — `update_sae_cadence()` added to comm_scan.py, runs with `--write-crm`. Advanced 44 entries on first run.
- [x] Phase B: `weekly_digest.py` — chains comm_scan + export_events + social_scan → `Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md`
- [x] GC phone index integration — comm_scan.py now resolves 925 additional GC contacts as gc_known
- [ ] Set up launchd plist for Friday 7 AM scheduled run (template in CRM-AUTOMATION-SPEC.md §4.5)
- [ ] Update `personal-crm` SKILL.md to document gc_phone_index.json as tier-2 phone master
- [ ] Update CRM-AUTOMATION-SPEC.md to document 3-tier matching architecture
- [ ] Phase C: Availability signal extraction from iMessage content (attributedBody parser is ready)
- [ ] Phase C: Kids age tracking — add `kids: [{name, birth_year}]` to CRM schema
- [x] Track D: Site social layer — **done 2026-07-06**: invite panel in bottom sheet (internal mode only, FIRST NAMES ONLY since data.js is public), FRIEND_SLOTS + generateDraftText + Copy Text. Also Rec 2 "Went ✓" attended state. NOT yet deployed — on branch `fable-crm-radar-2026-07-06` awaiting Dima review.
- [ ] Add ATL Radar to dimadimadima.com featured projects
- [ ] Review CRM-FUNCTIONAL-REQUIREMENTS.md + CRM-BEST-PRACTICES.md — key finding: SAE is the "silent killer" (social_scan reads stale SAE dates not crm_database.json), GCal not integrated

---

## Deploy History

| Deploy ID | What |
|-----------|------|
| ba48146 | Initial commit |
| 636026c | V3: internal mode, RSVP, image pipeline |
| 51934d2 | Enrichment: +22 ticket URLs, +16 images |
| f78d4ea | Evergreen 57→110 + enrichment docs |
| dpl_G9om5NFgSHQ8bEPJV4TWDZsdBjgK | Evergreen images (110/110) + card rendering |
| dpl_6DvCysiV9KDUDbZYbMFqfeDGwx5P | Design polish: hover glow, sticky wizard |
| dpl_92hVsLroaZ5bfnFondt8G8airqqA | 35→41 events, Jul-Aug coverage |
| dpl_GVgLNRqvpQfUhwqbvtWmqVfxHJ1i | **V5: Accordion row UX** — replaced horizontal scroll |
| dpl_GKyqS7aFcsYpHdomdHJBPJzaPuVW | **V6: Best practices** — TODAY Apr 30, urgent sort, axis star, Add to Calendar, share+ticket, Surprise Me strip, Top Picks clickable |
| atl-events-74hkxls3d | **Jul 6 mass enrichment** — 41→116 events, 110→142 evergreen, ~105/116 images, ~30 YouTube IDs, Facebook event intake (ids 109–118), Claremont Pool evergreen, block-scoped patch function |

---

## Prior Work

| Project | Path | Reusable |
|---------|------|---------|
| V1 Event List (Jan 2026) | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/` | Master.csv (517 events, 63 venues), venue_branding.json, taste_matcher_v2.py |

---

## Session History

| Date | Log |
|------|-----|
| 2026-04-21 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-21_ATL-Events-Site-Build.md` |
| 2026-04-22 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-22_CCC-ATL-Events-Session-Analysis-Handoff-Infra.md` |
| 2026-04-25 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-25_atl-radar-ux-crm-prd.md` |
| 2026-04-30 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-04-30_atl-radar-v6-crm-phase-a.md` |
| 2026-05-01 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-05-01_atl-radar-phase-b-gc-fix.md` |
| 2026-07-06 (2) | `Brain/03_Resources/Development/Claude-Code/Sessions/ATL-RADAR-CRM-FABLE-SESSION-2026-07-06.md` — Tier 1-3 retrospective: enrich --apply hardened, Track D, Phase B/C, awaiting-reply, intake/scan automation. Branch `fable-crm-radar-2026-07-06` awaits review+deploy |
| 2026-07-06 | `Brain/03_Resources/Development/Claude-Code/Sessions/2026-07-06_atl-radar-mass-event-image-enrichment.md` — mass enrichment + skill/docs update (SKILL.md v2.2.0, ENRICHMENT-METHODOLOGY.md phases 6–7, CLAUDE.md constraints) |
