#!/usr/bin/env python3
"""enrich_events.py — Fill ticket URLs and images for ATL Events.

Three modes:
  --audit   Identify gaps, print report, write scripts/enrichment_config.json
  --fetch   Fetch og:images from officialUrls, set free-event ticketUrls,
            extract ticket links from event pages. Writes scripts/enrichment_results.json
  --apply   Patch data.js with enrichment_results.json

Stdlib only — no pip deps.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
IMAGES_DIR = PROJECT_DIR / "images"
EVENTS_JSON = SCRIPTS_DIR / "events.json"
DATA_JS = PROJECT_DIR / "data.js"
CONFIG_JSON = SCRIPTS_DIR / "enrichment_config.json"
RESULTS_JSON = SCRIPTS_DIR / "enrichment_results.json"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# SSL context that doesn't verify (some event sites have bad certs)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# HTML Parsers
# ---------------------------------------------------------------------------

class OGImageParser(HTMLParser):
    """Extract og:image from <meta> tags."""
    def __init__(self):
        super().__init__()
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            if d.get("property") == "og:image" and d.get("content"):
                self.og_image = d["content"]


class TicketLinkParser(HTMLParser):
    """Extract ticket/buy links from a page."""
    TICKET_PATTERNS = re.compile(
        r"(ticket|buy|book|register|rsvp|eventbrite|axs\.com|ticketmaster|"
        r"dice\.fm|seetickets|tixr|universe\.com|showclix|etix|simpletix)",
        re.IGNORECASE,
    )

    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = None
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            href = d.get("href", "")
            self._in_a = True
            self._href = href
            self._text = ""
            # Check href itself
            if href and self.TICKET_PATTERNS.search(href):
                self.links.append(href)

    def handle_data(self, data):
        if self._in_a:
            self._text += data

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            # Check link text
            if self._href and self.TICKET_PATTERNS.search(self._text):
                if self._href not in self.links:
                    self.links.append(self._href)
            self._in_a = False


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_page(url, max_bytes=500_000):
    """Fetch a page, return HTML string or None."""
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=15, context=CTX) as resp:
            return resp.read(max_bytes).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    fetch failed: {e}")
        return None


def extract_og_image(html):
    """Extract og:image URL from HTML."""
    parser = OGImageParser()
    parser.feed(html)
    return parser.og_image


def extract_ticket_links(html):
    """Extract ticket/purchase links from HTML."""
    parser = TicketLinkParser()
    parser.feed(html)
    return parser.links


def get_ext(url):
    low = url.lower().split("?")[0]
    for ext in (".png", ".webp", ".gif", ".jpeg"):
        if ext in low:
            return ext.lstrip(".")
    return "jpg"


def slugify(name):
    """Convert event title to filename slug."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def download_image(url, name):
    """Download image to images/ dir. Returns relative path or None."""
    if not url:
        return None
    ext = get_ext(url)
    slug = slugify(name)
    filepath = IMAGES_DIR / f"{slug}.{ext}"
    if filepath.exists():
        print(f"    cached: {filepath.name}")
        return f"images/{filepath.name}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=20, context=CTX) as resp:
            data = resp.read()
        if len(data) < 1000:
            print(f"    tiny file ({len(data)}B), skipping")
            return None
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"    saved {filepath.name} ({len(data) // 1024}KB)")
        return f"images/{filepath.name}"
    except Exception as e:
        print(f"    download failed: {e}")
        return None


# ---------------------------------------------------------------------------
# --audit
# ---------------------------------------------------------------------------

