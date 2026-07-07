# ATL Radar — Product Requirements Document & Design Brief
**Owner:** Dima Perkis | **Last updated:** 2026-04-25 | **Version:** Current (post-V4)
**Live:** atlradar.vercel.app | **Repo:** github.com/WhatWouldDimaDo/atl-events

---

## 1. Product Vision

ATL Radar is a **personal Atlanta event intelligence layer** — not a generic event aggregator, but a highly curated, opinionated system built around one user's taste, social graph, and life constraints.

The core problem it solves: **Dima misses things.** Good shows, family-appropriate events, rare experiences — all lost to ambient noise, decision fatigue, and the friction of coordinating a busy schedule with kids + partner. ATL Radar eliminates that friction end-to-end: find the event → understand its fit → draft the text → buy the ticket.

**What it is NOT:**
- A public-facing event directory (Eventbrite/Bandsintown already exist)
- A social platform (no user accounts, no comments, no public profiles)
- A fully automated scraper (human curation is a feature, not a bug)

---

## 2. Primary User

**Dima Perkis, 37 — VP Data & Analytics, Atlanta**

### Life Context
- Married (Jeannie), two kids: Dean (~4yo) and Ruby (~newborn)
- **Life season:** Integration + Endurance — actively resisting default-to-couch entropy
- **Core tension:** High appetite for experiences + real capacity constraints (toddler schedule, new baby, demanding VP role)
- **Social energy:** Explorer/Bridge — loves meeting strangers, kinetic social situations, music, outdoor activity, dancing
- **ADHD operating model:** Needs external systems to surface options; decision fatigue kills follow-through. The site replaces "I should look into that" with "here's what, when, and who to text"

### Atlanta Context
- Lives in Virginia-Highland (30306 zip), 15 min from most ITP venues
- Membership: Fernbank Museum (family), Atlanta Botanical Garden
- Regular: Full Moon Drum Circle, Sol Dance, Critical Mass, Five Rhythms, High Museum Second Sundays
- Music taste: Electronic (techno, house, Afrobeats, ambient), indie rock, some hip-hop. Strongly avoids country, generic pop, jam bands
- Family activities: prefers structured kid activities with adult experiences nearby (not pure kiddie zones)

### Use Modes
| Mode | Context | Frequency |
|------|---------|-----------|
| **Weekend scan** | Friday morning — "what's good this weekend?" | Weekly |
| **Ticket-buy decision** | S/A-tier shows with advance purchase pressure | As events appear |
| **Social planning** | "Who should I text? What's a good excuse to reach out?" | 1-2x/week |
| **Date night discovery** | What can Dima + Jeannie do without kids? | Monthly |
| **Family outing** | What works with Dean (and sometimes Ruby)? | Weekly |
| **Spontaneous Sunday** | It's 10am, what can we do today? | Irregular |

---

## 3. Core Use Cases (ordered by frequency)

### UC1: "What's good this weekend?"
User lands on the site, wants to see relevant events for the next 2-3 days. Filters may be used but should not be required. The default sort (by date) should surface upcoming events prominently.

**Success:** User finds 1-2 events worth acting on within 60 seconds without using filters.

### UC2: "What should I do with Dean?"
User selects "With Dean" in the wizard → sees family-appropriate events + evergreen activities scored for a 4yo. Critical that age restrictions (21+) are filtered out.

**Success:** 3+ actionable options appear, at least one within 20 min of 30306.

### UC3: "What's a good date night?"
User selects "Date Night" → sees indoor/outdoor options appropriate for Dima + Jeannie without kids. Should feel exciting, not generic.

**Success:** At least one novel option Dima hadn't considered appears.

### UC4: "I need to reach out to [friend]"
User wants an excuse to reconnect with someone overdue. The social scan (external script) provides suggestions; the site provides event context that makes the invitation concrete.

**Success:** User has a copy-paste text draft + knows which event to invite them to.

### UC5: "Should I buy this ticket?"
User lands on an S/A-tier event card, wants to understand the score, check urgency, see ticket link. The scorecard (radar chart) + note should make the decision obvious.

