# ATL Radar — Design Review
**Scope:** Gap analysis vs. best practices for personal event discovery + social weekend planner
**Date:** 2026-04-30
**Inputs:** FUNCTIONAL-REQUIREMENTS.md, PRD.md, HANDOFF.md, web research (Foursquare, Luma, Partiful, Timeleft, AllEvents, RA, Bandsintown, PWA patterns, filter/serendipity research)

---

## Functional Strengths

**Scoring transparency.** The 5-axis radar chart (genreMatch, venueQuality, formatRarity, lineupStrength, valueForMoney) is auditable and honest. Most event apps hide their ranking logic entirely. Showing the chart in the bottom sheet lets Dima see *why* something scored 82 vs 74 — this is a meaningful trust signal and the product's strongest differentiator vs generic aggregators.

**Slot system accuracy.** Mapping events to life contexts (GROUP_NIGHT, DATE_NIGHT, FAMILY_OUT, SOLO_RESET, PAPA_DEAN) rather than generic categories is architecturally correct. It answers the real question ("what's right for *this configuration* of my life right now") rather than a generic category filter. Most event apps don't have this concept at all.

**Three-state progressive disclosure.** Collapsed → Peeked → Full Detail is a well-designed information hierarchy for a dense 40+ item list. The peek state (note + tags + buy button) surfaces exactly the right information for a yes/no decision without requiring a full page transition.

**Personal voice in the note field.** The note field as Dima's genuine editorial take is the soul of the product. "This will be transcendent if the sound system cooperates" vs a generic "great show!" is what makes the decision obvious. This is closer to a trusted friend's recommendation than any algorithmic summary.

**Dual dataset design (Events + Evergreen).** Separating time-bound events from evergreen activities solves a real problem: spontaneous Sunday decisions don't need a curated concert list. The Harvey ball dual-score (Dean/parent) on evergreen activities is a practical and underrated feature.

**Urgency is trustworthy.** `urgent: true` + `urgentNote` is applied sparingly. The scarcity of the signal makes it credible — when the red dot appears, it means something real.

**Internal mode separation.** Using `?mode=internal` to gate RSVP and social features on a public-shareable URL is architecturally clean. No friend data leaks to the public.

---

## Gaps vs Best Practices

### Gap 1: No persistent personal history or feedback loop

**What exists:** RSVP signals (in/maybe/pass) stored in localStorage. No attendance confirmation after the event.

**What best practices show:** Bandsintown's "High Notes 2024" year-end recap demonstrates that tracking *attended* events creates a virtuous feedback loop — users get value from history (what did I actually go to?), and the system gains data to improve future relevance. AllEvents uses "past events" as input for personalized recommendations. Foursquare built their entire early personalization engine on check-in history and loyalty (repeat visit frequency as a ranking signal).

**The gap:** ATL Radar has no concept of "went" vs "interested" vs "passed." A user who RSVPs "in" and attends has no way to mark completion. Over time, there's no growing personal record. The RSVP signal expires when localStorage is cleared. This means scoring cannot improve from actual behavior, and there's no way to surface "events similar to things Dima actually attended."

### Gap 2: ICS / "Add to Calendar" is missing

**What exists:** RSVP buttons (internal mode). No calendar export of any kind.

**What best practices show:** Calendar integration is table-stakes for any event app with intent-to-attend signals. Research on ICS implementation shows that "Add to Calendar" buttons (single-click, platform-specific: Google / Apple / .ics download) dramatically outperform raw ICS file downloads on completion rate. Luma and Partiful both provide single-click calendar add as a core feature. The draft text + ICS combination (already in Track D roadmap) is the correct pattern: one tap copies the invite text, one tap adds to calendar.

**The gap:** An event Dima marks "I'm In" has no path to his calendar without leaving the app and manually creating the event. This is exactly the friction point that causes him to miss things — the site surfaces the event, but doesn't close the loop to his actual schedule.

### Gap 3: Social layer is spec'd but not connected

**What exists:** `social_scan.py` runs weekly externally and generates group text drafts. `FRIEND_SLOTS` constant exists in data.js. The bottom sheet has a placeholder for the social layer (Track D). No in-site UI yet.

**What best practices show:** Timeleft's core insight is that the friction in social coordination isn't finding the event — it's the "who do I text and what do I say" step. Their algorithmic matching (age/personality/interest grouping into 4-6 person tables) + pre-drafted invite copy removes that friction entirely. For ATL Radar's use case, the pattern is simpler: given an event's slots, surface the 2-3 friends from Dima's CRM who match best, and render a copy-paste text. This is Track D, but it's the highest-leverage unbuilt feature for the core use case (UC4: "I need to reach out to [friend]").