def audit(events):
    """Print gap report and write enrichment_config.json."""
    missing_ticket = []
    missing_image = []
    missing_official = []
    free_no_ticket = []

    for e in events:
        eid = e["id"]
        has_ticket = bool(e.get("ticketUrl"))
        has_image = bool(e.get("imageUrl"))
        has_official = bool(e.get("officialUrl"))
        is_free = bool(e.get("free"))

        if not has_ticket:
            if is_free and has_official:
                free_no_ticket.append(e)
            else:
                missing_ticket.append(e)
        if not has_image:
            missing_image.append(e)
        if not has_official:
            missing_official.append(e)

    print(f"\n{'='*60}")
    print(f"ENRICHMENT AUDIT — {len(events)} events")
    print(f"{'='*60}")

    print(f"\nFree events (set ticketUrl = officialUrl): {len(free_no_ticket)}")
    for e in free_no_ticket:
        print(f"  [{e['id']:2d}] {e['title']} → {e['officialUrl']}")

    print(f"\nMissing ticketUrl (non-free): {len(missing_ticket)}")
    for e in missing_ticket:
        src = e.get("officialUrl") or e.get("instagramUrl") or "NO URL"
        print(f"  [{e['id']:2d}] {e['title']} — {e['venue']} — src: {src}")

    print(f"\nMissing imageUrl: {len(missing_image)}")
    for e in missing_image:
        src = e.get("officialUrl") or "NO officialUrl"
        print(f"  [{e['id']:2d}] {e['title']} — src: {src}")

    print(f"\nMissing officialUrl: {len(missing_official)}")
    for e in missing_official:
        print(f"  [{e['id']:2d}] {e['title']} — {e['venue']}")

    # --- V3 #7: flag YouTube-thumbnail fallback images (recurring audit) ---
    yt_fallback = [
        e for e in events
        if e.get("imageUrl") and ("youtube" in e["imageUrl"].lower()
                                  or e["imageUrl"].lower().endswith("_yt.jpg"))
    ]
    print(f"\nYouTube-thumbnail fallback images (replace with real flyers): {len(yt_fallback)}")
    for e in yt_fallback:
        print(f"  [{e['id']:2d}] {e['title']} — {e['imageUrl']}")
    print("  (note: fallbacks downloaded before 2026-07-06 lack the _yt marker "
          "and can't be auto-detected)")

    # --- V3 #6: ticket availability for advancePurchase/urgent events ---
    check_events = [e for e in events if e.get("advancePurchase") or e.get("urgent")]
    print(f"\nadvancePurchase/urgent events with ticketUrl: "
          f"{sum(1 for e in check_events if e.get('ticketUrl'))}/{len(check_events)}")
    if "--check-tickets" in sys.argv:
        print("Checking ticket link availability (skips AXS 403 / Ticketmaster 401)...")
        soldout_rx = re.compile(r"sold\s*out|off\s*sale|no longer available|not available",
                                re.IGNORECASE)
        for e in check_events:
            url = e.get("ticketUrl")
            if not url:
                continue
            if "axs.com" in url or "ticketmaster" in url or "livenation" in url:
                print(f"  [{e['id']:2d}] {e['title']} — SKIP (platform blocks scraping)")
                continue
            html = fetch_page(url)
            if html is None:
                print(f"  [{e['id']:2d}] {e['title']} — UNREACHABLE: {url[:60]}")
            elif soldout_rx.search(html):
                print(f"  [{e['id']:2d}] {e['title']} — ⚠️ SOLD OUT / OFF SALE signal")
            else:
                print(f"  [{e['id']:2d}] {e['title']} — ok")
            time.sleep(0.5)
    else:
        print("  (pass --check-tickets to probe ticket links live)")

    # Write config
    config = {
        "yt_fallback_images": [{"id": e["id"], "title": e["title"],
                                "imageUrl": e["imageUrl"]} for e in yt_fallback],
        "free_events": [{"id": e["id"], "title": e["title"],
                         "officialUrl": e["officialUrl"]} for e in free_no_ticket],
        "missing_ticket": [{"id": e["id"], "title": e["title"],
                            "venue": e["venue"],
                            "officialUrl": e.get("officialUrl"),
                            "instagramUrl": e.get("instagramUrl")}
                           for e in missing_ticket],
        "missing_image": [{"id": e["id"], "title": e["title"],
                           "officialUrl": e.get("officialUrl")}
                          for e in missing_image],
        "missing_official": [{"id": e["id"], "title": e["title"],
                              "venue": e["venue"]}
                             for e in missing_official],
    }
    CONFIG_JSON.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nWrote {CONFIG_JSON.name}")
    print(f"\nSummary:")
    print(f"  ticketUrl:   {sum(1 for e in events if e.get('ticketUrl'))}/{len(events)}")
    print(f"  imageUrl:    {sum(1 for e in events if e.get('imageUrl'))}/{len(events)}")
    print(f"  officialUrl: {sum(1 for e in events if e.get('officialUrl'))}/{len(events)}")


# ---------------------------------------------------------------------------
# --fetch
# ---------------------------------------------------------------------------