**Success:** User either buys from the ticket link or consciously decides to pass.

### UC6: "What can we do right now?"
User scrolls the Evergreen section — low-commitment, repeatable activities. No RSVP, no tickets, open whenever. Good for impromptu Sunday decisions.

**Success:** User picks something and just goes.

---

## 4. Information Architecture

```
ATL Radar
├── Hero (stats: events upcoming, evergreen count, S+A-tier count, RSVP'd)
├── Wizard (when/who/vibe filter — collapsible on mobile)
│   └── Preview strip (top matches for active filter)
├── Events (curated upcoming events)
│   ├── Filter bar (category chips + tier chips + sort)
│   ├── Event rows (accordion list)
│   │   ├── Collapsed: thumb + title + date·venue + score badge + chevron
│   │   ├── Peeked: tags + note + buy btn + "Full Details →"
│   │   └── Full detail: bottom sheet (image, lineup, radar, YouTube, RSVP, share)
│   └── Show more (if filtered list is long)
├── Calendar (mini month widget with event dots)
├── Map (Leaflet, events + evergreen, filterable by category)
├── Evergreen (repeatable Atlanta activities)
│   ├── Filter bar (category, time of day, day, availability)
│   └── Activity cards (expandable)
├── Guides (curated deep-dives — e.g., Strawberry Picking)
│   └── /strawberry.html (full guide with farms, logistics, timeline, cost)
└── About / Taste Profile
```

---

## 5. Event Data Model

### EVENTS array — full field schema
```js
{
  id: Number,                    // unique int, sequential
  date: 'YYYY-MM-DD',            // primary date
  dateEnd: 'YYYY-MM-DD',         // multi-day events (optional)
  dateStr: 'Day Mon D',          // display string: "Sat May 3"
  title: 'String',               // event/show name
  subtitle: 'String',            // supporting act or tagline (optional)
  venue: 'String',               // venue name
  address: 'String',             // full street address
  lat: Number, lng: Number,      // for map pins
  score: Number,                 // 0-100 composite score
  tier: 'S'|'A'|'B'|'C',        // S≥90, A≥75, B≥60, C<60
  slots: ['SLOT_TYPE'],          // see Slot System below
  category: 'music'|'family'|'comedy'|'outdoor'|'social'|'date'|'group',
  genres: ['String'],            // up to 4 genre tags
  environment: 'outdoor'|'indoor',
  eventType: 'String',           // concert, festival, workshop, etc.
  age: 'All ages'|'18+'|'21+',
  time: 'HH:MM AM/PM',           // start time
  timeSlot: 'morning'|'afternoon'|'evening'|'night',
  distance: 'ITP'|'OTP-near'|'OTP-far'|'road-trip',
  urgent: Boolean,               // show ⚡ badge + appear in urgent section
  urgentNote: 'String',          // why urgent: "on sale May 1", "selling fast"
  ticketUrl: 'https://...',      // direct buy link (priority: Ticketmaster → AXS → venue)
  free: Boolean,
  membershipIncluded: Boolean,   // if Fernbank/ABG membership covers entry
  membershipVenue: 'String',
  advancePurchase: Boolean,      // true = don't wait
  lineup: ['String'],            // ordered artist list
  setTimes: 'HH:MM · HH:MM',    // parallel to lineup, optional
  youtubeId: 'String',           // YouTube embed ID for watch preview
  imageUrl: 'String',            // local path: 'images/filename.jpg' or https://
  officialUrl: 'https://...',    // event/venue page
  instagramUrl: 'https://...',   // Instagram event/venue post
  note: 'String',                // Dima's personal take on the event
  scoreReasoning: {              // axes for radar chart
    genreMatch: 0-100,
    venueQuality: 0-100,
    formatRarity: 0-100,
    lineupStrength: 0-100,
    valueForMoney: 0-100
  },
  recurring: Boolean,
  recurringNote: 'String',       // "Every last Friday" etc.
}
```