**The gap:** The weekly `social_scan.py` output is disconnected from the site. Dima has to run the script separately, read the output, then cross-reference the site. The "who to invite" answer should live *inside the event drawer* where the invite decision happens.

### Gap 4: No serendipity mechanism — filter bubble risk

**What exists:** Wizard filters work by strict AND logic (slot match + vibe match + time window). The category filter chips further narrow. No mechanism to surface unexpected but relevant events outside active filters.

**What best practices show:** Recommender systems research (Kilitcioglu 2018, MDPI Electronics 2025, arxiv 2502.13539) consistently identifies that over-personalized filtering creates "filter bubbles" — users only see what confirms existing taste and miss adjacent discoveries. For Dima specifically, this is already in the PRD as a stated goal (UC3: "at least one novel option Dima hadn't considered appears"). AllEvents added a "serendipity" discovery layer in their 2025 redesign. Foursquare's collaborative filtering specifically accounted for the cold-start problem and "hidden gems" — venues with low check-in counts but high engagement from the few who went.

**The gap:** A user who always selects "music + friends" will never see the outdoor family event they'd love, or the comedy show that would be a perfect date night surprise. There's no "surprise me" or "outside my usual" entry point. The wizard is binary: matches get shown/brightened, non-matches get dimmed. There's no "adjacent discovery" mode.

### Gap 5: Score is static — no time-decay or contextual adjustment

**What exists:** `score` is a hand-scored static field per event, set at curation time and never updated. Tier thresholds are fixed.

**What best practices show:** Foursquare's venue rating system evolved away from raw popularity metrics to account for recency and context. Urgency signals already exist on ATL Radar (`urgent`, `urgentNote`) but are binary and manual. A show that's now 72 hours away with 20 tickets left is functionally more urgent than it was 3 weeks ago at the same static score — but the score doesn't change. Similarly, a recurring event that Dima has already attended 3 times this year has lower personal utility than a new one.

**The gap:** Score is editorial, not temporal. Two events with score 78 look identical in the list — the one happening tomorrow vs. the one happening in 6 weeks get the same visual weight. Proximity-to-event-date isn't factored into display priority beyond manual `urgent: true` flags.

### Gap 6: No PWA / installability — mobile-first site without homescreen presence

**What exists:** Static Vercel deploy. Dark theme optimized for phone use. No service worker, no manifest.json, no offline capability.

**What best practices show:** For a site Dima checks "every Friday morning on the couch on his phone," homescreen installability (PWA Add to Home Screen) removes the URL-navigation step. Service worker + cache-first strategy for static assets means the site loads instantly even on poor cell connections. The data layer (`data.js`) is static and could be cached aggressively. MDN and PWA best practice guides recommend cache-first for static assets + stale-while-revalidate for data that refreshes periodically.

**The gap:** The site has to be navigated to via browser every time. On a phone, this means opening Safari/Chrome → typing URL or finding bookmark → waiting for load. A homescreen icon with instant cached load reduces friction on the "Friday morning couch check" use case specifically.

### Gap 7: Evergreen discovery doesn't integrate with wizard results bar

**What exists:** Wizard results bar shows "N events, M evergreen — See results ↓." Wizard filters dim evergreen cards. Evergreen has its own 4-dimension filter system.

**What best practices show:** The best event + activity apps (AllEvents, Foursquare City Guide) unify time-bound and evergreen content in a single ranked feed when context is given. When Dima selects "Solo + Outdoor + Now," the results bar should surface both the 2 upcoming outdoor events *and* the 8 evergreen outdoor solo activities ranked by dean/parent score, all in one list rather than requiring section-jumping.

**The gap:** Wizard results live in the Events section; Evergreen is a separate scrollable section. The sticky results bar creates an affordance ("See results ↓") that takes the user to Events only. A user looking for a spontaneous Sunday activity needs to mentally track two separate filtered lists.

---

## Top 5 Recommendations

### Rec 1: In-drawer "Add to Calendar" button (ICS generation)

**What it is:** A client-side ICS file generator that creates a calendar event from the EVENTS object and triggers a download or opens Google Calendar "add event" URL. Shown in the bottom sheet alongside the "Buy Tickets" button.

**Why it matters for Dima:** The gap between "I'm In" and "it's actually on my calendar" is where events fall through. ADHD operating model means external systems (calendar = schedule reality) must close the loop. If the event isn't on the calendar, it doesn't exist. The site surfaces the event; the calendar commit makes it real.

