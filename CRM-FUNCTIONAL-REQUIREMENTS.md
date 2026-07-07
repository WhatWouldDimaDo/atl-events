# CRM Functional Requirements
**Owner:** Dima Perkis | **Updated:** 2026-04-30 | **Scope:** Personal CRM automation for ~107 contacts

---

## 1. Current State

### What actually works

| Component | Status | What it does |
|-----------|--------|-------------|
| `comm_scan.py` | Functional | Reads `chat.db` (iMessage) + `CallHistory.storedata`, normalizes to E.164, matches against `crm_database.json` + `crm_database_batch2.json`, writes `comm_scan_results.json` with `last_imessage`, `last_call`, `last_contact`, `contact_count_90d`. New-contact detection (handles with 3+ msgs or 1+ calls not in CRM). AddressBook reverse-lookup for name enrichment. |
| `social_scan.py` | Functional | Reads `social_activation_engine.md` (SAE), computes `priority = (days_since - cadence_days) × tier_mult`, matches people to events from `events.json` by slot type and lead time, generates Social Brief with inner-circle invite lists and draft texts. |
| `weekly_digest.py` | Functional | Chains comm_scan → export_events → social_scan, assembles "This Week's Contacts", "New Contact Inbox", "Manual-Only Contacts", and the full Social Brief into `~/Documents/Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md`. |
| Memory Banks | Functional | `~/Documents/Brain/02_Areas/Friends/Tier-1-Active/` — YAML frontmatter + narrative. Primary source of truth for narrative data. |
| `crm_database.json` | Partially stale | 40+ entries. Writeback from `comm_scan.py --write-crm` is implemented but never runs on a schedule. |
| SAE (`social_activation_engine.md`) | Manually curated | Generated 2026-04-21, not auto-regenerated. `social_scan.py` reads cadence `last:` dates directly from this file. |

### What is manual / broken

1. **`comm_scan.py` runs on demand only.** No launchd plist loaded. CRM writeback requires explicit `--write-crm` flag and someone to run the script. This is the single highest-leverage gap — the entire priority queue in `social_scan.py` depends on fresh `last_contact` dates in the SAE.

2. **SAE cadence section is never updated automatically.** `comm_scan.py --write-crm` writes back to `crm_database.json` but does NOT regenerate the `## Cadence Targets` section of `social_activation_engine.md`. `social_scan.py` reads from the SAE, not from `crm_database.json`, so stale SAE = wrong priority queue even after CRM writeback runs.

3. **New contacts have no phone.** Rich, Charles, Marina, Devin, Hadi — met in-person, `phone: null`, no `iMessage_handle`. `comm_scan.py` lists them under `manual_only_contacts` in output but can never auto-track them. The `iMessage_handle` field exists in the schema but is unpopulated.

4. **No scheduled run.** `weekly_digest.py` has no launchd plist. Nothing runs Friday at 7 AM automatically.

5. **Gmail is not scanned.** `comm_scan.py` only reads iMessage + calls. Email exchanges (e.g., personal Gmail at dperkis@gmail.com) are not considered for `last_contact_date`. The Gmail MCP token (dperkis@lahzo.com) is work-only and currently expired.

6. **Calendar is not read for social signals.** The 14-day calendar window shows the next two weeks are entirely Lahzo work meetings (CR Team meetings, Brad/Mitchell/Dima weekly, Dima/Carter 1:1s). No personal social events are on the calendar. `social_scan.py` does not read Google Calendar at all — available time slots are never computed.

7. **New contact pipeline is voice-note-dependent.** Dima meets someone → Superwhisper voice note → agent writes to daily note → manual CRM entry. Zero automation in this flow. If the voice note doesn't happen, the person is lost.

8. **`last_contact_date` is stale for ~60% of entries.** Example from CRM-AUTOMATION-SPEC: Arjun shows `2026-03-01` in `crm_database.json` but Memory Bank says "iMessage thread active Apr 2026."

---

## 2. Data Sources Audit