### Slot System (maps events to life contexts)
| Slot | Meaning | Wizard filter |
|------|---------|---------------|
| `GROUP_NIGHT` | Friends group outing | Who: Friends |
| `DATE_NIGHT` | Dima + Jeannie, no kids | Who: Date |
| `FAMILY_OUT` | Kids welcome, all ages | Who: With Dean / Family |
| `SOLO_RESET` | Solo exploration, Dima alone | Who: Solo |
| `PAPA_DEAN` | Specifically great for Dean (4yo) | Who: Papa + Dean |

### Scoring Axes
- **Genre Match** (0-100): How well does this map to Dima's documented taste profile?
- **Venue Quality** (0-100): Is this a great room for this type of show? (Terminal West = 90, random bar = 50)
- **Format Rarity** (0-100): How often does something like this come to ATL? (one-off UK artist = 90, local weekly = 30)
- **Lineup Strength** (0-100): Artist quality, known headliners, supporting cast
- **Value for Money** (0-100): Free events score high; $100+ tickets need strong lineup to justify

**Tier thresholds:** S ≥ 90 · A 75-89 · B 60-74 · C < 60

### EVERGREEN array — activity schema
```js
{
  id: 'eXXX',                    // string ID: e001–e140
  name: 'String',
  description: 'String',        // 1-2 sentence pitch
  category: 'family'|'solo'|'date'|'group'|'papa',
  environment: 'outdoor'|'indoor'|'both',
  effort: 'low'|'medium'|'high',
  timeOfDay: 'morning'|'afternoon'|'evening'|'anytime',
  bestDays: 'weekdays'|'weekends'|'any',
  availability: 'year-round'|'seasonal'|'scheduled',
  availabilityNote: 'String',    // "Strawberries mid-Apr to mid-May"
  address: 'String',
  lat: Number, lng: Number,
  url: 'https://...',
  imageUrl: 'String',
  cost: 'String',               // "$15/person", "Free", "$5-20"
  free: Boolean,
  membershipIncluded: Boolean,
  membershipVenue: 'String',
  deanScore: 1-5,               // Harvey ball score: how good for Dean
  parentScore: 1-5,             // Harvey ball score: how good for parents
  notes: 'String',              // logistics, tips, insider notes
  emoji: 'String',              // single emoji for card
  distance: 'ITP'|'OTP'|'road-trip',
}
```

---

## 6. Design System

### Visual Identity
- **Dark theme only.** No light mode. The site is used at night, on phones, often in dark environments.
- **Background:** Near-black `#0D0D19` — not pure black, has a faint blue-purple cast
- **Card surface:** `#12121E` with `#1A1A2E` for secondary surfaces
- **Borders:** 5-8% white opacity — subtle, not harsh

### Color System
| Role | Hex | Usage |
|------|-----|-------|
| `--teal` | `#14B8A6` | Music events, primary accent, B-tier |
| `--amber` | `#F59E0B` | S-tier, family events, warning/urgent adjacent |
| `--purple` | `#8B5CF6` | A-tier, date/group events, interactive elements |
| `--green` | `#10B981` | Outdoor events, free badge, evergreen pins |
| `--red` | `#EF4444` | Urgent/act-now, urgent dot |
| `--pink` | `#F472B6` | Date night category |
| `--blue` | `#60A5FA` | Social/community category |

### Category Left-Border System
Each event card has a 3px left border colored by category:
- Music → teal · Family → amber · Comedy → purple · Outdoor → green · Social → blue · Date → pink

### Typography
- **Headlines:** system-ui, heavy weight (800), large tracking on section labels
- **Event titles:** 700 weight, 14px in row view
- **Meta/tags:** 11-12px, light weight, dimmed color
- **Body text (notes):** 13px, 1.55-1.6 line-height, `--text-muted` color

### Tier Visual Encoding (score badges)
- S-tier: amber background tint + amber text
- A-tier: purple background tint + purple text
- B-tier: teal background tint + teal text
- C-tier: gray background tint + dim text

---

## 7. Interaction Model

### Event Row (current design — post-V4)

**Three states per event:**