def fetch(events):
    """Fetch enrichment data. Writes enrichment_results.json."""
    config = json.loads(CONFIG_JSON.read_text()) if CONFIG_JSON.exists() else None
    if not config:
        print("Run --audit first to generate enrichment_config.json")
        return

    results = {}  # id -> {ticketUrl, imageUrl, officialUrl}

    # Phase 1: Free events — ticketUrl = officialUrl
    print("\n--- Phase 1: Free events (instant) ---")
    for entry in config["free_events"]:
        eid = entry["id"]
        results[str(eid)] = {"ticketUrl": entry["officialUrl"]}
        print(f"  [{eid}] {entry['title']} → ticketUrl = officialUrl")

    # Phase 2: og:image extraction from officialUrl
    print("\n--- Phase 2: og:image from officialUrl ---")
    for entry in config["missing_image"]:
        eid = entry["id"]
        url = entry.get("officialUrl")
        if not url:
            print(f"  [{eid}] {entry['title']} — no officialUrl, skipping")
            continue
        print(f"  [{eid}] {entry['title']} — fetching {url}")
        html = fetch_page(url)
        if not html:
            continue
        og = extract_og_image(html)
        if og:
            print(f"    og:image found: {og[:80]}")
            # Find event title for slug
            ev = next((e for e in events if e["id"] == eid), None)
            title = ev["title"] if ev else entry["title"]
            local_path = download_image(og, title)
            if local_path:
                r = results.setdefault(str(eid), {})
                r["imageUrl"] = local_path
        else:
            print(f"    no og:image found")
        time.sleep(0.5)

    # Phase 3: Ticket link extraction from officialUrl
    print("\n--- Phase 3: Ticket links from officialUrl ---")
    for entry in config["missing_ticket"]:
        eid = entry["id"]
        url = entry.get("officialUrl")
        if not url:
            continue
        # Skip if we already found a ticket URL for this event
        if results.get(str(eid), {}).get("ticketUrl"):
            continue
        ev = next((e for e in events if e["id"] == eid), None)
        if ev and ev.get("free"):
            continue
        print(f"  [{eid}] {entry['title']} — scanning {url}")
        html = fetch_page(url)
        if not html:
            continue
        links = extract_ticket_links(html)
        if links:
            # Prefer external ticket platform links over self-links
            best = None
            for link in links:
                if any(p in link.lower() for p in
                       ["eventbrite", "axs.com", "ticketmaster", "dice.fm",
                        "tixr", "seetickets", "etix", "simpletix", "universe.com"]):
                    best = link
                    break
            if not best:
                # Use first ticket-looking link that's a full URL
                for link in links:
                    if link.startswith("http"):
                        best = link
                        break
            if best:
                print(f"    ticket link: {best[:80]}")
                r = results.setdefault(str(eid), {})
                r["ticketUrl"] = best
            else:
                print(f"    found {len(links)} links but none external")
        else:
            print(f"    no ticket links found")
        time.sleep(0.5)

    # Phase 4: For events with no officialUrl — try YouTube-based image
    print("\n--- Phase 4: YouTube thumbnail fallback ---")
    for entry in config["missing_image"]:
        eid = str(entry["id"])
        if results.get(eid, {}).get("imageUrl"):
            continue  # already got an image
        ev = next((e for e in events if e["id"] == entry["id"]), None)
        if not ev:
            continue
        yt = ev.get("youtubeId")
        if yt:
            yt_url = f"https://img.youtube.com/vi/{yt}/maxresdefault.jpg"
            print(f"  [{entry['id']}] {entry['title']} — trying YouTube thumbnail")
            # "_yt" suffix marks the file as a thumbnail fallback so --audit
            # can flag it for replacement with a real flyer later
            local = download_image(yt_url, ev["title"] + " yt")
            if local:
                r = results.setdefault(eid, {})
                r["imageUrl"] = local

    # Write results
    RESULTS_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Enrichment results: {len(results)} events updated")
    ticket_count = sum(1 for r in results.values() if r.get("ticketUrl"))
    image_count = sum(1 for r in results.values() if r.get("imageUrl"))
    print(f"  New ticketUrls: {ticket_count}")
    print(f"  New imageUrls:  {image_count}")
    print(f"Wrote {RESULTS_JSON.name}")


# ---------------------------------------------------------------------------
# --apply
# ---------------------------------------------------------------------------

