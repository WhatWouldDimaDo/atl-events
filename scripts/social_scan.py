#!/usr/bin/env python3
"""Social Scan — Weekly Social Momentum Brief

Reads CRM data (social_activation_engine.md), events (events.json),
and generates a Social Brief matching friends to upcoming events.

Usage:
    python3 scripts/social_scan.py              # Print brief to stdout
    python3 scripts/social_scan.py --json       # Output raw JSON matches
"""
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
EVENTS_JSON = SCRIPTS_DIR / "events.json"
SAE_FILE = Path.home() / "Documents/Coding/Projects/2026-04-18_Personal-CRM/derived/social_activation_engine.md"

# CRM JSON fallback paths
CRM_DB = Path.home() / "Documents/Brain/02_Areas/Friends/crm_database.json"
CRM_DB2 = Path.home() / "Documents/Brain/02_Areas/Friends/crm_database_batch2.json"

# Cadence in days
CADENCE_DAYS = {
    "weekly": 7,
    "bi-weekly": 14,
    "monthly": 30,
    "quarterly": 90,
    "6 months": 180,
    "yearly": 365,
}

# Tier multipliers for priority scoring
TIER_MULT = {1: 3, 2: 2, 3: 1}

# Lead time: how far in advance an event needs to be for this slot type
LEAD_TIME_DAYS = {
    "GROUP_NIGHT": 7,
    "DATE_NIGHT": 3,
    "FAMILY_OUT": 3,
    "LAST_MINUTE": 0,
    "SOLO_RESET": 0,
}

# Inner circles — the always-invite crew per social group.
# These are relational, not algorithmic — they come from /social-scan command context.
# The broader CRM groups (23 Concert Squad, 39 Kids Crew) are the outreach pool.
INNER_CIRCLE = {
    "Concert Squad": {
        "David Feldman", "Craig Jones", "Davis Burgess",
        "Arjun Sawhney", "James Watson", "Jeff Ader", "Cole Younger",
    },
    "Kids Crew": {
        "Davis Burgess", "Craig Jones", "Liam Greenamyre", "Josh Wallace",
        "Chris Willey", "Ted Ketterer", "Ben Karsai", "Shubh Singhi",
    },
    "Couples Dinner": {
        "Arjun Sawhney", "Jeff Ader", "James Watson", "Craig Jones",
    },
    "Close By": {
        "Davis Burgess", "Robert Nonemaker", "Craig Jones", "Jon Berman",
    },
}

# Map event slot types to social groups
SLOT_TO_GROUP = {
    "GROUP_NIGHT": "Concert Squad",
    "FAMILY_OUT": "Kids Crew",
    "DATE_NIGHT": "Couples Dinner",
    "LAST_MINUTE": "Close By",
}

# How many events to show per slot type
MAX_PER_SLOT = {
    "GROUP_NIGHT": 4,
    "DATE_NIGHT": 2,
    "FAMILY_OUT": 3,
    "SOLO_RESET": 2,
}

SLOTS_TO_SHOW = ["GROUP_NIGHT", "DATE_NIGHT", "FAMILY_OUT", "SOLO_RESET"]

SLOT_LABELS = {
    "GROUP_NIGHT": "Nights Out",
    "DATE_NIGHT": "Date Nights",
    "FAMILY_OUT": "Family Outings",
    "SOLO_RESET": "Solo Resets",
}


