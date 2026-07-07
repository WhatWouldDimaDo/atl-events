# CRM Best Practices & Social Dashboard Vision
**Owner:** Dima Perkis | **Updated:** 2026-04-30 | **Scope:** Personal CRM — best practices, dashboard design, implementation phases

---

## 1. Best Practices from Comparable Systems

### Clay / Mesh (clay.earth)
**Pattern:** Every channel (iMessage, email, LinkedIn, calendar) contributes a single `last_contacted` date. No manual logging required. Reconnect reminders triggered when that date exceeds the cadence threshold.

**What to steal:** The "single last_contact signal from all channels" approach is exactly what `merge_results()` in `comm_scan.py` does. The gap is that Clay runs continuously and writes back to a live DB — the equivalent here is the scheduled launchd job writing back to `crm_database.json` + the SAE.

**What not to copy:** Clay enriches with LinkedIn/Twitter/social graph data via scraping. Not worth building for a personal-use system. Keep enrichment limited to sources you already have (iMessage, calls, Calendar).

### Dex (getdex.com)
**Pattern:** Daily digest of overdue contacts, surfaced as a text message or push notification. "Pre-meeting brief" — before a scheduled event with someone, auto-generates: when you last talked, what you discussed, what's new with them.

**What to steal:**
1. The daily/weekly push (not pull) model. Don't require Dima to open a dashboard — push the digest to a place he already looks (Obsidian daily note or Slack DM to himself).
2. The "pre-meeting brief" concept: when a social event is added to Google Calendar involving a CRM contact (matched by name in the event title/description), auto-generate a Memory Bank summary. `social_scan.py` draft texts are the equivalent for outbound outreach.

**What not to copy:** Dex is LinkedIn-first. The personal CRM here is iMessage-first, which is correct for Dima's actual communication patterns.

### Monica CRM (monicahq.com)
**Pattern:** Manual interaction logging. Every hangout, call, gift, life event must be entered by hand.

**Lesson:** This fails. The system Dima has is already better than Monica because `comm_scan.py` passively reads from existing channels. The risk of regressing toward Monica-style manual tracking is real — any feature that requires Dima to take a manual step to log an interaction will eventually be skipped.

**Rule derived from this:** Never add a feature that requires a manual log step unless it's a voice note → agent pipeline (already in place). Passive ingestion only.

### Timeleft (timeleft.io)
**Pattern:** Hosts group dinners by matching strangers with compatible interests. Forces social scheduling into a structured weekly cadence.

**What to steal:** The fixed-cadence forcing function. The `social_scan.py` "Top 10 Overdue" table serves this purpose — but it only has impact if it's surfaced weekly without requiring Dima to run it. The launchd schedule is the Timeleft equivalent: enforce cadence structurally, not willpower-dependently.

### Nat Eliason personal CRM pattern
**Key insight:** "A CRM only works if you trust the data. One stale last_contact_date corrupts the entire priority queue." This is the exact failure mode documented in CRM-AUTOMATION-SPEC Section 1 — Arjun showing `2026-03-01` in the JSON while being actively texted in April 2026.

---

## 2. Automation Frequency Recommendations

| Task | Frequency | Mechanism | Why |
|------|-----------|-----------|-----|
| `comm_scan.py --write-crm` | Weekly, Friday 7:00 AM | launchd plist | iMessage/call data is stable enough for weekly granularity. More frequent would add noise without signal. |
| SAE cadence section update | Same run as comm_scan | Called from within comm_scan.py (FR-02) | Must be atomic with CRM writeback or SAE will lag by a run. |
| `weekly_digest.py` | Weekly, Friday 7:05 AM | launchd plist | 5-minute offset ensures comm_scan completes before digest reads `comm_scan_results.json`. |
| `export_events.py` | Same as weekly_digest | Called by weekly_digest.py (already implemented) | events.json should reflect current data.js before social_scan runs. |
| Calendar slot scan | At digest generation time | Called by social_scan.py on each run (FR-06) | Real-time is better than cached here — calendar changes daily. |
| Availability signal scan | Weekly, same run | Add `scan_availability()` call to comm_scan.py | Phase C. 30-day lookback window, 14-day expiry — weekly is fine. |
| Birthday reminders | Daily, morning | Separate lightweight script or added to daily-planner skill | Check `birthday` field against today's date. Fire 7 days before. Only worth doing after birthday normalization (FR-08) is complete. |
| New contact detection | Same as weekly digest | Already in comm_scan output under `new_contacts` | No additional run needed. Surface in digest "New Contact Inbox" section. |

**On-demand (never scheduled):**
- `python3 scripts/comm_scan.py --dry-run` — preview before writing
- `python3 scripts/social_scan.py` — ad-hoc brief before a weekend
- Memory Bank updates — always manual + agent-assisted, never automated

---

## 3. Social Dashboard Design

### What it should show

The dashboard is not a web UI — it's the weekly digest markdown file, which Dima reads in Obsidian. The design principle: **status first, action second**. Show what happened, then show what needs to happen.

**Section order and purpose:**

