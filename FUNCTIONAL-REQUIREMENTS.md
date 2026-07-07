# ATL Radar — Functional Requirements
**Extracted from:** PRD.md, HANDOFF.md, app.js (L1-900), data.js (L1-100)
**Date:** 2026-04-30

---

## 1. Data Model

### 1.1 Events
Each event record carries:
- Unique sequential integer `id`
- Date fields: `date` (YYYY-MM-DD), optional `dateEnd`, display `dateStr`
- Location: `venue`, `address`, `lat`/`lng`, `distance` enum (ITP / OTP-near / OTP-far / road-trip)
- Scheduling: `time` (display string), `timeSlot` enum (morning / afternoon / evening / night)
- Score: `score` (0-100 composite), `tier` (S/A/B/C), `scoreReasoning` object (5 axes)
- Slot tags: `slots` array — one or more of `GROUP_NIGHT`, `DATE_NIGHT`, `FAMILY_OUT`, `SOLO_RESET`, `PAPA_DEAN`
- Category: `category` enum (music / family / comedy / outdoor / social / date / group)
- Detail fields: `genres` (up to 4), `environment` (outdoor/indoor), `eventType`, `age` (All ages / 18+ / 21+)
- Media: `imageUrl`, `youtubeId`, `officialUrl`, `instagramUrl`
- Commerce: `ticketUrl`, `free`, `membershipIncluded`, `membershipVenue`, `advancePurchase`
- Urgency: `urgent` bool, `urgentNote` string
- Content: `lineup`, `setTimes`, `note` (Dima's personal take)
- Recurrence: `recurring` bool, `recurringNote` string

### 1.2 Evergreen Activities
Each evergreen record carries:
- String `id` (e001–e140), `name`, `description`, `notes`
- Classification: `category` (family/solo/date/group/papa), `environment`, `effort` (low/medium/high)
- Scheduling: `timeOfDay`, `bestDays`, `availability` (year-round/seasonal/scheduled), `availabilityNote`
- Location: `address`, `lat`/`lng`, `distance` (ITP/OTP/road-trip)
- Commerce: `cost`, `free`, `membershipIncluded`, `membershipVenue`
- Dual scoring: `deanScore` (1-5 Harvey ball, for Dean at 4yo), `parentScore` (1-5)
- Media: `url`, `imageUrl`, `emoji`

### 1.3 Scoring System
Five axes, each 0-100:
- `genreMatch` — alignment with Dima's documented taste profile
- `venueQuality` — room quality for the event type
- `formatRarity` — how infrequently this format appears in ATL
- `lineupStrength` — artist/headliner quality
- `valueForMoney` — cost-adjusted value (free events score high; expensive events need strong lineup)

Tier thresholds: S ≥ 90 · A 75-89 · B 60-74 · C < 60

Scoring caps:
- Recurring events cap at 72 (format rarity penalized)
- S-tier reserved for once-in-ATL appearances
- Venue multiplier: premium rooms add +5-10 vs generic bar

### 1.4 Slot System
Maps events to Dima's life contexts:
| Slot | Meaning | Wizard "Who" mapping |
|------|---------|----------------------|
| `GROUP_NIGHT` | Friends group outing | friends |
| `DATE_NIGHT` | Dima + Jeannie, no kids | date |
| `FAMILY_OUT` | Kids welcome, all ages | dean, family |
| `SOLO_RESET` | Dima alone | solo |
| `PAPA_DEAN` | Dean-centric (4yo optimal) | papa |

---

## 2. Filtering System

### 2.1 Wizard (Smart Pre-filter)
Three independent single-select axes:
- **When:** now (next 3 days), weekend (Sat-Sun of current week), next 30 days
- **Who:** solo, dean, family, date, friends, papa
- **Vibe:** music, outdoor, indoor, chill (score < 85), food

Wizard state stored in `wizard` object `{when, who, vibe}`. Each axis independently nullable (no selection = ignore axis).

When filter active: non-matching event cards are dimmed with `.wizard-dim` class (not hidden). Matching count displayed in sticky results bar: "N events, M evergreen — See results ↓".

Preview strip: top 12 wizard-matching events rendered as horizontally scrollable mini-cards.

Ruby Nap Banner: shown only when `wizard.who === 'family'`.

### 2.2 Category + Tier Filter Chips
Independent of wizard. Single-select per dimension.
- Category chips: all / music / family / comedy / group / date / free
- Tier chips: all / S / A / B / C
- Sort: date (default) / score

Filter logic combines: date >= today AND category match AND tier match AND search query. Applied simultaneously. Wizard dim overlay applied on top of filtered results.

### 2.3 Evergreen Filters
Four independent dimensions:
- Category: all / family / solo / date / group / papa
- Time of day: any / morning / afternoon / evening
- Day: any / weekdays / weekends
- Availability: all / year-round / seasonal / scheduled

Wizard `who` selection additionally dims non-matching evergreen cards (opacity 0.35) without hiding them.

### 2.4 Universal Search (Cmd+K)
Modal overlay search across both EVENTS and EVERGREEN simultaneously.
- Events search corpus: title, subtitle, venue, note, genres, lineup
- Evergreen search corpus: name, description, category, notes
- Returns up to 6 event matches + 5 evergreen matches
- Keyboard navigable (arrow keys + enter)
- Inline grid search also active via search input (same corpus, live filter)

---

## 3. Event Display System

### 3.1 Three-State Accordion Row
Each event renders as a DOM element with three progressive states:

**Collapsed (default, ~62px):**
- 44px thumbnail (local image → YouTube thumb → category emoji fallback)
- Title + optional subtitle
- Date string + time + venue
- Urgent dot (red) if `urgent: true`
- Score badge (tier-colored)
- Chevron indicator

**Peeked (expanded inline, max-height 400px):**
- Triggered by tap/click on collapsed row (`togglePeek(id)`)
- Tags row: urgent, free, age, environment, up to 2 genre tags, road-trip, recurring
- Note text (3-line clamp)
- RSVP buttons (internal mode only)
- Buy Tickets button (if `ticketUrl` present) + Full Details button

**Full Detail (bottom sheet overlay):**
- Triggered by "Full Details →" button (`openDetails(id)` → `openBottomSheet(id)`)
- Hero image (full-width)
- Category badge + date pill + title + subtitle + venue
- Full tags row
- Buy Tickets + Share buttons (share copies title/date/venue to clipboard)
- Full note text
- RSVP section (internal mode only)
- YouTube embed (lazy — click-to-load on thumbnail, avoids autoplay on scroll)
- Lineup with set times
- Radar chart (Chart.js, 5-axis, tier-colored)
- Official URL + Instagram links
- Recurring note if applicable

### 3.2 Bottom Sheet Behavior
- Slides up from bottom on mobile
- Swipe-down-to-dismiss: drag handle > 100px triggers close
- Backdrop click closes
- ESC key closes
- `body.overflow = hidden` while open (prevents scroll bleed)

### 3.3 Thumbnail Fallback Chain
1. `imageUrl` (local path or https)
2. YouTube thumbnail from `youtubeId` (mqdefault for row, maxresdefault for sheet)
3. Category emoji

---

## 4. Calendar Widget

- Single-month view
- Navigation: ±4 months from today (hard limit: Apr 2026 – Sep 2026)
- Days with events rendered with tier-colored pills
- Pill click: `jumpToEvent(id)` — smooth scrolls to events section, resets any active filters hiding the event, scrolls to card, opens peek, flashes card with `.highlight-flash`
- Calendar pill dimming: when wizard filter active, non-matching event pills dim (`cal-pill-dim`)

---

## 5. Map (Leaflet)

- Dark CartoDB tile layer
- Two data layers: Events (upcoming only) + Evergreen
- Each marker: colored div-icon (14px circle with glow, color by category)
- Marker popup: title, venue/date, tier+score badge, ticket link if available
- Layer toggles: show/hide Events layer, show/hide Evergreen layer
- Category filter: all / music / family / date / group + evergreen
- Map legend: bottom-right, category → color mapping
- Mobile FAB button: smooth-scrolls to map, hides when map is in viewport

---

## 6. RSVP Signal System (Internal Mode Only)

- Activated via `?mode=internal` URL parameter
- Stored in `localStorage` as `rsvp_${id}` per event
- Three states: in / maybe / pass (toggle — clicking same state removes it)
- RSVP state visible on event card (CSS class `rsvp-in/maybe/pass`)
- RSVP buttons in both peek state and bottom sheet
- Hero stat counter shows total "RSVP'd" count (state = 'in')

---

## 7. Hero Stats

Live-computed on page load and on RSVP state change:
- Upcoming events count (date >= today)
- Evergreen count (total)
- S+A tier event count
- RSVP'd count (internal mode only — events with state 'in')

---

## 8. User Workflows

### UC1: Weekend Scan
Default landing state: all upcoming events sorted by date, no filters active. User scans collapsed rows (title + venue + date + score), taps one to peek, optionally opens full detail.

### UC2: Family/Dean Outing
User selects "With Dean" in wizard → events filtered to FAMILY_OUT slot, evergreen filtered to family category. Age 21+ events automatically excluded from results (slots don't include FAMILY_OUT). Wizard result count shown.

### UC3: Date Night
User selects "Date Night" in wizard → events filtered to DATE_NIGHT slot, evergreen filtered to date category.

### UC4: Social Invite (external — social_scan.py)
`social_scan.py` (not deployed) runs weekly: reads CRM data, matches friends to event slots, generates group text drafts. Output consumed externally — not yet integrated into site UI (Track D in roadmap).

### UC5: Ticket Decision
User lands on S/A-tier event: score badge + urgency dot visible in collapsed state. Peek reveals note (Dima's personal take) + urgency tag + buy button. Bottom sheet reveals full scorecard (radar chart) for detailed justification.

### UC6: Spontaneous Activity
User scrolls to Evergreen section: 110+ activities with effort + distance + day filters. No RSVP/tickets required. Dean/parent Harvey ball scores provide instant child-appropriateness signal.

---

## 9. Internal Mode Features

Unlocked via `?mode=internal`:
- RSVP buttons (in/maybe/pass) in peek state and bottom sheet
- Hero stat: RSVP'd count
- CSS class `internal` on `<html>` element (can gate additional CSS)
- Site is public/shareable without this parameter — no friend names or private data exposed in any public state

---

## 10. Content Workflow (External Scripts)

Not deployed to site. Python scripts (stdlib-only) for enrichment pipeline:
- `export_events.py` — exports EVENTS array to events.json
- `enrich_events.py` — audit/fetch/apply modes for ticket URLs + images
- `expand_concerts.py` — mines venue CSVs and batch JSONs for new candidates
- `social_scan.py` — weekly brief: friend matching to event slots, group text generation
- `fetch_images.py` / `fetch_evergreen_images.py` — og:image downloaders
- `fix_urls.py` / `patch_evergreen_images.py` — patch missing data in data.js

Data source for enrichment: Bandsintown ATL, Resident Advisor ATL, Do404, venue Instagram pages, venue websites.

---

## 11. Roadmap Features (Not Yet Implemented)

### Track B: Communication Intelligence
Goal: auto-update `last_contact_date` from iMessage/calls SQLite. Detect availability signals (travel, busy windows) in message text. Output: `comm_scan_results.json` + `availability_suppressions.json`. Feeds into social_scan.py for suppression logic.

### Track C: CRM Completeness
Goal: expand social activation engine from 55 to 80+ people. Add ATL: yes/no flag. Filter non-ATL friends from same-week event suggestions. Add activity tags for better event-person matching.

### Track D: Site Social Layer (internal mode)
Goal: show "who to invite" panel in event bottom sheet. Display friend group name + member list + pre-drafted copy-paste text. "Add to Calendar" ICS download. Depends on Tracks B+C.

### Track E: Agent-Driven Event Addition
Goal: paste URL or screenshot → Claude parses event → appended to data.js → deployed.

### Track F: Recurring Event Generation
Goal: `recurringRule` field auto-generates all instances (Full Moon Drum Circle, Sol Dance, etc.) rather than hardcoding single instances.

### Track G: Guides Expansion
Current: 1 guide live (strawberry.html). Template established. Next candidates: swimming holes, fall activities, kid hikes, date night neighborhood guide.

### Track H: Weather Integration
Goal: OpenWeatherMap badge on outdoor events within 14 days (clear/rain).
