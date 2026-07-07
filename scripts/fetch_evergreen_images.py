#!/usr/bin/env python3
"""
Download images for all evergreen activities.
Stdlib only: urllib, html.parser, json, re, os, time, ssl, pathlib
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).parent.parent
EXPORT_JSON = BASE_DIR / "scripts" / "evergreen_export.json"
OUT_DIR = BASE_DIR / "images" / "evergreen"
RESULTS_JSON = BASE_DIR / "scripts" / "evergreen_image_results.json"
DELAY = 0.3
MIN_BYTES = 1024  # skip placeholders < 1 KB

# Venue branding logos (name → logo URL)
VENUE_LOGOS = {
    "The Eastern": "https://storage.googleapis.com/cms-org.media.aegpresents.com/venue-rentals/logos/the-eastern.png",
    "Terminal West": "https://storage.googleapis.com/cms-org.media.aegpresents.com/venue-rentals/logos/terminal-west.png",
    "Variety Playhouse": "https://storage.googleapis.com/cms-org.media.aegpresents.com/venue-rentals/logos/variety-playhouse.png",
    "The Masquerade": "https://www.masqueradeatlanta.com/wp-content/uploads/2017/10/Logo-Horizontal.png",
    "Tabernacle": "https://assets.livenationcdn.com/uploads/ab900d16-3b3f-4ae9-b914-fcc4d94baeff.png",
    "District Atlanta": "https://districtatlanta.com/images/logo.png",
    "Believe Music Hall": "https://believeatl.com/wp-content/uploads/2023/07/Believe-Logo.png",
    "High Museum of Art": "https://highmuseum-redesign.s3.amazonaws.com/uploads/2022/07/high-logo.svg",
    "Fernbank Museum": "https://fernbankmuseum.org/media/kugpki3e/fmnh_logorefresh_final_full_color.svg",
    "Atlanta Botanical Garden": "https://atlantabg.org/wp-content/uploads/2018/07/logo.svg",
}

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def make_request(url: str, timeout: int = 15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )
    return urllib.request.urlopen(req, context=ssl_ctx(), timeout=timeout)


class OGImageParser(HTMLParser):
    """Extract og:image content from HTML."""

    def __init__(self):
        super().__init__()
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            prop = d.get("property", "") or d.get("name", "")
            if prop == "og:image" and "content" in d:
                self.og_image = d["content"]


def fetch_og_image(url: str) -> str | None:
    """Fetch a URL and return its og:image value, or None."""
    try:
        resp = make_request(url)
        # Only read up to 500KB to find the <head>
        raw = resp.read(500_000)
        html = raw.decode("utf-8", errors="replace")
        parser = OGImageParser()
        parser.feed(html)
        return parser.og_image
    except Exception as e:
        print(f"    [warn] fetch_og_image({url}): {e}")
        return None


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].split("#")[0]
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


def download_image(url: str, dest: Path) -> bool:
    """Download image to dest. Returns True on success."""
    try:
        resp = make_request(url, timeout=20)
        data = resp.read()
        if len(data) < MIN_BYTES:
            print(f"    [skip] too small ({len(data)} bytes): {url}")
            return False
        dest.write_bytes(data)
        print(f"    [ok] {dest.name} ({len(data):,} bytes)")
        return True
    except Exception as e:
        print(f"    [err] download {url}: {e}")
        return False


def find_existing(slug: str) -> Path | None:
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        p = OUT_DIR / f"{slug}{ext}"
        if p.exists() and p.stat().st_size >= MIN_BYTES:
            return p
    return None


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = json.loads(EXPORT_JSON.read_text())
    print(f"Processing {len(entries)} evergreen entries…\n")

    results = {}
    success = 0
    skipped_existing = 0
    failed = 0

    for entry in entries:
        eid = entry["id"]
        name = entry["name"]
        url = entry.get("url", "")
        slug = slugify(name)

        print(f"[{eid}] {name}")

        # 1. Already downloaded?
        existing = find_existing(slug)
        if existing:
            print(f"    [cached] {existing.name}")
            results[eid] = f"images/evergreen/{existing.name}"
            skipped_existing += 1
            continue

        image_url = None
        dest_path = None

        # 2. Venue branding logo?
        if name in VENUE_LOGOS:
            logo_url = VENUE_LOGOS[name]
            # SVG → try og:image from website instead
            if logo_url.lower().endswith(".svg"):
                print(f"    [svg logo] trying og:image from {url}")
                og = fetch_og_image(url)
                if og and not og.lower().endswith(".svg"):
                    image_url = og
                else:
                    print(f"    [skip] no raster alternative for SVG logo")
                    failed += 1
                    continue
            else:
                image_url = logo_url
        elif url:
            # 3. Fetch og:image from entry's URL
            print(f"    fetching og:image from {url}")
            og = fetch_og_image(url)
            if og:
                if og.lower().endswith(".svg"):
                    print(f"    [skip] og:image is SVG: {og}")
                    failed += 1
                    time.sleep(DELAY)
                    continue
                image_url = og
            else:
                print(f"    [warn] no og:image found")
                failed += 1
                time.sleep(DELAY)
                continue
        else:
            print(f"    [skip] no URL")
            failed += 1
            continue

        # Build destination path
        ext = ext_from_url(image_url)
        dest_path = OUT_DIR / f"{slug}{ext}"

        ok = download_image(image_url, dest_path)
        if ok:
            results[eid] = f"images/evergreen/{dest_path.name}"
            success += 1
        else:
            failed += 1

        time.sleep(DELAY)

    # Write results
    RESULTS_JSON.write_text(json.dumps(results, indent=2))

    print(f"\n--- Results ---")
    print(f"  Newly downloaded : {success}")
    print(f"  Already cached   : {skipped_existing}")
    print(f"  Failed / skipped : {failed}")
    print(f"  Total with image : {success + skipped_existing} / {len(entries)}")
    print(f"\nResults written to {RESULTS_JSON}")


if __name__ == "__main__":
    main()
