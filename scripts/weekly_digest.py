#!/usr/bin/env python3
"""Weekly Social Digest — Phase B

Chains: comm_scan → export_events → social_scan → assembles digest → writes to Brain vault.

Steps:
  1. comm_scan.py            — scan iMessage + calls, refresh comm_scan_results.json
  2. export_events.py        — refresh events.json from data.js
  3. social_scan.py          — generate event-friend match brief
  4. Prepend contact activity — "This Week's Contacts" + "New Contact Inbox"
  5. Write to Brain vault     — ~/Documents/Brain/02_Areas/Friends/social_digest_YYYY-MM-DD.md

Usage:
    python3 scripts/weekly_digest.py              # full run, write to vault
    python3 scripts/weekly_digest.py --dry-run    # scan + assemble, print to stdout (no vault write, no CRM update)
    python3 scripts/weekly_digest.py --no-crm     # skip comm_scan, use existing results.json
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"

COMM_SCAN     = SCRIPTS_DIR / "comm_scan.py"
EXPORT_EVENTS = SCRIPTS_DIR / "export_events.py"
SOCIAL_SCAN   = SCRIPTS_DIR / "social_scan.py"
COMM_RESULTS  = SCRIPTS_DIR / "comm_scan_results.json"

VAULT_FRIENDS = Path.home() / "Documents/Brain/02_Areas/Friends"

PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------

def run_step(label: str, cmd: list[str]) -> tuple[bool, str]:
    """Run a subprocess step. Returns (success, stdout). Prints status to terminal."""
    print(f"  [{label}]", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FAILED")
        for line in result.stderr.strip().splitlines()[:5]:
            print(f"    stderr: {line}")
        return False, result.stderr
    print("OK")
    # Print informational stderr lines (many scripts write status to stderr)
    for line in result.stderr.strip().splitlines():
        print(f"    {line}")
    return True, result.stdout


# ---------------------------------------------------------------------------
# Digest sections
# ---------------------------------------------------------------------------

def _build_contact_table(contacts: list[dict]) -> list[str]:
    """Shared table renderer for contact lists."""
    lines = [
        "| Name | Last Contact | Platform | 90d Messages |",
        "|------|-------------|----------|-------------|",
    ]
    for p in contacts:
        try:
            dt = datetime.strptime(p["last_contact"], "%Y-%m-%d")
            date_str = dt.strftime("%b %d")
        except ValueError:
            date_str = p["last_contact"]
        lines.append(f"| {p['name']} | {date_str} | {p['platform']} | {p['count_90d']} |")
    lines.append("")
    return lines


def build_this_week_section(results: dict, today: date) -> str:
    """'This Week's Contacts' — CRM + GC contacts communicated with in the last 7 days."""
    cutoff = (today - timedelta(days=7)).isoformat()

    recent = []
    # CRM people
    for name, data in results.get("people", {}).items():
        last = data.get("last_contact")
        if last and last >= cutoff:
            recent.append({
                "name": name,
                "last_contact": last,
                "platform": data.get("last_platform_detected") or "?",
                "count_90d": data.get("contact_count_90d", 0),
                "in_crm": True,
            })
    # GC-known people (in Google Contacts, not yet in CRM JSON)
    for name, data in results.get("gc_known", {}).items():
        last = data.get("last_contact")
        if last and last >= cutoff:
            recent.append({
                "name": name,
                "last_contact": last,
                "platform": data.get("last_platform_detected") or "?",
                "count_90d": data.get("contact_count_90d", 0),
                "in_crm": False,
            })

    recent.sort(key=lambda x: x["last_contact"], reverse=True)

    lines = [
        "### This Week's Contacts",
        "*Who you actually talked to in the last 7 days (★ = in CRM)*",
        "",
    ]

    if not recent:
        lines += ["*No contacts detected in the last 7 days.*", ""]
        return "\n".join(lines)

    lines += [
        "| Name | Last Contact | Platform | 90d Messages |",
        "|------|-------------|----------|-------------|",
    ]
    for p in recent:
        try:
            dt = datetime.strptime(p["last_contact"], "%Y-%m-%d")
            date_str = dt.strftime("%b %d")
        except ValueError:
            date_str = p["last_contact"]
        star = "★ " if p["in_crm"] else ""
        lines.append(f"| {star}{p['name']} | {date_str} | {p['platform']} | {p['count_90d']} |")

    lines.append("")
    return "\n".join(lines)