```
COLLAPSED (default)
┌────────────────────────────────────────────────────────┐
│ [44px thumb] Title — Subtitle          Date · Venue  [score ›] │
└────────────────────────────────────────────────────────┘

PEEKED (after single click on row)
┌────────────────────────────────────────────────────────┐
│ [44px thumb] Title — Subtitle          Date · Venue  [score ▾] │
├────────────────────────────────────────────────────────┤
│         [tags: ⚡ Act Now] [💸 Free] [🌿 Outdoor] ...         │
│         Note text here, up to 3 lines max...                    │
│         [Buy Tickets →]  [Full Details →]                       │
└────────────────────────────────────────────────────────┘

FULL DETAIL (bottom sheet — opens on "Full Details →")
Full-screen slide-up overlay with:
- Hero image
- Title, category badge, date pill, venue
- Tags row
- Buy Tickets + Share buttons
- Note (full text)
- RSVP buttons (internal only)
- YouTube embed (lazy-loaded)
- Lineup with set times
- Radar chart (score breakdown)
- Links (official, Instagram)
```

**Rationale for this model:**
- Collapsed rows allow scanning all 40+ events on one page without overwhelming
- Peek layer surfaces just enough to make a yes/no decision (note + tags + buy)
- Full detail (bottom sheet) is for when you've decided "I want to know more" — not the default path

### Wizard (smart pre-filter)

Three axes, each single-select, independent:
- **When:** Now (3 days) · This Weekend · Next 30 Days
- **Who:** Solo · With Dean · Date Night · Friends · Papa + Dean · Family
- **Vibe:** Music · Outdoor · Indoor · Chill · Food

Active filters show a results bar: "6 events, 23 evergreen — See results ↓"
Wizard preview strip shows top 12 matching events as horizontally scrollable mini-cards.

On mobile, wizard is collapsed behind a "🎯 Filter Events" toggle button to not eat screen space.

### Calendar Widget
- Single-month view, navigate ±4 months
- Event dots on dates with events (colored by tier)
- Clicking a pill: smooth-scrolls to event, opens peek, flashes card
- Wizard filter dims non-matching pills

### Map (Leaflet)
- Dark base tile (CartoDB Dark)
- Colored dots by category (no image markers — too heavy)
- Events + Evergreen layers, toggleable
- Category filter row
- Map legend bottom-right (category → color)
- Map FAB button on mobile (smooth-scrolls to map, hides when map in viewport)

---

## 8. Mobile-First Decisions

### Principles
1. **Show value immediately.** Events should be visible without scrolling more than one screen from page load.
2. **Never obstruct.** The hero section and filter wizard should compress on mobile, not dominate.
3. **Touch-first interactions.** All interactive elements ≥44px touch targets.
4. **Bottom sheet for detail.** On mobile, full detail slides up from bottom (native feel). Not a new page, not a modal.

### Specific implementations
- **Hero:** `min-height: 0` on mobile — compact, no full-viewport art.
- **Wizard:** Hidden behind a toggle button (`🎯 Filter Events`) by default on mobile.
- **Event list:** Vertical accordion rows on all breakpoints (phone, tablet, desktop).
- **Bottom sheet:** Swipe-down-to-close (>100px drag on handle), backdrop tap, ESC key.
- **Filter chips:** Horizontal scroll (`overflow-x: auto`, no scrollbar visible).
- **Nav:** Becomes a bottom tab bar on mobile with emoji shortcuts.

---

## 9. Current Feature Inventory