**How it works:**
- Client-side function `generateICS(ev)` builds a VCALENDAR string from `ev.date`, `ev.time`, `ev.title`, `ev.venue`, `ev.address`, `ev.ticketUrl`
- `data:text/calendar;charset=utf8,...` URL triggers download on click
- Also render a "Add to Google Calendar" link (gcal.com/calendar/r/eventedit?text=...&dates=...&location=... URL pattern) as alternate
- Both options shown in bottom sheet: `[📅 Add to Calendar ▾]` → dropdown with "Download .ics" and "Google Calendar"
- Triggered alongside or replacing the manual "I'm In" RSVP flow in internal mode

**Scope:** ~2 hours. Pure client-side JS. One function + 2 buttons in `buildBottomSheetHTML`. No backend needed.

---

### Rec 2: "Attended" post-event state + personal history

**What it is:** A fourth RSVP state — `attended` — that Dima sets after the event. Stored in localStorage. Hero stat shows "attended" count. Eventually feeds a "History" section showing past events with notes.

**Why it matters for Dima:** Two benefits:
1. Streak tracking (weeks with at least one event attended) is a stated success metric in the PRD (Section 14) — this makes it measurable.
2. A growing "attended" log is the data foundation for future scoring refinements (e.g., "you went to 3 Drumcode shows — formatRarity should be lower for you personally").

**How it works:**
- Add `attended` to the RSVP state machine alongside in/maybe/pass
- Show `attended` state only on events where `ev.date < SITE_TODAY` (past events) OR on events where `rsvp = 'in'` (promoting from intent to confirmation)
- Store as `rsvp_${id}: 'attended'` in localStorage (same key)
- Hero stat: add "N attended" counter
- Optional: add a collapsed "Past Events" section (internal mode only) listing attended events in reverse chronological order with score and note

**Scope:** ~3 hours. RSVP state machine extension + hero stat update + optional past-events section.

---

### Rec 3: "Surprise Me" discovery mode — serendipity entry point

**What it is:** A button in the wizard or standalone CTA that selects one high-quality event *outside* the user's currently active filters — surfacing something adjacent to usual taste that Dima might overlook.

**Why it matters for Dima:** The PRD calls out "at least one novel option Dima hadn't considered" as a UC3 success criterion. The wizard filters currently narrow; there's no mechanism for adjacent discovery. Dima's stated life goal is "resisting default-to-couch entropy" — this directly serves that by removing the "I can't think of anything" paralysis.

**How it works:**
- Algorithm: from EVENTS where `date >= today AND score >= 70 AND NOT currently matching wizard filters`, sort by score desc, return the top 1-3
- Surface as a separate strip below the wizard preview: "Outside your filter — you might like:"
- Use a distinct visual treatment (e.g., dashed border, "🎲 Discovery Pick" badge)
- The strip only appears when a wizard filter is active and at least one non-matching event scores 70+
- On click: opens that event's peek state and scrolls to it

**Scope:** ~2 hours. One filter function + one rendering strip. No data changes needed.

---

### Rec 4: Site social layer — "who to invite" in event bottom sheet (complete Track D)

**What it is:** In internal mode, after the RSVP section in the bottom sheet, render a "Invite" panel that shows: the relevant friend group for this event's slots, a pre-drafted copy-paste SMS text, and the Add to Calendar button for forwarding.

**Why it matters for Dima:** This is the highest-leverage unbuilt feature. The entire social scan workflow (`social_scan.py`) currently requires: running the script → reading terminal output → cross-referencing the site → drafting a text manually. Collapsing that into the event drawer makes the action happen in one place. This is UC4 ("I need to reach out to [friend]") fully closed in the product.

**How it works:**
- `FRIEND_SLOTS` constant already exists in data.js (not confirmed if populated)
- `generateDraftText(ev)` already in app.js scope per HANDOFF Track D spec
- In `buildBottomSheetHTML`, after rsvpSection, add:
  ```
  [Group: Concert Squad — Arjun, Davis, Craig]
  "Hey, Patrick Topping is May 15 at District. You in?"
  [Copy Text] [Add to Calendar →]
  ```
- Friend names only appear when `INTERNAL = true`; no leakage to public view
- Draft text generated from `ev.title`, `ev.dateStr`, `ev.venue`, `ev.time` + a template per slot type
- Matches friends to events by comparing `ev.slots` to each friend's `preferred_slots` in FRIEND_SLOTS

**Scope:** ~4-6 hours for the UI layer (dependent on FRIEND_SLOTS being populated from social_scan.py output).

---

### Rec 5: PWA manifest + service worker — homescreen installability

**What it is:** Add `manifest.json` + a minimal service worker to make ATL Radar installable to Dima's phone homescreen with cache-first asset loading.

**Why it matters for Dima:** The primary use mode is "Friday morning on his phone." Removing the browser-URL step makes this a homescreen tap instead of a search/type. Cached assets mean the site loads in under 1 second even on poor LTE. For a dark-theme app used at night on the couch, the full-screen PWA mode (no browser chrome) also improves the experience.