def build_new_contacts_section(results: dict) -> str:
    """'New Contact Inbox' — people texted/called not in the CRM."""
    new_contacts = results.get("new_contacts", [])

    lines = [
        "### New Contact Inbox",
        "*People you communicate with who aren't in the CRM — add them?*",
        "",
    ]

    if not new_contacts:
        lines += ["*No new contacts detected.*", ""]
        return "\n".join(lines)

    lines += [
        "| Name | Handle | Messages (90d) | Calls (90d) | First Seen |",
        "|------|--------|----------------|-------------|------------|",
    ]
    for nc in new_contacts[:15]:
        handle = nc.get("handle", "?")
        name   = nc.get("name") or "—"
        msgs   = nc.get("message_count_90d", 0)
        calls  = nc.get("call_count_90d", 0)
        first  = nc.get("first_seen", "?")
        lines.append(f"| {name} | `{handle}` | {msgs} | {calls} | {first} |")

    lines.append("")
    return "\n".join(lines)


def build_manual_only_section(results: dict) -> str:
    """Contacts with no phone/email — comm_scan can't track them."""
    manual = results.get("manual_only_contacts", [])
    if not manual:
        return ""

    lines = [
        "### Manual-Only Contacts",
        "*No phone or email in CRM — comm_scan can't auto-track these. Add `iMessage_handle` to enable.*",
        "",
        ", ".join(manual),
        "",
    ]
    return "\n".join(lines)


def build_awaiting_reply_section(results: dict) -> str:
    """'Awaiting Reply' — Dima texted last, no response 3+ days. Different action
    than overdue: a nudge (or letting go), not a fresh reach-out."""
    awaiting = results.get("awaiting_reply", {})
    # Jeannie is household logistics, not social follow-up
    awaiting = {n: d for n, d in awaiting.items() if n != "Jeannie Perkis"}
    if not awaiting:
        return ""
    def nudge_draft(name: str, days: int) -> str:
        first = name.split()[0]
        if days <= 7:
            return f"Bumping this one 👆 no stress either way, {first}"
        if days <= 21:
            return f"Hey {first} — circling back on my last text. Still game?"
        return f"Hey {first}, dropping the old thread — how've you been?"

    lines = [
        "### Awaiting Reply",
        "*You texted last and they haven't answered — nudge or let it go*",
        "",
        "| Person | Your last text | Silent for | Nudge draft |",
        "|--------|---------------|------------|-------------|",
    ]
    for name, d in list(awaiting.items())[:10]:
        lines.append(f"| {name} | {d['since']} | {d['days']}d | {nudge_draft(name, d['days'])} |")
    lines.append("")
    return "\n".join(lines)


def build_availability_section(today: date) -> str:
    """'Availability Flags' — Phase C signals from crm_database.json.

    People flagged available/open are outreach candidates; traveling people
    should be skipped for near-term invites; heads_down = go easy.
    """
    crm_path = Path.home() / "Documents/Brain/02_Areas/Friends/crm_database.json"
    try:
        db = json.loads(crm_path.read_text())
    except Exception:
        return ""

    today_iso = today.isoformat()
    flags = [
        (name, a) for name, entry in db.items()
        if (a := entry.get("availability")) and a.get("expires", "") >= today_iso
    ]
    if not flags:
        return ""

    order = {"open": 0, "available": 1, "traveling": 2, "heads_down": 3}
    flags.sort(key=lambda x: order.get(x[1].get("status"), 9))

    labels = {"open": "🟢 open", "available": "🟢 available",
              "traveling": "✈️ traveling — skip invites", "heads_down": "🔴 heads-down"}
    lines = [
        "### Availability Flags",
        "*From iMessage content (last 30 days, 14-day expiry) — Phase C*",
        "",
        "| Person | Status | Signal | Detected |",
        "|--------|--------|--------|----------|",
    ]
    for name, a in flags:
        note = (a.get("note") or "").replace("|", "\\|")[:80]
        lines.append(f"| {name} | {labels.get(a['status'], a['status'])} | {note} | {a.get('detected','?')} |")
    lines.append("")
    return "\n".join(lines)