def patch_event_field(js, eid, field, value):
    """Patch a single field in a specific event block — safe for out-of-order IDs.

    data.js events are NOT in strict ID order (confirmed misfire Jul 2026:
    st_lucia.jpg landed on Magic for Adults via cross-boundary DOTALL regex).
    This scopes the substitution to the block between `id: N,` and the next
    event/array boundary. See ENRICHMENT-METHODOLOGY.md "Apply Phase".
    """
    m = re.search(rf'(?<!\d)id:\s*{eid},', js)
    if not m:
        return js, False
    start = m.start()
    next_event = re.search(r'\n  [{\]]', js[start + 10:])
    end = start + 10 + next_event.start() if next_event else len(js)
    block = js[start:end]
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    new_block, n = re.subn(
        rf"({re.escape(field)}:\s*)(?:null|'[^']*'|\"[^\"]*\")",
        lambda mm: f"{mm.group(1)}'{escaped}'",
        block, count=1,
    )
    return js[:start] + new_block + js[end:], n > 0


def export_snapshot():
    """Run export_events.py and return {id: event} from the fresh events.json."""
    rc = os.system(f"cd {PROJECT_DIR} && python3 scripts/export_events.py > /dev/null")
    if rc != 0:
        raise RuntimeError("export_events.py failed")
    return {e["id"]: e for e in json.loads(EVENTS_JSON.read_text())}


VALIDATED_FIELDS = ("imageUrl", "ticketUrl", "officialUrl", "youtubeId", "instagramUrl")


def apply_results():
    """Patch data.js with enrichment_results.json — block-scoped + validated.

    Validation (mandatory): snapshot events.json before, re-export after, then
    assert that among VALIDATED_FIELDS the ONLY changes are exactly the
    intended (id, field, value) triples. Any change on an event id that was
    not in the patch list restores data.js from backup and exits non-zero.
    """
    if not RESULTS_JSON.exists():
        print("No enrichment_results.json found. Run --fetch first.")
        return

    results = json.loads(RESULTS_JSON.read_text())
    if not results:
        print("No results to apply.")
        return

    before = export_snapshot()

    js_text = DATA_JS.read_text(encoding="utf-8")
    backup = DATA_JS.with_suffix(".js.pre-apply.bak")
    backup.write_text(js_text, encoding="utf-8")

    intended = {}  # (id, field) -> value
    patched = 0
    for eid_str, fields in results.items():
        eid = int(eid_str)
        for field, value in fields.items():
            if not value:
                continue
            js_text, ok = patch_event_field(js_text, eid, field, value)
            if ok:
                intended[(eid, field)] = value
                patched += 1
                print(f"  [{eid}] {field} = '{value[:60]}'")
            else:
                print(f"  [{eid}] {field} — MISS (id or field not found in data.js)")

    DATA_JS.write_text(js_text, encoding="utf-8")
    print(f"\nPatched {patched} fields in data.js")

    # --- mandatory post-apply validation ---
    print("Validating: re-exporting events.json and diffing tracked fields...")
    after = export_snapshot()
    errors = []
    for eid in set(before) | set(after):
        b, a = before.get(eid), after.get(eid)
        if b is None or a is None:
            errors.append(f"event id {eid} appeared/disappeared during apply")
            continue
        for field in VALIDATED_FIELDS:
            bv, av = b.get(field), a.get(field)
            if bv == av:
                if (eid, field) in intended and av != intended[(eid, field)]:
                    errors.append(f"[{eid}] {field}: intended change did not take "
                                  f"(still {av!r})")
                continue
            want = intended.get((eid, field))
            if want is None:
                errors.append(f"[{eid}] {field} changed UNINTENDED: {bv!r} -> {av!r}")
            elif av != want:
                errors.append(f"[{eid}] {field}: wrong value {av!r} (wanted {want!r})")

    if errors:
        print("\n*** VALIDATION FAILED — restoring data.js from backup ***")
        for err in errors:
            print(f"  ✗ {err}")
        DATA_JS.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        export_snapshot()  # restore events.json to match
        sys.exit(1)

    backup.unlink()
    print(f"Validation passed: {len(intended)} intended changes, 0 unintended.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ATL Events enrichment pipeline")
    parser.add_argument("--audit", action="store_true", help="Identify gaps")
    parser.add_argument("--fetch", action="store_true", help="Fetch enrichment data")
    parser.add_argument("--apply", action="store_true", help="Apply results to data.js")
    args = parser.parse_args()

    if not any([args.audit, args.fetch, args.apply]):
        parser.print_help()
        return

    if args.audit or args.fetch:
        events = json.loads(EVENTS_JSON.read_text())

    if args.audit:
        audit(events)
    if args.fetch:
        fetch(events)
    if args.apply:
        apply_results()


if __name__ == "__main__":
    main()
