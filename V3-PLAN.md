# ATL Events Site — V3 Architecture Plan
**Drafted:** 2026-04-21
**Based on:** User feedback through sessions 1–3 + Opus agent analysis

---

## V3 Core Premise

V2 is a personal event discovery tool. V3 splits into two versions:
- **Internal (Dima+Jeannie):** Full feature set, friend coordination, RSVP signals, agent-driven updates
- **Public (shareable):** Clean read-only view, no friend names, no private data

This is the biggest architectural decision in V3 — everything else follows from it.

---

## V3 Feature Roadmap

### P0 — Critical (ship next)

**1. Internal vs External version split**
- Build a URL-based toggle: `?mode=internal` unlocks coordination features
- Or: private deployment on a password-protected route
- Public version: everything visible now, minus friend names and private notes
- Internal version: adds coordination layer, agent mode, RSVP signals

**2. Agent-driven data update pipeline**
- Drop a URL or screenshot into Claude → agent parses event details → appends to `EVENTS` array in `data.js`
- Reduce manual data entry to near-zero
- Priority: Bandsintown, Resident Advisor ATL, Do404 event pages
- Format: "Add this event" + paste URL → Claude reads page, generates correct object, appends to data.js

**3. Friend interest/RSVP signaling (Internal only)**
- Per-event tags: "I'm in", "Maybe", "Pass"
- Signals shown on cards without exposing who said what on public version
- Storage: localStorage for now (no backend needed)
- Show: "3 people interested" vs. friend names on public

### P1 — High Value

**4. Thread per event (Internal)**
- Each event card gets a collapsible thread section
- Notes, logistics, links, coordination snippets
- Rendered as a timeline inside the drawer
- Storage: localStorage JSON keyed by event ID

**5. "Which dates are still open, who to reach out to" query mode**
- Natural language query box: "What's a good group night in May that hasn't been planned yet?"
- Cross-references slot type, upcoming events, basic availability logic
- Could be powered by local LLM (Ollama) or Claude API call
- Output: ranked list with "Start planning" button → pre-drafts a message

**6. Real-time ticket availability scraping**
- For S/A-tier shows marked `advancePurchase: true`, check if still available
- Background agent checks Ticketfairy, AXS, etc. every 24h
- Surfaced as a "Last checked" timestamp on the urgent badge
- Could use Firecrawl for scraping

**7. Event image loading (real flyers)**
- Eventbrite, RA, venue Instagram → pull actual event flyers
- Store in `imageUrl` field (already in schema, unused)
- Replace YouTube thumbnails as primary card image for non-music events
- Priority: Disclosure, Sub Focus, Shaky Knees, DWTD+Magic Sword

### P2 — Enhancement

**8. Recurring event generator**
- Sol Dance, Five Rhythms, High Museum Second Sundays, Full Moon Drum Circle
- Currently hardcoded as single instances with `recurring: true`
- V3: generate the full cadence automatically from a `recurringRule` field
- Populate the calendar with all future instances without manual data entry

**9. Weather integration**
- For outdoor events within 2 weeks, pull forecast from OpenWeatherMap
- Show a weather badge on the card (🌞 Clear · 🌧 Rain)
- Priority: Shake the Lake, Atlanta Jazz Festival, Shaky Knees

**10. Distance matrix**
- Current `distance` field is categorical (ITP/OTP/etc.)
- V3: calculate driving time from Virginia-Highland (30306)
- Display "~18 min" instead of "ITP"
- API: Google Maps Distance Matrix or Mapbox

**11. Push/SMS reminders (Internal)**
- For events with `advancePurchase: true` and `urgent: true`
- "Sub Focus is 2 days away and you haven't bought a ticket" type alert
- Delivery: Pushover, or SMS via Twilio

### P3 — Future

**12. Multi-user coordination (requires backend)**
- Shared RSVP state between Dima+Jeannie via a lightweight backend
- Could be: Supabase, PocketBase, or a simple Cloudflare Worker + KV
- Unlocks: shared thread, real-time signals, babysitter reminder logic

**13. Historic archive mode**
- Past events flip to an archive view
- Stats: "14 shows attended in 2026, 8 were S/A-tier"
- Journal-style entry for each attended event

**14. Accessibility pass**
- ARIA labels, keyboard navigation for all interactive elements
- Focus states on drawer expand buttons
- Screen-reader-friendly event cards

---

## V3 Technical Architecture

### Option A: Keep static 4-file (minimal backend)
- Add `?mode=internal` toggle, localStorage for coordination state
- Agent update via Claude Code CLI (not in-browser)
- **Pro:** Zero infrastructure, fast, free to host
- **Con:** No real-time sync between Dima + Jeannie

### Option B: Add lightweight backend
- Cloudflare Workers + KV for RSVP signals and threads
- Still static frontend, but async POST/GET to edge worker
- **Pro:** Enables real-time sync without a full database
- **Con:** More complexity, requires auth layer

### Option C: Next.js app on Vercel
- Full migration to Next.js App Router
- Server components for data fetching, client components for interactivity
- Supabase for coordination state
- **Pro:** Full power, scalable
- **Con:** Significant rebuild, overkill for personal use

**Recommendation:** Start with Option A + localStorage for V3, then migrate to Option B when coordination features are needed.

---

## V3 Data Schema Additions

```js
// EVENTS additions
{
  // ... existing fields ...
  imageUrl: 'https://...', // actual event flyer, fetched by agent
  rsvpSignals: null, // added by coordination layer
  thread: null, // added by internal version
  weatherForecast: null, // auto-populated for outdoor events <14 days
  drivingMinutes: 18, // computed from home location
}
```

---

## Priority Order

| Rank | Feature | Effort | Value |
|---|---|---|---|
| 1 | Agent-driven data update | Medium | Very High |
| 2 | Real event images/flyers | Low | High |
| 3 | Friend RSVP signals (localStorage) | Medium | High |
| 4 | Internal/External split | Low | Medium |
| 5 | Recurring event auto-generation | Low | Medium |
| 6 | Weather badges | Low | Medium |
| 7 | Thread per event | High | Medium |
| 8 | Query mode (natural language) | High | High |
| 9 | Ticket availability scraping | High | High |
| 10 | Backend sync | Very High | Medium |

---

## Next Immediate Step

Before starting V3, the most impactful quick wins:

1. **Agent update pipeline** — teach Claude Code to append new events to `data.js` from a URL drop
2. **Real event flyers** — find actual images for Disclosure, Sub Focus, Shaky Knees
3. **RSVP signals** — localStorage-backed "I'm in / Maybe / Pass" buttons per event
