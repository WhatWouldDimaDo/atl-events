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
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
EVENTS_JSON = SCRIPTS_DIR / "events.json"
SAE_FILE = Path.home() / "Documents/Coding/Projects/personal-crm/derived/social_activation_engine.md"

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
    "GROUP_NIGHT": 10,
    "DATE_NIGHT": 5,
    "FAMILY_OUT": 5,
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


def generate_brief(people: list[dict], events: list[dict], today: date) -> str:
    """Generate the full Social Brief as markdown."""
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

    # --- Select events per slot type (ensures diversity) ---
    slot_events = {}
    for slot in SLOTS_TO_SHOW:
        candidates = [e for e in events if slot in e.get("slots", [])]
        candidates.sort(key=lambda e: -e.get("score", 0))
        slot_events[slot] = candidates[:MAX_PER_SLOT.get(slot, 3)]

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
        brief = generate_brief(people, events, today)
        print(brief)


if __name__ == "__main__":
    main()