```
1. Header stats
   CRM: 107 | iMessage matched: N | New contacts: N | Digest date

2. This Week's Contacts          ← What actually happened
   Table: Name | Last Contact | Platform | 90d count
   Source: comm_scan_results.json → people, filtered last_contact >= 7 days ago

3. New Contact Inbox             ← Who you should add
   Table: Name (if resolved) | Handle | Messages 90d | Calls 90d | First Seen
   Source: comm_scan_results.json → new_contacts

4. Manual-Only Contacts          ← Who you're losing track of
   Comma list of names with no trackable handle
   Source: comm_scan_results.json → manual_only_contacts
   Action prompt: "Add iMessage_handle for: [names]"

5. Open Slots This Week          ← NEW: Calendar-derived
   Table: Date | Day | Type | Time window
   e.g.: Sat May 2, FAMILY_OUT, 9 AM–1 PM (Dima has kids, Jeannie getting haircut)
         Sat May 2, GROUP_NIGHT, evening (no conflict)
         Sun May 3, SOLO_RESET, morning

6. Events This Weekend           ← Slot-matched events (current social_scan output)
   Grouped by slot type. Only show events that match an open slot from section 5.

7. Overdue Outreach              ← Who needs a text
   Tier-1 table first, then Tier-2. Computed by social_scan.py. Already exists.

8. Availability Flags            ← Phase C placeholder now; real data in Phase C
   People whose iMessage content signals travel or availability

9. Draft Texts                   ← Ready to send
   Group texts + individual outreach. Already generated by social_scan.py.

10. Birthday Alerts              ← After FR-08 normalization
    Anyone with birthday within next 14 days.
```

### How it flows

```
Friday 7:00 AM
  └── launchd → comm_scan.py --write-crm
        → updates crm_database.json (last_contact_date, contact_count_90d)
        → updates SAE ## Cadence Targets (last: dates)
        → writes comm_scan_results.json
        → writes comm_scan_log_YYYY-MM-DD.json

Friday 7:05 AM
  └── launchd → weekly_digest.py
        → reads comm_scan_results.json (sections 2–4)
        → calls export_events.py (refresh events.json)
        → calls social_scan.py (reads SAE with fresh dates → sections 5–9)
        → assembles digest
        → writes ~/Documents/Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md

Friday morning (Dima opens Obsidian)
  └── reads digest → sends texts → makes plans
```

### Key design decisions

**Why calendar slot computation belongs in social_scan.py, not weekly_digest.py:** `social_scan.py` already knows slot types and event matching logic. The slot-detection function should sit there as `compute_open_slots(cal_events, today)` and the output should gate which events get surfaced. `weekly_digest.py` is just the orchestrator — it should not have slot logic.

**Why "This Week's Contacts" shows platform:** `imessage` vs `call` vs `in_person` matters. A phone call to someone is qualitatively different from a text. Dima can see at a glance that he talked to someone substantively vs. just texted.

**Why the digest goes to `02_Areas/Friends/`, not `07_Daily/` or a planning note:** It's a social-specific artifact, not a planning artifact. Keeping it in `02_Areas/Friends/` means it's findable next to Memory Banks and the CRM JSON files. The weekly planning note (`02_Areas/Planning/Weekly/`) can link to it, but the digest lives in Friends.

**Why no web UI:** The digest is read once a week in a context Dima already uses (Obsidian). A separate web dashboard adds a navigation step with no benefit. The `atl-events.vercel.app` site is for event discovery — keep it separate.

---

## 4. Gap Analysis: Current `weekly_digest.py` Output vs. Ideal Dashboard

| Section | Current state | Gap |
|---------|--------------|-----|
| This Week's Contacts | Implemented in `build_this_week_section()` | Only shows contacts from `comm_scan_results.json`. In-person contacts with no phone (Rich, Charles, Hadi) never appear here even if Dima saw them. |
| New Contact Inbox | Implemented in `build_new_contacts_section()` | Works correctly. Name enrichment from AddressBook is in place. Gap: no prompt to add `iMessage_handle` for phone-less contacts vs. full CRM entries. |
| Manual-Only Contacts | Implemented in `build_manual_only_section()` | Good. Needs a sharper action prompt: not just listing names, but linking to the add-contact workflow. |
| Open Slots This Week | Missing entirely | `social_scan.py` never reads Google Calendar. Slot suggestions are made with no awareness of Dima's schedule. As of Apr 30, Dima has a dense work week (Mon–Fri Lahzo meetings) with open evenings and a free weekend. The digest would suggest GROUP_NIGHT events on weeknights where Dima actually has early morning calls the next day. |
| Events This Weekend | Implemented via `social_scan.py` | Good coverage. Gap: no slot gating. Also: `SOLO_RESET` events rendered without friend matching — correct, but there's no "time to yourself" context (e.g., "Sat May 2 morning you have the kids solo"). |
| Overdue Outreach | Implemented in `generate_brief()` "Top 10 Overdue" section | Works but uses SAE `last:` dates, which are stale (SAE was generated 2026-04-21 and never refreshed). Gap: Tier separation in the table is missing — all 10 shown together, not Tier-1 first then Tier-2. |
| Availability Flags | Placeholder in CRM-AUTOMATION-SPEC Section 5 | Not implemented. Requires Phase C (`scan_availability()` function). |
| Draft Texts | Implemented in `generate_brief()` "Draft Texts" section | Good. Inner-circle group texts + individual outreach. Gap: texts reference event titles but not the actual event date formatted naturally (e.g., "this Saturday" vs. "2026-05-03"). `event["dateStr"]` is used, which should be human-readable — verify format in `data.js`. |
| Birthday Alerts | Missing | Not implemented anywhere. Requires FR-08 birthday normalization first. |
| Header stats | Implemented in `assemble_digest()` | Good. Shows CRM total, matched count, new contacts. |