### Shipping (live at atlradar.vercel.app)
| Feature | Status | Notes |
|---------|--------|-------|
| Event list (accordion rows) | ✅ | Post-V4, replaced horizontal scroll |
| Wizard filter | ✅ | When/Who/Vibe, collapsible mobile |
| Wizard preview strip | ✅ | Top 12 matches, horizontal scroll |
| Category + tier filter chips | ✅ | |
| Date/score sort | ✅ | |
| Calendar widget | ✅ | With event pills, nav, highlight |
| Leaflet map | ✅ | Events + evergreen, category filter |
| Evergreen grid | ✅ | 110+ activities, fully filtered |
| Universal search (⌘K) | ✅ | Events + evergreen, keyboard nav |
| Bottom sheet (mobile detail) | ✅ | Swipe dismiss, full rich content |
| Radar chart (score breakdown) | ✅ | Per-event, 5 axes, Chart.js |
| YouTube embed (lazy) | ✅ | Click-to-load, in bottom sheet |
| RSVP signals (localStorage) | ✅ | Internal mode only |
| Internal mode (?mode=internal) | ✅ | RSVP + planning features |
| Hero stats (live counts) | ✅ | Events, evergreen, S+A, RSVP'd |
| Image fallback chain | ✅ | Local → YouTube thumb → cat poster |
| Urgent event badges | ✅ | ⚡ tag + red dot |
| Sticky wizard results bar | ✅ | IntersectionObserver |
| Back-to-top button | ✅ | |
| Map FAB (mobile) | ✅ | Scrolls to map |
| Guides section | ✅ | /guides.html with cards |
| Strawberry picking guide | ✅ | /strawberry.html, full deep-dive |

### Data (as of V4)
| Dataset | Count | Coverage |
|---------|-------|----------|
| Curated events | 51 | Apr 2026 – Oct 2026 |
| Events with ticket URL | 46/51 (90%) | |
| Events with image | 48/51 (94%) | |
| Evergreen activities | 110 | Year-round + seasonal |
| Evergreen with image | 110/110 (100%) | |

---

## 10. Deferred Features (Roadmap)

### Track A: Event Data Quality (ongoing)
- Keep ticket URLs fresh (they expire; urgent items especially)
- Sosa image (RA blocks scraping — manual download)
- Pedro Sampaio ticket URL
- Monthly venue monitoring per VENUE-REFRESH-GUIDE.md

### Track B: Communication Intelligence
**Goal:** Auto-update `last_contact_date` from iMessage/calls; detect availability signals; suppress unavailable friends from suggestions.

Script: `personal-crm/tools/comm_scan.py`

Data sources:
- `~/Library/Messages/chat.db` (iMessage SQLite, nanosecond epoch)
- `~/Library/Application Support/CallHistoryDB/CallHistory.storedata` (calls)
- Phone index from social_activation_engine.md (SAE)

Output:
- `comm_scan_results.json` — per-person last_contact from iMessage + calls
- `availability_suppressions.json` — detected unavailability windows

Integration: social_scan.py reads comm_scan_results.json to override stale last_contact dates; filters suppressed friends from suggestions.

Signal patterns to detect:
- "out of town", "traveling", "on vacation" → suppress 7-14 days
- "back on [date]", "free after [date]" → suppress until date
- "let's do [event]", "interested in [event]" → interest signal (boost priority)

### Track C: CRM Completeness
**Goal:** Expand SAE from 55 to 80+ people; add location filtering.

Actions:
1. Regenerate SAE from full 107-person CSV (`crm_groupings_review.csv`)
2. Add ATL: yes/no flag to social_scan.py — only suggest ATL locals for same-week events
3. Import activity tags for better event-person matching
4. Use iMessage enrichment data for actual cadence computation

### Track D: Site Social Layer
**Goal:** Show "who to invite" in event drawers with pre-drafted texts and calendar download.

Files: `data.js` (FRIEND_SLOTS constant), `app.js` (socialLayerHTML, generateDraftText, generateICS)

Depends on: Tracks A+B being correct.

Design:
- In the event bottom sheet (internal mode), after RSVP section:
  ```
  [Invite This Group] 
  ┌────────────────────────────────────────────────────────┐
  │ 🎵 Concert Squad: Arjun, Davis, Craig                  │
  │ "Hey, Sub Focus is May 15 at Underground. You in?"     │
  │ [Copy Text]  [Add to Calendar]                         │
  └────────────────────────────────────────────────────────┘
  ```

### Track E: Agent-Driven Event Addition
**Goal:** Drop a URL or screenshot → Claude parses event details → appended to data.js.