def parse_sae_file(path: Path) -> dict:
    """Parse social_activation_engine.md into structured data.

    Returns {
        'phone_index': {name: phone},
        'people': [{name, tier, kids, slots, groups, cadence, last_contact}],
        'couples': [(name1, name2)],
    }
    """
    text = path.read_text(encoding="utf-8")

    # Phone index
    phone_index = {}
    for m in re.finditer(r"^- (.+?):\s*(\+\d+)", text, re.MULTILINE):
        phone_index[m.group(1).strip()] = m.group(2).strip()

    # Slot assignments table
    people = []
    table_match = re.search(
        r"\| Name \| Tier \| Kids \| best_invite_for \| social_groups \|(.+?)(?=\n## |\Z)",
        text,
        re.DOTALL,
    )
    if table_match:
        for row in table_match.group(1).strip().splitlines():
            cols = [c.strip() for c in row.split("|")]
            if len(cols) < 6 or cols[1] == "---":
                continue
            name = cols[1]
            try:
                tier = int(cols[2])
            except (ValueError, IndexError):
                tier = 3
            kids = cols[3].lower() if len(cols) > 3 else "unknown"
            slots_raw = cols[4] if len(cols) > 4 else ""
            groups_raw = cols[5] if len(cols) > 5 else ""

            slots = [s.strip() for s in slots_raw.split(",") if s.strip()]
            groups = [g.strip() for g in groups_raw.split(",") if g.strip() and g.strip() != "—"]

            people.append({
                "name": name,
                "tier": tier,
                "kids": kids,
                "slots": slots,
                "groups": groups,
                "phone": phone_index.get(name),
            })

    # Cadence targets
    cadence_section = re.search(r"## Cadence Targets(.+?)(?=\Z)", text, re.DOTALL)
    if cadence_section:
        current_cadence = None
        for line in cadence_section.group(1).splitlines():
            cadence_match = re.match(r"### (\w[\w\s]*)\s*\(\d+\)", line)
            if cadence_match:
                current_cadence = cadence_match.group(1).strip()
                continue
            person_match = re.match(r"- (.+?)\s*\(last:\s*(.+?)\)", line)
            if person_match and current_cadence:
                pname = person_match.group(1).strip()
                last_str = person_match.group(2).strip()
                last_date = None
                if last_str != "unknown":
                    try:
                        last_date = datetime.strptime(last_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                # Merge into people list
                for p in people:
                    if p["name"] == pname:
                        p["cadence"] = current_cadence
                        p["last_contact"] = last_date
                        break

    # Couples pairs
    couples = []
    couples_section = re.search(r"## Couples Dinner Pairs(.+?)(?=\n## |\Z)", text, re.DOTALL)
    if couples_section:
        for line in couples_section.group(1).splitlines():
            m = re.match(r"- (.+?)\+(.+)", line.strip())
            if m:
                couples.append((m.group(1).strip(), m.group(2).strip()))

    return {"phone_index": phone_index, "people": people, "couples": couples}


def compute_priority(person: dict, today: date) -> int:
    """Compute priority score. Higher = more overdue."""
    cadence = person.get("cadence", "quarterly")
    cadence_days = CADENCE_DAYS.get(cadence, 90)
    last = person.get("last_contact")
    if not last:
        return cadence_days * TIER_MULT.get(person.get("tier", 3), 1)
    days_since = (today - last).days
    days_overdue = days_since - cadence_days
    return days_overdue * TIER_MULT.get(person.get("tier", 3), 1)


def days_overdue_str(person: dict, today: date) -> str:
    """Human-readable overdue string."""
    cadence = person.get("cadence", "quarterly")
    cadence_days = CADENCE_DAYS.get(cadence, 90)
    last = person.get("last_contact")
    if not last:
        return "unknown"
    days_since = (today - last).days
    overdue = days_since - cadence_days
    if overdue > 0:
        return f"+{overdue}d overdue"
    elif overdue == 0:
        return "due today"
    else:
        return f"{-overdue}d until due"


def load_events(path: Path, today: date) -> list[dict]:
    """Load events.json, filter to future events, sort by date."""
    events = json.loads(path.read_text(encoding="utf-8"))
    future = [e for e in events if e.get("date", "") >= today.isoformat()]
    future.sort(key=lambda e: (e.get("date", ""), -e.get("score", 0)))
    return future


# --- Phase B: Google Calendar slot awareness (FR-06 / CRM-BEST-PRACTICES B1-B3) ---

SLOT_HORIZON_DAYS = 14
BABYSITTER_RE = re.compile(r"babysit|sitter|nanny|au pair", re.IGNORECASE)


def fetch_calendar_events(today: date, days: int = SLOT_HORIZON_DAYS) -> list[dict] | None:
    """Fetch events from the primary Google Calendar via the gws CLI.

    Returns a list of {date, start_hour, end_hour, all_day, summary} dicts,
    or None if the calendar is unavailable (gws missing, auth expired, etc.).
    Callers must treat None as "no gating possible", not "calendar empty".
    """
    params = json.dumps({
        "calendarId": "primary",
        "timeMin": f"{today.isoformat()}T00:00:00Z",
        "timeMax": f"{(today + timedelta(days=days)).isoformat()}T00:00:00Z",
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 250,
    })
    try:
        proc = subprocess.run(
            ["gws", "calendar", "events", "list", "--params", params],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(proc.stdout)
        if "error" in data or "items" not in data:
            return None
    except Exception:
        return None

    out = []
    for item in data.get("items", []):
        if item.get("status") == "cancelled" or item.get("transparency") == "transparent":
            continue
        start, end = item.get("start", {}), item.get("end", {})
        if "date" in start:  # all-day
            out.append({"date": start["date"], "start_hour": None, "end_hour": None,
                        "all_day": True, "summary": item.get("summary", "")})
            continue
        try:
            sdt = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00")).astimezone()
            edt = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00")).astimezone()
        except ValueError:
            continue
        out.append({"date": sdt.date().isoformat(),
                    "start_hour": sdt.hour + sdt.minute / 60,
                    "end_hour": edt.hour + edt.minute / 60,
                    "all_day": False, "summary": item.get("summary", "")})
    return out


def compute_open_slots(cal_events: list[dict], today: date,
                       days: int = SLOT_HORIZON_DAYS) -> list[dict]:
    """Compute open social slots from calendar busy-time (FR-06 rules).

    - DATE_NIGHT:  evening free after 6 PM; "confirmed" only when a babysitter
                   keyword event exists that day, else flagged "book sitter"
                   (social events rarely reach the calendar — Apr 30 finding)
    - GROUP_NIGHT: weeknight free 7 PM+, no meeting before 8 AM next morning
    - FAMILY_OUT:  Sat/Sun free 9 AM-2 PM
    - SOLO_RESET:  morning free before 9 AM
    """
    by_date: dict[str, list[dict]] = {}
    for e in cal_events:
        by_date.setdefault(e["date"], []).append(e)

    def busy(day_iso: str, h1: float, h2: float) -> bool:
        return any(
            not e["all_day"] and e["start_hour"] is not None
            and e["start_hour"] < h2 and e["end_hour"] > h1
            for e in by_date.get(day_iso, [])
        )

    slots = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        iso = day.isoformat()
        wd = day.weekday()  # 0=Mon .. 6=Sun
        next_iso = (day + timedelta(days=1)).isoformat()
        early_next = any(
            not e["all_day"] and e["start_hour"] is not None and e["start_hour"] < 8
            for e in by_date.get(next_iso, [])
        )
        evening_free = not busy(iso, 18, 23)
        sitter = any(BABYSITTER_RE.search(e["summary"] or "") for e in by_date.get(iso, []))

        if wd < 5 and evening_free and not early_next:
            slots.append({"date": iso, "day": day.strftime("%a"), "slot": "GROUP_NIGHT",
                          "window": "7 PM+", "note": ""})
        if evening_free and (sitter or wd in (4, 5)):  # sitter-confirmed, or Fri/Sat
            slots.append({"date": iso, "day": day.strftime("%a"), "slot": "DATE_NIGHT",
                          "window": "evening",
                          "note": "sitter booked" if sitter else "book sitter"})
        if wd >= 5 and not busy(iso, 9, 14):
            slots.append({"date": iso, "day": day.strftime("%a"), "slot": "FAMILY_OUT",
                          "window": "9 AM-2 PM", "note": ""})
        if not busy(iso, 6, 9):
            slots.append({"date": iso, "day": day.strftime("%a"), "slot": "SOLO_RESET",
                          "window": "before 9 AM", "note": ""})
    return slots


def match_events_to_person(person: dict, events: list[dict], today: date) -> list[dict]:
    """Find events matching this person's slot types, respecting lead time."""
    person_slots = set(person.get("slots", []))
    if not person_slots or person_slots == {"SOLO_RESET"}:
        return []

    matches = []
    for ev in events:
        ev_slots = set(ev.get("slots", []))
        common = person_slots & ev_slots
        if not common:
            continue
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        days_until = (ev_date - today).days
        # Check lead time for each matching slot
        for slot in common:
            min_lead = LEAD_TIME_DAYS.get(slot, 7)
            if days_until >= min_lead:
                matches.append({
                    "event": ev,
                    "slot": slot,
                    "days_until": days_until,
                })
                break  # one match per event is enough
    # Sort by score desc, take top 3
    matches.sort(key=lambda m: -m["event"].get("score", 0))
    return matches[:3]


def draft_text(person: dict, event: dict, slot: str) -> str:
    """Generate a ready-to-send text message draft."""
    first = person["name"].split()[0]
    title = event["title"]
    datestr = event.get("dateStr", event.get("date", ""))
    venue = event.get("venue", "")
    ticket = event.get("ticketUrl") or event.get("officialUrl") or ""

    if slot == "FAMILY_OUT":
        msg = f"{title} — {datestr} at {venue}. Bringing Dean, want to join with the kids?"
    elif slot == "DATE_NIGHT":
        msg = f"{title} — {datestr} at {venue}. Want to make it a double date?"
    else:
        msg = f"{title} — {datestr} at {venue}. You in?"

    if ticket:
        msg += f"\n{ticket}"
    return msg


def draft_group_text(event: dict) -> str:
    """Generate a group text for the inner circle."""
    title = event["title"]
    datestr = event.get("dateStr", event.get("date", ""))
    venue = event.get("venue", "")
    ticket = event.get("ticketUrl") or event.get("officialUrl") or ""
    msg = f"{title} — {datestr} at {venue}. Who's in?"
    if ticket:
        msg += f"\n{ticket}"
    return msg


def best_friends_for_event(
    ev: dict, people: list[dict], today: date, target_slot: str | None = None,
) -> dict:
    """Find the best friends to invite to this event.

    Args:
        target_slot: If set, only match this slot type (used when the brief
                     renders a specific section like DATE_NIGHT).

    Returns {
        "inner": [(person, slot), ...],    # always-invite crew, never capped
        "outreach": [(person, slot), ...],  # overdue non-inner people, capped at 4
    }
    """
    ev_slots = [target_slot] if target_slot else ev.get("slots", [])
    ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
    days_until = (ev_date - today).days

    inner = []
    outreach = []
    seen = set()

    for slot in ev_slots:
        if slot == "SOLO_RESET":
            continue
        min_lead = LEAD_TIME_DAYS.get(slot, 7)
        if days_until < min_lead:
            continue

        preferred_group = SLOT_TO_GROUP.get(slot)
        inner_names = INNER_CIRCLE.get(preferred_group, set()) if preferred_group else set()

        for p in people:
            if p["name"] in seen:
                continue
            if slot not in p.get("slots", []):
                continue

            priority = p.get("_priority", 0)

            if p["name"] in inner_names:
                inner.append((p, slot))
            elif preferred_group and preferred_group in p.get("groups", []) and priority > 0:
                outreach.append((p, slot))

            seen.add(p["name"])

    # Sort inner by priority desc (most overdue inner member first, but all appear)
    inner.sort(key=lambda x: -x[0].get("_priority", 0))
    # Sort outreach by priority desc, cap at 4
    outreach.sort(key=lambda x: -x[0].get("_priority", 0))
    outreach = outreach[:4]

    return {"inner": inner, "outreach": outreach}


def generate_brief(people: list[dict], events: list[dict], today: date,
                   open_slots: list[dict] | None = None) -> str:
    """Generate the full Social Brief as markdown.

    open_slots: output of compute_open_slots(), or None when the calendar is
    unavailable — then no slot gating is applied (pre-Phase-B behavior).
    """
    lines = []
    lines.append(f"## Social Scan — Week of {today.strftime('%b %d')}")
    lines.append("")

    # Compute priority for everyone
    for p in people:
        p["_priority"] = compute_priority(p, today)
        p["_overdue_str"] = days_overdue_str(p, today)

    # All overdue (for the outreach table)
    all_overdue = [p for p in people if p["_priority"] > 0]
    all_overdue.sort(key=lambda p: -p["_priority"])

    # --- Open Slots This Week (Phase B3) ---
    open_dates: dict[str, set[str]] = {}
    if open_slots is None:
        lines.append("_Calendar unavailable (gws auth expired or offline) — "
                     "event suggestions are NOT gated by your actual schedule._")
        lines.append("")
    else:
        for s in open_slots:
            open_dates.setdefault(s["slot"], set()).add(s["date"])
        lines.append("### Open Slots This Week")
        lines.append("")
        lines.append("| Date | Day | Slot | Window | Note |")
        lines.append("|------|-----|------|--------|------|")
        shown = 0
        for s in open_slots:
            if s["slot"] == "SOLO_RESET" and shown > 14:
                continue  # solo mornings are plentiful — don't drown the table
            lines.append(f"| {s['date']} | {s['day']} | {s['slot']} | {s['window']} | {s['note']} |")
            shown += 1
        lines.append("")

    # --- Select events per slot type (ensures diversity) ---
    # Phase B2 gating: events inside the calendar horizon must land on an open
    # slot date for their slot type; events beyond the horizon pass through.
    def slot_open(e: dict, slot: str) -> bool:
        if open_slots is None:
            return True
        ev_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
        if (ev_date - today).days >= SLOT_HORIZON_DAYS:
            return True
        return e["date"] in open_dates.get(slot, set())

    slot_events = {}
    for slot in SLOTS_TO_SHOW:
        candidates = [e for e in events
                      if slot in e.get("slots", []) and slot_open(e, slot)]
        candidates.sort(key=lambda e: -e.get("score", 0))
        slot_events[slot] = candidates[:MAX_PER_SLOT.get(slot, 3)]
        if open_slots is not None and not candidates and not open_dates.get(slot):
            slot_events[slot] = []  # section will be skipped — no phantom suggestions

    # Track outreach names used across all events to avoid repetition
    used_outreach = set()

    # --- Event Matches by Slot Type ---
    for slot_type in SLOTS_TO_SHOW:
        evs = slot_events.get(slot_type, [])
        if not evs:
            continue

        label = SLOT_LABELS.get(slot_type, slot_type)
        lines.append(f"### {label}")
        lines.append("")

        for ev in evs:
            ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            days_until = (ev_date - today).days

            if slot_type == "SOLO_RESET":
                # No friend matching — personal calendar suggestion
                lines.append(f"**{ev['dateStr']} — {ev['title']} (Score {ev['score']})**")
                lines.append(f"Venue: {ev['venue']}")
                lines.append("No invite needed — personal slot")
                if ev.get("officialUrl"):
                    lines.append(f"Info: {ev['officialUrl']}")
                lines.append("")
                continue

            result = best_friends_for_event(ev, people, today, target_slot=slot_type)

            if slot_type == "DATE_NIGHT":
                lines.append(f"**{ev['dateStr']} — {ev['title']} (Score {ev['score']})**")
                lines.append(f"Venue: {ev['venue']}")
                lines.append("Primary: Jeannie date — check babysitter calendar")
                if result["inner"]:
                    couples = [p["name"] for p, _ in result["inner"]]
                    lines.append(f"Double date: {', '.join(couples)}")
                if days_until <= 7:
                    lines.append(f"Lead time: {days_until} days — text NOW")
                elif days_until <= 14:
                    lines.append(f"Lead time: {days_until} days — plan this week")
                if ev.get("ticketUrl"):
                    lines.append(f"Tickets: {ev['ticketUrl']}")
                elif ev.get("officialUrl"):
                    lines.append(f"Info: {ev['officialUrl']}")
                lines.append("")
                continue

            # GROUP_NIGHT and FAMILY_OUT — full friend matching
            inner_names = [p["name"] for p, _ in result["inner"]]

            # Deduplicate outreach across events
            fresh_outreach = []
            for p, s in result["outreach"]:
                if p["name"] not in used_outreach and p["_priority"] > 0:
                    fresh_outreach.append(f"{p['name']} ({p['_overdue_str']})")
                    used_outreach.add(p["name"])
                if len(fresh_outreach) >= 3:
                    break

            lines.append(f"**{ev['dateStr']} — {ev['title']} (Score {ev['score']})**")
            lines.append(f"Venue: {ev['venue']}")
            if inner_names:
                lines.append(f"Invite: {', '.join(inner_names)}")
            if fresh_outreach:
                lines.append(f"Also reach out: {', '.join(fresh_outreach)}")
            if days_until <= 7:
                lines.append(f"Lead time: {days_until} days — text NOW")
            elif days_until <= 14:
                lines.append(f"Lead time: {days_until} days — text this week")
            else:
                lines.append(f"Lead time: {days_until} days")
            if ev.get("ticketUrl"):
                lines.append(f"Tickets: {ev['ticketUrl']}")
            elif ev.get("officialUrl"):
                lines.append(f"Info: {ev['officialUrl']}")
            if ev.get("urgent"):
                lines.append(f"**ACT FAST:** {ev.get('urgentNote', 'Limited availability')}")
            lines.append("")

    # --- Buy Now / Act Fast ---
    urgent_events = [e for e in events if e.get("urgent") or e.get("tier") == "S"]
    if urgent_events:
        lines.append("### Buy Now / Act Fast")
        lines.append("")
        for ev in urgent_events:
            ticket = ev.get("ticketUrl") or ev.get("officialUrl") or "no link"
            note = ev.get("urgentNote") or f"Score {ev['score']}, Tier {ev['tier']}"
            lines.append(f"- **{ev['title']}** — {ev['dateStr']} — {note} — {ticket}")
        lines.append("")

    # --- Top Overdue ---
    lines.append("### Top 10 Overdue")
    lines.append("")
    lines.append("| Friend | Tier | Cadence | Last Contact | Status |")
    lines.append("|--------|------|---------|-------------|--------|")
    for p in all_overdue[:10]:
        last = p.get("last_contact")
        last_str = last.strftime("%b %d") if last else "unknown"
        lines.append(
            f"| {p['name']} | {p['tier']} | {p.get('cadence', '?')} | "
            f"{last_str} | {p['_overdue_str']} |"
        )
    lines.append("")

    # --- Draft Texts ---
    lines.append("### Draft Texts")
    lines.append("")

    # Group texts for inner circle (one per slot type with events)
    group_drafted = set()
    for slot_type in ["GROUP_NIGHT", "FAMILY_OUT"]:
        evs = slot_events.get(slot_type, [])
        if not evs:
            continue
        # Use the highest-score event for the group text
        top_ev = evs[0]
        result = best_friends_for_event(top_ev, people, today, target_slot=slot_type)
        if not result["inner"]:
            continue

        inner_first_names = []
        for p, _ in result["inner"]:
            first = p["name"].split()[0]
            if first not in group_drafted:
                inner_first_names.append(first)
                group_drafted.add(first)

        if inner_first_names:
            msg = draft_group_text(top_ev)
            lines.append(f"**Group text -> {', '.join(inner_first_names)}:**")
            lines.append(f"> {msg}")
            lines.append("")

    # Individual outreach drafts for overdue friends
    individual_drafted = set()
    for slot_type in SLOTS_TO_SHOW:
        for ev in slot_events.get(slot_type, []):
            if slot_type in ("SOLO_RESET", "DATE_NIGHT"):
                continue
            result = best_friends_for_event(ev, people, today, target_slot=slot_type)
            for p, slot in result["outreach"]:
                if p["name"] in individual_drafted:
                    continue
                if p["_priority"] <= 0:
                    continue
                individual_drafted.add(p["name"])
                msg = draft_text(p, ev, slot)
                lines.append(f"**{p['name']}** ({p['_overdue_str']}):")
                lines.append(f"> {msg}")
                lines.append("")
                if len(individual_drafted) >= 5:
                    break
            if len(individual_drafted) >= 5:
                break
        if len(individual_drafted) >= 5:
            break

    return "\n".join(lines)


def main():
    today = date.today()

    # Load CRM data from social_activation_engine.md
    if not SAE_FILE.exists():
        print(f"Error: {SAE_FILE} not found. Run personal-crm agent first.", file=sys.stderr)
        sys.exit(1)

    sae = parse_sae_file(SAE_FILE)
    people = sae["people"]
    print(f"Loaded {len(people)} people from social_activation_engine.md", file=sys.stderr)

    # Load events
    if not EVENTS_JSON.exists():
        print("events.json not found — run export_events.py first", file=sys.stderr)
        sys.exit(1)

    events = load_events(EVENTS_JSON, today)
    print(f"Loaded {len(events)} future events", file=sys.stderr)

    # Phase B: calendar slot awareness (graceful when gws is unavailable)
    open_slots = None
    if "--no-cal" not in sys.argv:
        cal_events = fetch_calendar_events(today)
        if cal_events is None:
            print("Calendar unavailable — skipping slot gating", file=sys.stderr)
        else:
            open_slots = compute_open_slots(cal_events, today)
            print(f"Calendar: {len(cal_events)} events -> {len(open_slots)} open slots",
                  file=sys.stderr)

    if "--json" in sys.argv:
        # Raw JSON output for debugging
        for p in people:
            p["_priority"] = compute_priority(p, today)
            p["_matches"] = [
                {"event_id": m["event"]["id"], "title": m["event"]["title"], "slot": m["slot"]}
                for m in match_events_to_person(p, events, today)
            ]
        output = sorted(
            [p for p in people if p["_priority"] > 0],
            key=lambda p: -p["_priority"],
        )
        print(json.dumps(output[:20], indent=2, default=str))
    else:
        brief = generate_brief(people, events, today, open_slots=open_slots)
        print(brief)


if __name__ == "__main__":
    main()
