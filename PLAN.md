# ATL Events Site — Session Plan
**Session:** 2026-04-21 (Round 3)
**Status:** Executing

---

## Overview

This session completed V2 Round 3 changes to the static 4-file ATL Events site deployed at https://atl-events.vercel.app.

---

## Changes Made (Round 3)

### 1. Nav Persistence Fix
**Problem:** Nav bar disappeared on scroll — `position: sticky` was broken by `overflow-x: hidden` on `html` and `body`, which creates a new block formatting context that prevents sticky from working.
**Fix:** Changed `nav { position: sticky; }` → `position: fixed; top: 0; left: 0; right: 0; width: 100%;` and added `body { padding-top: 60px; }`.
**Files:** `style.css` lines ~57, ~44

### 2. Event Card Poster Backgrounds
**Problem:** Events without YouTube IDs showed a plain dark poster (`.ev-img-poster`) with no background color — the gradient CSS existed only for `.ev-img-fallback.cat-*`, not `.ev-img-poster.cat-*`.
**Fix:** Added `.ev-img-poster.cat-music/family/comedy/outdoor/social/date` gradient rules. Also redesigned the poster layout: content now sits at bottom-left (like a real flyer), category emoji floats top-right, gradient overlay ensures readability.
**Files:** `style.css` — EVENT CARD POSTER section

### 3. YouTube Thumbnail Behind Play Button
**Problem:** Drawer "Watch" section showed only a dark placeholder with a play button — no visual context about what would play.
**Fix:** Added `<img class="yt-thumb-bg">` inside `.yt-placeholder`, pulling `hqdefault.jpg` from YouTube's thumbnail CDN. Added CSS: `position: absolute; inset: 0; object-fit: cover; filter: brightness(0.55)`. Play button floats on top via z-index.
**Files:** `app.js` — `ytSection` template in `renderEventCard()`; `style.css` — `.yt-thumb-bg` rule

### 4. Calendar Moved Into Events Section
**Problem:** Calendar was a separate section (`<section id="calendar">`) that felt disconnected from the events grid.
**Fix:** Removed the standalone calendar section and its `<hr>`. Added a compact calendar widget (`#cal-mini`) directly inside the events section container — positioned after the inline search bar, before the filter chips.
**Files:** `index.html` — removed section, added `#cal-mini` widget in events section

### 5. Single-Month Calendar with Prev/Next Navigation
**Problem:** Calendar rendered all months Apr–Sep stacked, making it too long and hard to navigate.
**Fix:** Added `calYear`/`calMonth` state variables. Rewrote `buildCalendar()` to render a single month only. Added `initCalendarNav()` function that wires up `#cal-prev` and `#cal-next` buttons. Month label updates dynamically in the widget header.
**Files:** `app.js` — `buildCalendar()`, `initCalendarNav()`, `let calYear/calMonth`

### 6. Inline Search Bar Restored
**Problem:** The inline grid search input was missing — only the ⌘K modal existed.
**Fix:** Restored `initSearch()` function. Added `<input id="search-input">` inside events section. Input filters the events grid in real time via `searchQuery` state shared with `applyEventFilters()`.
**Files:** `app.js` — `initSearch()`; `index.html` — search input HTML

### 7. Expanded Event Descriptions
**Problem:** 8 key events had only 1–2 sentence notes — insufficient context for decision-making.
**Fix:** Expanded notes for:
- id:1 Patrick Topping — style context, venue fit, urgency
- id:2 Shake the Lake — format, atmosphere, ticket urgency
- id:5 Disclosure LIVE — full band vs DJ, track callouts, venue rationale
- id:6 DWTD + Magic Sword — both acts described, rare format
- id:7 Vintage Culture — sound profile, set length, context
- id:8 Sub Focus 360° — 360° format explained, artist history, support lineup
- id:27 Empire of the Sun — tour/setlist context, group logistics
- id:28 Shaky Knees — day-by-day breakdown, full value proposition
**File:** `data.js`

### 8. Nav Calendar Link Updated
Updated `#calendar` → `#cal-mini` so the nav Calendar link jumps to the new inline widget.
**File:** `index.html`

---

## Architecture (V2 — 4 files)

```
index.html   — HTML structure
data.js      — EVENTS + EVERGREEN data arrays
style.css    — All CSS
app.js       — All JavaScript logic
```

**Deploy:** `/opt/homebrew/bin/vercel --prod` from project dir
**Live:** https://atl-events.vercel.app
**GitHub:** https://github.com/WhatWouldDimaDo/atl-events

---

## Known Remaining Issues / Future Work

- `chartjs-plugin-annotation@3.0` CDN not loaded (referenced in original spec but not currently in use)
- Progress bar z-index may conflict with fixed nav on some browsers — test on mobile
- Calendar prev/next navigation could disable buttons at date boundaries (Apr 2026 / Sep 2026)
- Map Leaflet layer uses CartoDB dark tiles — fallback if CDN is slow
- Consider adding `scroll-margin-top` to `#cal-mini` for more accurate nav jumping