Command pattern:
```
"Add this event: [URL or paste event page text]"
→ Claude extracts: title, date, venue, lineup, ticket URL, score, slots
→ Appends correctly formatted object to EVENTS array
→ Deploys
```

Priority sources: Bandsintown ATL, Resident Advisor ATL, Do404, venue Instagram pages, ATL music blogs.

### Track F: Recurring Event Generation
Current: recurring events are hardcoded as single instances with `recurring: true` and a `recurringNote`.

Target: `recurringRule` field generates all instances automatically:
```js
recurringRule: { freq: 'monthly', dayOfWeek: 0, weekOfMonth: -1 }
// → Last Sunday of every month
```

Priority events: Full Moon Drum Circle, Sol Dance, Five Rhythms, High Museum Second Sundays, Critical Mass.

### Track G: Guides Expansion
Current: 1 guide live (strawberry picking), 2 coming-soon slots.

Guide template established at `/strawberry.html`:
- Hero image + rating badge
- Decision matrix (which venue wins + why)
- Photo gallery grid
- Timeline (departure → arrival → activities → return)
- Comparison table
- Nearby recommendations with Maps links
- Cost breakdown

Next guide candidates:
1. **Outdoor swimming holes** (Bear Creek, Rock Town) — summer seasonal
2. **Fall family activities** (apple picking, corn mazes, pumpkin patches)
3. **Kid-friendly hikes** (Arabia Mountain, Stone Mountain, Kennesaw)
4. **Date night in ATL** (neighborhood guide format — Ponce City, Old Fourth Ward, Inman Park)

### Track H: Weather Integration
For outdoor events within 14 days: pull OpenWeatherMap forecast, show `🌞 Clear · 🌧 Rain` badge on card.

Priority: Shake the Lake, Atlanta Jazz Festival, Shaky Knees, any outdoor event marked `urgent`.

---

## 11. Technical Architecture

### Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS — no framework, no build step |
| Data | `data.js` — EVENTS array + EVERGREEN array, imported via `<script>` |
| Charts | Chart.js (radar) |
| Maps | Leaflet.js + CartoDB Dark tiles |
| Deploy | Vercel CLI (`/opt/homebrew/bin/vercel --prod`) — static site |
| Repo | GitHub (public) — `git push` blocked on main; deploy via Vercel CLI directly |

### File Map
```
/
├── index.html       — Structure, nav, section divs, external scripts
├── app.js           — All interactivity: wizard, filters, calendar, map, drawers, search
├── style.css        — All styles, variables, responsive, component-specific
├── data.js          — EVENTS[] + EVERGREEN[] data arrays
├── guides.html      — Guides landing page
├── strawberry.html  — Strawberry picking guide (self-contained)
├── about.html       — About + taste profile
├── vercel.json      — Cache headers, security headers
└── images/          — Event images (local, loaded in imageUrl field)
    └── evergreen/   — Evergreen activity images
└── scripts/         — Python enrichment scripts (not deployed)
```

### Python Scripts (enrichment pipeline, not shipped)
```
scripts/
├── export_events.py           — data.js → events.json
├── enrich_events.py           — 3-mode: audit / fetch / apply
├── expand_concerts.py         — Mine CSV + batch JSONs for new events
├── social_scan.py             — Social activation engine (weekly brief)
├── fetch_images.py            — stdlib-only og:image + download
├── fetch_evergreen_images.py  — Evergreen og:image + venue logos
├── fix_urls.py                — Patch missing URLs on existing entries
└── patch_evergreen_images.py  — Patch EVERGREEN imageUrl fields
```

### Constraints (non-negotiable)
- **stdlib-only Python** — PEP 668 blocks pip on Python 3.14. No `pip install` in scripts.
- **No friend names in public build** — Site is shareable. All social graph logic lives in `social_scan.py` only.
- **No backend** — No database, no auth, no server. RSVP state in localStorage. Coordination state (if added) via Cloudflare Workers KV.
- **Git push to main blocked** — Use `vercel --prod` for all production deploys.
- **SSL cert disabled in enrichment scripts** — Some ATL event sites have cert issues (squarespace, old wordpress).