def assemble_digest(today: date, comm_results: dict, social_brief: str) -> str:
    """Assemble the full weekly digest markdown."""
    generated_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    crm_total = comm_results.get("crm_total", "?")
    matched = comm_results.get("matched", "?")
    gc_count = comm_results.get("gc_known_count", len(comm_results.get("gc_known", {})))
    new_count = len(comm_results.get("new_contacts", []))

    header = "\n".join([
        f"## Social Digest — Week of {today.strftime('%b %d, %Y')}",
        f"*Generated: {generated_ts} | CRM: {crm_total} ({matched} matched) | GC contacts: {gc_count} | Unknown: {new_count}*",
        "",
        "---",
        "",
    ])

    this_week   = build_this_week_section(comm_results, today)
    new_inbox   = build_new_contacts_section(comm_results)
    manual_only = build_manual_only_section(comm_results)
    awaiting = build_awaiting_reply_section(comm_results)
    availability = build_availability_section(today)

    parts = [header, this_week, awaiting, new_inbox]
    if manual_only:
        parts.append(manual_only)
    if availability:
        parts.append(availability)
    parts.append("---\n")
    parts.append(social_brief.strip())
    parts.append(
        f"\n\n---\n*Generated by weekly_digest.py | "
        f"Sources: comm_scan_results.json + events.json + social_activation_engine.md*\n"
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def empty_results() -> dict:
    return {
        "crm_total": 0, "matched": 0,
        "people": {}, "new_contacts": [], "manual_only_contacts": [],
    }


def main():
    dry_run = "--dry-run" in sys.argv
    no_crm  = "--no-crm"  in sys.argv

    today = date.today()
    mode  = "DRY RUN" if dry_run else ("NO-CRM" if no_crm else "FULL")
    print(f"=== Weekly Social Digest ({today}) [{mode}] ===\n")

    # -------------------------------------------------------------------
    # Step 1: comm_scan
    # -------------------------------------------------------------------
    if no_crm:
        print("  [1/3 comm_scan] Skipped (--no-crm)")
    else:
        # --dry-run: scan only, write results.json, don't touch crm_database.json
        # normal:    scan + write results.json + write back to crm_database.json
        crm_flags = [] if dry_run else ["--write-crm"]
        ok, _ = run_step("1/3 comm_scan", [PYTHON, str(COMM_SCAN)] + crm_flags)
        if not ok and not COMM_RESULTS.exists():
            print("comm_scan failed and no existing results.json — aborting.")
            sys.exit(1)
        elif not ok:
            print("  Using existing comm_scan_results.json (comm_scan failed)")

    # Load comm results
    if COMM_RESULTS.exists():
        with open(COMM_RESULTS) as f:
            comm_results = json.load(f)
    else:
        print("  WARNING: no comm_scan_results.json found — contact sections will be empty")
        comm_results = empty_results()

    # -------------------------------------------------------------------
    # Step 2: export_events
    # -------------------------------------------------------------------
    ok, _ = run_step("2/3 export_events", [PYTHON, str(EXPORT_EVENTS)])
    if not ok:
        print("export_events failed — aborting.")
        sys.exit(1)

    # -------------------------------------------------------------------
    # Step 3: social_scan
    # -------------------------------------------------------------------
    ok, social_brief = run_step("3/3 social_scan", [PYTHON, str(SOCIAL_SCAN)])
    if not ok or not social_brief.strip():
        social_brief = "*social_scan.py failed to run — check SAE file and events.json.*"

    # -------------------------------------------------------------------
    # Assemble + output
    # -------------------------------------------------------------------
    print()
    digest = assemble_digest(today, comm_results, social_brief)

    if dry_run:
        print("=" * 70)
        print(digest)
        print("=" * 70)
        output_path = VAULT_FRIENDS / f"social_digest_{today}.md"
        print(f"\n[DRY RUN] Would write to: {output_path}")
    else:
        output_path = VAULT_FRIENDS / f"social_digest_{today}.md"
        VAULT_FRIENDS.mkdir(parents=True, exist_ok=True)
        output_path.write_text(digest, encoding="utf-8")
        print(f"Digest written → {output_path}")
        print(f"Open in Obsidian: Brain/02_Areas/Friends/social_digest_{today}.md")

    # Print a summary regardless of dry_run
    this_week_count = sum(
        1 for data in comm_results.get("people", {}).values()
        if (data.get("last_contact") or "") >= (today - timedelta(days=7)).isoformat()
    )
    new_count = len(comm_results.get("new_contacts", []))
    print(f"\nSummary: {this_week_count} contacts this week | {new_count} new contact candidates")


if __name__ == "__main__":
    main()
