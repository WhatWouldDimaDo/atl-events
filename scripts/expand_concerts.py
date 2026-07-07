#!/usr/bin/env python3
"""
expand_concerts.py — Extract concert candidates from prior project CSVs/JSONs.

Reads the Master CSV and batch JSON files, deduplicates, filters to future
events (>= 2026-04-22), removes events already in data.js, and outputs
candidates sorted by date with genre/venue context.

stdlib-only (PEP 668 safe).
"""

import csv
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

CUTOFF = date(2026, 4, 22)
END = date(2026, 9, 30)

EXISTING_JSON = Path(__file__).parent / "events.json"
MASTER_CSV = Path(os.path.expanduser(
    "~/Documents/Coding/Projects/2026-01-24_atl-event-list/"
    "ATL Event List 2025-2026 - Master.csv"
))
BATCH_DIR = Path(os.path.expanduser(
    "~/Documents/Coding/Projects/2026-01-24_atl-event-list/results"
))

# Electronic / interest keywords (boost score)
ELECTRONIC_KEYWORDS = {
    "electronic", "house", "techno", "trance", "dnb", "drum and bass",
    "dubstep", "bass", "edm", "dj", "deep house", "tech house",
    "progressive", "breaks", "jungle", "garage", "ambient", "downtempo",
    "psytrance", "hardstyle", "melodic", "synthwave", "disco", "funk",
    "live electronic", "experimental"
}

# Tier-1 venues that add points
GOOD_VENUES = {
    "the eastern", "terminal west", "district atlanta", "believe music hall",
    "tabernacle", "variety playhouse", "the masquerade", "heaven at the masquerade",
    "hell at the masquerade", "purgatory at the masquerade", "altar at the masquerade",
    "center stage", "buckhead theatre", "atlanta symphony hall",
    "fox theatre", "roxy", "ameris bank amphitheatre", "state farm arena",
    "underground atlanta", "piedmont park", "centennial olympic park",
    "537 lounge", "aisle 5"
}


def load_existing():
    """Load existing event titles for dedup."""
    with open(EXISTING_JSON) as f:
        events = json.load(f)
    titles = set()
    for e in events:
        titles.add(normalize(e["title"]))
        if e.get("subtitle"):
            titles.add(normalize(e["subtitle"]))
    return titles


def normalize(s):
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def parse_date(s):
    """Try common date formats, return date or None."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def read_master_csv():
    """Read Master CSV, return list of event dicts."""
    events = []
    if not MASTER_CSV.exists():
        print(f"  SKIP: {MASTER_CSV} not found")
        return events
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("Event_Name") or "").strip()
            if not title or title.startswith("The Masquerade presents"):
                continue
            d = parse_date(row.get("Start Date", ""))
            if not d:
                continue
            events.append({
                "title": title,
                "venue": (row.get("Venue") or "").strip(),
                "date": d.isoformat(),
                "category": (row.get("Category") or "").strip(),
                "sub_category": (row.get("Sub_Category") or "").strip(),
                "price": (row.get("Price_Range") or "").strip(),
                "family": (row.get("Family_Level") or "").strip(),
                "going": (row.get("Going") or "").strip(),
                "interested": (row.get("Interested") or "").strip(),
                "source": "master_csv"
            })
    return events


def read_batch_jsons():
    """Read batch JSON files from results/, return list of event dicts."""
    events = []
    if not BATCH_DIR.exists():
        print(f"  SKIP: {BATCH_DIR} not found")
        return events
    for fname in sorted(BATCH_DIR.glob("batch_*.json")):
        try:
            with open(fname) as f:
                data = json.load(f)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("events", data.get("results", []))
            else:
                continue
            for item in items:
                title = (item.get("event_name") or item.get("Event_Name") or "").strip()
                if not title or title.startswith("The Masquerade presents"):
                    continue
                d = parse_date(
                    item.get("start_date") or item.get("date") or ""
                )
                if not d:
                    continue
                events.append({
                    "title": title,
                    "venue": (item.get("venue") or item.get("Venue") or "").strip(),
                    "date": d.isoformat(),
                    "category": (item.get("category") or "").strip(),
                    "sub_category": (item.get("sub_category") or "").strip(),
                    "price": (item.get("price_range") or "").strip(),
                    "ticket_link": (item.get("ticket_link") or "").strip(),
                    "description": (item.get("description") or "").strip(),
                    "image_url": (item.get("image_url") or "").strip(),
                    "source": fname.name
                })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  WARN: {fname.name}: {e}")
    return events


def score_candidate(ev):
    """Rough interest score based on venue, genre keywords, markings."""
    s = 50  # baseline
    venue_norm = normalize(ev.get("venue", ""))
    if venue_norm in GOOD_VENUES:
        s += 15

    text = " ".join([
        ev.get("title", ""), ev.get("category", ""),
        ev.get("sub_category", ""), ev.get("description", "")
    ]).lower()

    for kw in ELECTRONIC_KEYWORDS:
        if kw in text:
            s += 10
            break

    if ev.get("going", "").lower() in ("yes", "true", "1"):
        s += 20
    if ev.get("interested", "").lower() in ("yes", "true", "1"):
        s += 10

    return min(s, 100)


def main():
    existing = load_existing()
    print(f"Existing events: {len(existing)} titles")

    # Gather all candidates
    all_events = read_master_csv() + read_batch_jsons()
    print(f"Raw events from sources: {len(all_events)}")

    # Filter: future, within range, not existing
    seen = set()
    candidates = []
    for ev in all_events:
        d = parse_date(ev["date"])
        if not d or d < CUTOFF or d > END:
            continue
        key = (normalize(ev["title"]), ev["date"])
        if key in seen:
            continue
        if normalize(ev["title"]) in existing:
            continue
        seen.add(key)
        ev["interest_score"] = score_candidate(ev)
        candidates.append(ev)

    # Sort by interest score desc, then date
    candidates.sort(key=lambda e: (-e["interest_score"], e["date"]))

    print(f"\nFuture candidates (after dedup): {len(candidates)}")
    print(f"Date range: {CUTOFF} to {END}\n")

    # Print top candidates
    print(f"{'Score':>5} | {'Date':>10} | {'Title':<40} | {'Venue':<30} | {'Cat'}")
    print("-" * 120)
    for ev in candidates:
        cat = ev.get("sub_category") or ev.get("category") or ""
        print(f"{ev['interest_score']:>5} | {ev['date']:>10} | {ev['title'][:40]:<40} | {ev['venue'][:30]:<30} | {cat}")

    # Save full list
    out_path = Path(__file__).parent / "concert_candidates.json"
    with open(out_path, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"\nSaved {len(candidates)} candidates to {out_path}")


if __name__ == "__main__":
    main()