---

## 12. Content Strategy

### Curation Principles
- **Quality over quantity.** 50 highly scored events beats 500 mediocre ones.
- **Score honestly.** A B-tier event with a 62 shouldn't pretend to be A-tier. The radar chart makes the scoring auditable.
- **Dima's voice in the note field.** Not a press release — a genuine take. "This will be transcendent if the sound system cooperates" vs "Good if you like the genre."
- **Urgency is real.** Only mark `urgent: true` for events with genuine time pressure (on-sale dates, selling-out shows, one-day-only experiences).

### Event Refresh Cycle
- **Weekly:** Check urgent events for ticket availability
- **Monthly:** Scrape tier-1 venues for new shows (per VENUE-REFRESH-GUIDE.md)
- **Quarterly:** Prune past events, review scoring consistency, update evergreen for seasonal changes

### Scoring Consistency Rules
- Free outdoor events can score high on value but rarely exceed 80 total (format rarity low)
- Recurring events cap at 72 (format rarity penalized — not rare if it happens every month)
- S-tier (90+) is reserved for once-in-ATL-or-rare appearances: major touring acts in intimate venues, singular cultural events
- Venue multiplier: Terminal West/Variety Playhouse add +5-10 vs generic bar venue

---

## 13. Design Brief: Key UX Principles

### 1. Density without overwhelm
Show all events in one scan-able list. Accordion rows let 40+ events fit on a single page without hiding anything. The peek state gives depth on demand without leaving the list.

### 2. Progressive disclosure
Collapsed → Peeked → Full Detail. Each step reveals more only when the user signals interest. This matches how Dima actually browses: skim titles, hover on one or two, go deep on one.

### 3. Smart defaults, zero friction for the base case
Landing without any filters set = all upcoming events by date. No mandatory onboarding, no wizard to complete before seeing content. The wizard is a power-user shortcut, not a gate.

### 4. Personal, not generic
The note field is the product's soul. Generic "must-see concert!" copy is useless. Dima's actual take ("this is the only time Chet Faker has played somewhere this size in years") is what makes the card worth reading.

### 5. Mobile is the primary surface
Dima checks this on his phone, on the couch, at 10pm. Every interaction must work one-handed. Bottom sheet, row taps, filter chips — all touch-first. Desktop is a bonus.

### 6. Urgency surfacing
Red dot + ⚡ tag are rare and trustworthy because they're applied sparingly. If everything is urgent, nothing is. The urgentNote field provides specific context ("on-sale Apr 24 10am") that makes urgency actionable.

### 7. Internal vs external modes
`?mode=internal` unlocks RSVP signals and planning features. Public users never see friend names, private notes, or coordination tools. The site is shareable to anyone in ATL without leaking personal data.

---

## 14. Success Metrics (personal product)

These are subjective but worth tracking:
- **Events attended** that were discovered via ATL Radar (vs. stumbled upon elsewhere)
- **Lead time on ticket purchases** — are urgent flags being caught in time?
- **Outreach generated** from social scan — texts sent using draft templates
- **Streaks** — weeks where at least one event was attended vs. default couch entropy
- **Guide utility** — does the strawberry guide actually reduce trip planning friction?

---

## 15. Anti-Patterns (what to never do)

- **Don't add events to pad the count.** A low-quality C-tier event that Dima would never attend adds noise, not value.
- **Don't score-inflate to make things look better.** The radar chart is visible; inflation is obvious.
- **Don't expose friend names on the public site.** Ever. Not in comments, not in note fields, not in social layer UI.
- **Don't build features for hypothetical future users.** This is a product of one. Every decision is filtered through Dima's actual use patterns.
- **Don't hide events behind required filters.** Discovery works best when the full list is visible by default.
- **Don't let the wizard become a maze.** Three single-select dimensions max. If it takes more than 2 taps to filter, the UX has failed.
- **Don't rebuild what works.** The bottom sheet, radar chart, and scoring system are established and tested. Iterate, don't replace.
