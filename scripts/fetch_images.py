#!/usr/bin/env python3
"""ATL Events — Image Fetcher (stdlib only, no pip deps)"""
import json
import os
import time
import re
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

PROJECT_DIR = Path("/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site")
IMAGES_DIR = PROJECT_DIR / "images"
SCRIPTS_DIR = PROJECT_DIR / "scripts"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


class OGImageParser(HTMLParser):
    """Extract og:image meta tag from HTML."""
    def __init__(self):
        super().__init__()
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            if d.get("property") == "og:image" and d.get("content"):
                self.og_image = d["content"]


def extract_og_image(url):
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=10) as resp:
            html = resp.read(200_000).decode("utf-8", errors="ignore")
        parser = OGImageParser()
        parser.feed(html)
        return parser.og_image
    except Exception as e:
        print(f"  ⚠️  og:image extraction failed: {e}")
        return None


def get_ext(url):
    low = url.lower()
    for ext in (".png", ".webp", ".gif"):
        if ext in low:
            return ext.lstrip(".")
    return "jpg"


def download_image(url, name):
    if not url:
        return None
    ext = get_ext(url)
    filepath = IMAGES_DIR / f"{name}.{ext}"
    if filepath.exists():
        print(f"  ✓ Cached: {filepath.name}")
        return str(filepath)
    try:
        print(f"  ⬇️  {name}.{ext}...")
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) < 1000:
            print(f"  ⚠️  Tiny file ({len(data)}B), likely placeholder — skipping")
            return None
        with open(filepath, "wb") as f:
            f.write(data)
        print(f"  ✅ {filepath.name} ({len(data)//1024}KB)")
        time.sleep(0.5)
        return str(filepath)
    except (URLError, HTTPError) as e:
        print(f"  ❌ {e}")
    except Exception as e:
        print(f"  ❌ {e}")
    return None


def main():
    print("🎨 ATL Events Image Fetcher\n")
    src_file = SCRIPTS_DIR / "image_sources.json"
    if not src_file.exists():
        print("❌ image_sources.json not found")
        return

    with open(src_file) as f:
        sources = json.load(f)

    ok, fail = 0, 0
    for entry in sources:
        eid, name, urls = entry["id"], entry["name"], entry.get("urls", [])
        print(f"[{eid}] {name}")
        got = False
        for url in urls:
            is_image = any(url.lower().endswith(e) for e in (".jpg", ".png", ".webp", ".gif"))
            if is_image:
                if download_image(url, name):
                    got = True; break
            else:
                print(f"  🔍 Checking og:image...")
                og = extract_og_image(url)
                if og:
                    print(f"  → {og}")
                    if download_image(og, name):
                        got = True; break
                else:
                    print(f"  → No og:image found")
        if got:
            ok += 1
        else:
            fail += 1
        print()

    print(f"{'='*50}\n✅ {ok} downloaded, ❌ {fail} failed\n{'='*50}")


if __name__ == "__main__":
    main()