| Source | Connected | What's used today | Gap |
|--------|-----------|-------------------|-----|
| iMessage (`chat.db`) | Yes | Timestamps + message count per handle. Matched by E.164 phone or email handle. | Message content not scanned (needed for availability/interest signals). `attributedBody` parsing implemented in `extract_message_text()` but not called in Phase A flows. |
| Call history (`CallHistory.storedata`) | Yes | Last call date, call count 90d, direction (incoming/outgoing). | Same gap — no content. |
| `crm_database.json` | Yes | Phone + email for handle matching; `last_contact_date` as floor for writeback. | Stale. 15% of contacts have no phone. 30% have no email. `contact_count_90d` field is new (Phase A) — not in original schema. |
| `crm_database_batch2.json` | Read-only | Same as above — scanned for matching but writeback only goes to `crm_database.json`. | Batch2 contacts never get their `last_contact_date` updated. |
| AddressBook (`AddressBook-v22.abcddb`) | Yes | Name enrichment for new contact candidates (unmatched handles). | Two source UUIDs hard-coded in `ADDRESSBOOK_SOURCES`. Will silently fail if the path changes (OS upgrade). |
| Google Contacts (People API via `gws`) | Push target only | `push_payload_preview.json` is generated but `push_to_google_contacts.py` is listed as TBD. | No active sync. |
| `social_activation_engine.md` | Yes | Phone index + slot assignments + cadence `last:` dates — the actual input to `social_scan.py`. | Not auto-regenerated. Last updated 2026-04-21. |
| Memory Banks (`Tier-1-Active/*.md`) | Read-only | Narrative context. Not parsed by any script today. | YAML frontmatter (`last_contact_date`, `tier`, `cadence`) is the authoritative record but no script reads it programmatically. |
| Google Calendar | Not connected | Not read by any script. | `social_scan.py` does not know which evenings are actually free. DATE_NIGHT/GROUP_NIGHT suggestions are made blind to Dima's schedule. |
| Gmail (personal) | Not connected | Not scanned. | Email outreach (e.g., reconnect threads) not counted toward `last_contact_date`. |
| Dex snapshot | Read-only archive | Used as seed data when CRM was built. | Snapshot is from Dec 2025. No live sync. |
| Daily notes | Manual capture | New contacts captured via voice note → agent → daily note → manual CRM entry. | No automated extraction from daily notes into CRM. |

---

## 3. Functional Requirements

### FR-01: Scheduled weekly CRM refresh (P0)
The system must run `comm_scan.py --write-crm` automatically every Friday morning at 7 AM via launchd plist at `~/Library/LaunchAgents/com.atlradar.social-scan.plist`. No manual intervention required. Output logged to `/tmp/comm_scan.log`.

### FR-02: SAE cadence section writeback (P0)
After `comm_scan.py --write-crm` updates `crm_database.json`, it must also regenerate the `## Cadence Targets` section of `social_activation_engine.md` with updated `last:` dates. The update logic: for each person in the SAE cadence section, if `crm_database.json` has a more recent `last_contact_date`, write it as `last: YYYY-MM-DD`. `social_scan.py` must not require any other change.

### FR-03: Weekly digest auto-run (P0)
`weekly_digest.py` must run every Friday at 7:05 AM (after FR-01 completes), writing to `~/Documents/Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md`. A second launchd plist handles this, with a 5-minute offset from the comm_scan plist.

### FR-04: New contact candidate surfacing (P1)
The "New Contact Inbox" section of the weekly digest must surface all unmatched handles with `message_count_90d >= 3` OR `call_count_90d >= 1`. Already implemented in `build_new_contacts_section()` in `weekly_digest.py` — requires FR-01 to run so `comm_scan_results.json` is fresh.

### FR-05: `iMessage_handle` field population for phone-less contacts (P1)
For contacts with `phone: null` (Rich, Charles, Marina, Devin, Hadi, and all future in-person contacts), an `iMessage_handle` field must be populated in `crm_database.json` as soon as their email is known. Once set, `build_phone_index()` in `comm_scan.py` picks it up automatically on the next scan.