**Largest single gap:** Calendar slot awareness (section 5 above). Without it, the digest recommends GROUP_NIGHT events for any upcoming Saturday regardless of whether Dima has early Sunday obligations or other conflicts. The calendar data is already accessible (demonstrated in this session — Google Calendar MCP works, returns events in structured format). The integration point is `social_scan.py`: add a `--cal-events` argument or a direct MCP/gws call to fetch the next 14 days, then gate slot matching.

---

## 5. Recommended Implementation Phases

### Phase A — Now: Make the loop automatic (1–2 hours)

**A1. Install launchd plists** — Create and load two plists:
- `com.atlradar.comm-scan.plist` → `comm_scan.py --write-crm` at Friday 7:00 AM
- `com.atlradar.weekly-digest.plist` → `weekly_digest.py` at Friday 7:05 AM
- Template in CRM-AUTOMATION-SPEC Section 4.5 is ready to use.

**A2. SAE cadence writeback** — Add function `update_sae_cadence(sae_path, people_updates)` to `comm_scan.py`. Called after `write_crm_updates()`. Reads the SAE, regex-replaces `last:` dates for each updated person, writes back. ~40 lines of Python. This is the highest-leverage change in the codebase.

**A3. Populate `iMessage_handle` for phone-less contacts** — One-time data task. For Rich, Charles, Marina, Devin, Hadi: add their email or phone to `crm_database.json` as `iMessage_handle` as soon as known. No code change needed — `build_phone_index()` already reads this field.

**Deliverable:** Weekly digest runs automatically every Friday. SAE dates are fresh. Priority queue is trustworthy.

### Phase B — Next week: Calendar slot gating (2–3 hours)

**B1. Add `compute_open_slots(start_date, days=14)` to `social_scan.py`** — Uses `gws calendar events list` CLI or direct Google Calendar API call. Returns a list of `{date, slot_type, time_window}` dicts based on weekday/hour analysis of existing events.

**B2. Gate event matching by open slots** — In `generate_brief()`, before rendering a slot section (e.g., GROUP_NIGHT), check that at least one GROUP_NIGHT slot is open in the next 14 days. If no open DATE_NIGHT slots exist, skip that section entirely rather than suggesting phantom date nights.

**B3. Add open slots table to digest header** — New section between "Manual-Only Contacts" and "Events This Weekend". Shows Dima what's actually free so the event recommendations are grounded.

**Deliverable:** Digest only recommends things that can actually happen given the current week.

### Phase C — Later: Signal extraction (4–6 hours)

**C1. `scan_availability()` in `comm_scan.py`** — Query `message` table, `is_from_me = 0`, last 30 days, per matched contact. Apply `AVAILABILITY_PATTERNS` regex (CRM-AUTOMATION-SPEC Section 3.3). Write `availability` field to `crm_database.json`. 14-day expiry.

**C2. `scan_interest_signals()` in `comm_scan.py`** — Same approach for activity interest signals. 60-day window. Write `interest_signals` array to `crm_database.json`.

**C3. Surface in digest** — Add "Availability Flags" section (people flagged `available` or `open`) and "Skip List" (people flagged `traveling` — omit from outreach suggestions).

**C4. Kids age data** — Manual data entry task: add `kids: [{name, birth_year, birth_month}]` to the 20 Tier-1/Tier-2 parents. Dean is b. Aug 2022 (age ~3.5), Ruby is b. 2026 (infant). Use in `FAMILY_OUT` slot matching to prefer contacts whose kids are within 2 years of Dean.

**Deliverable:** Digest knows who's available, who's traveling, and matches family events to friends with same-age kids.

### Phase D — Future: Memory Bank integration

**D1. Parse Memory Bank YAML frontmatter** — Add a function that reads `~/Documents/Brain/02_Areas/Friends/Tier-1-Active/*.md` frontmatter and extracts `last_contact_date`, `cadence`, `tier`, `location`. Use this as a supplementary signal (higher trust than SAE since it's the primary source of truth per SKILL.md).

**D2. Merge CRM JSON + batch2** — Combine `crm_database.json` and `crm_database_batch2.json` into a single file. The split is an artifact of incremental data entry, not a design choice. Single file simplifies all writeback logic and eliminates the batch2 gap in FR-07.

**Deliverable:** Single authoritative data layer. No more source-of-truth fragmentation between Memory Banks, CRM JSON, SAE, and batch2.