**How it works:**
- `manifest.json`: name, short_name, start_url, display: standalone, background_color, theme_color, icons (generate 192px and 512px from existing site assets)
- `<link rel="manifest">` in index.html `<head>`
- `sw.js`: minimal service worker with cache-first strategy for `style.css`, `app.js`, `data.js`, `index.html`, `images/` directory; network-first for everything else
- `navigator.serviceWorker.register('/sw.js')` at bottom of index.html
- iOS "Add to Home Screen" prompt: manual (iOS doesn't support install prompt), but `apple-mobile-web-app-capable` meta tag enables full-screen mode

**Scope:** ~3 hours. Two new files (manifest.json, sw.js) + 3 lines in index.html. Vercel serves static files natively.

---

## Quick Wins

These can each be done in under 60 minutes of coding:

**QW1: "Add to Google Calendar" link in bottom sheet.** Generate a gcal URL from `ev.date`, `ev.time`, `ev.title`, `ev.venue`, `ev.ticketUrl`. One anchor tag in `buildBottomSheetHTML`. No backend. No service worker needed. ~20 minutes.

**QW2: Auto-advance urgent events to top of date sort.** Within the same date, sort urgent events before non-urgent. One line change in the sort comparator in `applyEventFilters()`. Makes `urgent: true` events surface on their date even if three events share the date. ~10 minutes.

**QW3: Recurring event badge with "next occurrence" note.** Events marked `recurring: true` currently show a "↺ Recurring" tag but no context. Add `recurringNote` as a tooltip or small line under the tag in peek state. Already a field in the data model, just not fully surfaced. ~20 minutes.

**QW4: Score delta tag for events with >2 S/A tier radar outliers.** If any axis in `scoreReasoning` is 90+, show a small "★ [Axis Name]" tag on the peek row (e.g., "★ Genre Match"). Surfaces the standout reason without requiring the radar chart. One pass over `scoreReasoning` keys in `renderEventCard`. ~30 minutes.

**QW5: "Copy event details" share action with ticket URL included.** Current share button copies "Title — Date @ Venue" without the ticket URL. Adding the `ticketUrl` to the clipboard payload means Dima can text it directly with the buy link. One-line change in `buildBottomSheetHTML` shareText variable. ~5 minutes.

**QW6: Hero stat — S+A tier count becomes a filter shortcut.** Make the "N S+A tier" hero stat card clickable — clicking it activates the tier filter to show only S+A events. Same pattern as calendar pill → jumpToEvent. ~30 minutes.

---

## References

| Pattern / Tool | Source | Applied To |
|----------------|---------|------------|
| ICS "Add to Calendar" button vs .ics download — single-click completion rate advantage | AddEvent blog, addevent.com/blog | Rec 1 |
| gcal URL pattern for calendar add | add-to-calendar-pro.com | Rec 1 |
| Attendance tracking as feedback loop foundation | Bandsintown High Notes 2024 recap, company.bandsintown.com | Rec 2 |
| Streak tracking as engagement + motivation signal | PRD Section 14 self-identified metric | Rec 2 |
| Serendipity vs. filter bubble in recommender systems | Kilitcioglu, dorukkilitcioglu.com/2018; MDPI Electronics 2025, mdpi.com/2079-9292/14/4/821; arxiv 2502.13539 | Rec 3 |
| AllEvents 2025 "serendipity discovery layer" redesign | allevents.in/blog/allevents-launches-new-personalized-homepage | Rec 3 |
| Foursquare "hidden gems" cold-start accounting | Foursquare engineering blog, medium.com/foursquare-direct/building-a-recommendation-engine | Rec 3 |
| Timeleft — friction in social coordination is "who do I text" not "what's the event" | Timeleft algorithm blog, timeleft.com/blog/2023/11/10/timeleft-algorithm | Rec 4 |
| Pre-drafted invite text as conversion mechanism | Partiful + Luma invite flow patterns, lemonvite.com/blog/partiful-vs-luma-vs-lemonvite | Rec 4 |
| PWA cache-first strategy for static assets | MDN PWA caching guide, developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Caching | Rec 5 |
| PWA homescreen installability for habitual-access apps | Progressier, progressier.com/pwa-capabilities | Rec 5 |
| Foursquare social proof — "which friends went" as ranking signal | Foursquare eng blog, medium.com/foursquare-direct/building-a-recommendation-engine | Gap 3 |
| Calendar integration as "closing the loop" between interest and commitment | General pattern — Luma, Partiful, all event RSVP platforms | Gap 2 |
| Urgency notification patterns — "get ready" → "now live" → "window closing" | ticketsdata.com/blog/ticket-event-alerts | QW2 |