### FR-06: Calendar slot awareness in social_scan.py (P1)
`social_scan.py` must read the primary Google Calendar for the next 14 days and compute available evening/weekend slots before generating the Social Brief. Available slot types:
- `DATE_NIGHT`: evening with no work event after 6 PM AND babysitter booked (manual flag or event keyword match)
- `GROUP_NIGHT`: weeknight 7 PM+, no early meeting next morning (before 8 AM)
- `FAMILY_OUT`: Sat/Sun before 2 PM, no conflicts
- `SOLO_RESET`: any morning block before 9 AM with no meeting

The generated brief must only suggest events within slots that are actually open. Currently the brief suggests any event regardless of Dima's schedule.

**Calendar observation (Apr 30 – May 14):** Zero personal/social events on calendar. Work is entirely Lahzo (CR Team meetings M/W/Th/F, Brad/Mitchell/Dima weekly Mondays, Dima/Carter bi-weekly). Evenings and weekends May 2–13 are unblocked except May 2 AM (Dima has kids) and May 2 4–7 PM (Adric Karsai birthday, already on daily note). The calendar gap confirms that social events never make it onto Google Calendar, which makes slot-detection logic require careful weekday/hour logic rather than literal event presence.

### FR-07: Batch2 writeback (P2)
`comm_scan.py --write-crm` must also write back to `crm_database_batch2.json` for the 36 contacts stored there. Currently writeback is `CRM_DB` only (line 496 in `comm_scan.py`: `if name not in db: continue`).

### FR-08: Birthday normalization (P2)
Normalize all `birthday` values in both CRM JSON files to `MM-DD` format (drop year or use `YYYY-MM-DD` where year is known). Run a one-time migration script; ongoing entries should enforce the format. Enables a birthday reminder section in the weekly digest.

### FR-09: `location` field enforcement (P2)
Add `location` (city string, e.g., `"Atlanta"`, `"Chicago"`) to all CRM entries. Currently populated for only 2 contacts. Required for "who's local this weekend" filter in social_scan.py. Can be bootstrapped from Memory Bank frontmatter where it exists.

### FR-10: Availability signal extraction from iMessage (Phase C)
Add `scan_availability()` function to `comm_scan.py` that queries `message.text` (with `attributedBody` fallback via `extract_message_text()`) for `is_from_me = 0` messages in the last 30 days per matched contact. Apply `AVAILABILITY_PATTERNS` regex dict (defined in CRM-AUTOMATION-SPEC Section 3.3). Write result to `availability` field in `crm_database.json`. Expire after 14 days. Surface in weekly digest as "Availability Flags" section.

---

## 4. Data Model Changes Needed

### Fields missing from `crm_database.json`

| Field | Type | Status | Needed for |
|-------|------|--------|-----------|
| `contact_count_90d` | `int` | Schema defined, not yet populated | FR-01, digest "This Week" section |
| `last_comm_scan` | `string (YYYY-MM-DD)` | Schema defined, not yet populated | Audit trail — when was this record last touched by comm_scan |
| `iMessage_handle` | `string` | Schema defined, not populated for phone-less contacts | FR-05 — alternate matching handle |
| `availability` | `object {status, note, detected, expires}` | Missing | FR-10 |
| `interest_signals` | `array [{tag, detected, source, expires}]` | Missing | Phase C |
| `kids` | `array [{name, birth_year, birth_month}]` | Missing | FAMILY_OUT age matching |
| `location` | `string (city)` | Populated for 2/107 contacts | FR-09, "who's local" filter |

### Normalization issues to fix (one-time migration)

| Field | Current mess | Target format |
|-------|-------------|---------------|
| `last_platform` | Mixed casing: `"imessage"`, `"iMessage"`, `"in_person"`, `"In Person"` | Enum: `imessage \| call \| in_person \| email \| linkedin \| facebook` |
| `birthday` | `"November 11"`, `"1986-06-27"`, `"????-02-05"`, `""` | `"MM-DD"` or `"YYYY-MM-DD"` or `null` |
| `linkedin_connected` | Mix of bool and string `"yes"/"no"` | `true \| false \| null` |

### `crm_database_batch2.json` gap
Batch2 has 36 contacts that only get read, never written. Either merge batch2 into the main file (preferred) or extend `write_crm_updates()` to handle both files. The current `if name not in db: continue` guard (line 496 of `comm_scan.py`) silently skips all batch2 contacts.
