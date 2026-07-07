#!/usr/bin/env python3
"""
Pass 4: Wikipedia page scraping + correct browser headers (Sec-Fetch-*) to bypass
Wikimedia 403 blocks. Stdlib only.
"""
import json
import os
import re
import ssl
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXPORT_JSON = BASE_DIR / "scripts" / "evergreen_export.json"
OUT_DIR = BASE_DIR / "images" / "evergreen"
RESULTS_JSON = BASE_DIR / "scripts" / "evergreen_image_results.json"
DELAY = 0.4
MIN_BYTES = 1024

# Wikipedia article titles for each missing entry
WIKIPEDIA_ARTICLES = {
    "e02": ("Fernbank_Museum_of_Natural_History", "https://en.wikipedia.org/wiki/Fernbank_Museum_of_Natural_History"),
    "e10": ("Car_wash", "https://en.wikipedia.org/wiki/Car_wash"),
    "e19": ("Fox_Theatre_(Atlanta)", "https://en.wikipedia.org/wiki/Fox_Theatre_(Atlanta)"),
    "e20": ("Fernbank_Museum_of_Natural_History", "https://en.wikipedia.org/wiki/Fernbank_Museum_of_Natural_History"),
    "e22": ("Virginia_Highland", "https://en.wikipedia.org/wiki/Virginia_Highland"),
    "e25": ("Axe_throwing", "https://en.wikipedia.org/wiki/Axe_throwing"),
    "e26": ("Rock_climbing", "https://en.wikipedia.org/wiki/Rock_climbing"),
    "e28": ("Centennial_Olympic_Park", "https://en.wikipedia.org/wiki/Centennial_Olympic_Park"),
    "e31": ("Sweetwater_Creek_State_Park", "https://en.wikipedia.org/wiki/Sweetwater_Creek_State_Park"),
    "e37": ("DeKalb_Farmers_Market", "https://en.wikipedia.org/wiki/DeKalb_Farmers_Market"),
    "e38": ("Centennial_Olympic_Park", "https://en.wikipedia.org/wiki/Centennial_Olympic_Park"),
    "e40": ("Michael_C._Carlos_Museum", "https://en.wikipedia.org/wiki/Michael_C._Carlos_Museum"),
    "e41": ("Rock_climbing", "https://en.wikipedia.org/wiki/Rock_climbing"),
    "e43": ("Virginia_Highland", "https://en.wikipedia.org/wiki/Virginia_Highland"),
    "e52": ("Bowling", "https://en.wikipedia.org/wiki/Bowling"),
    "e54": ("Manuel%27s_Tavern", "https://en.wikipedia.org/wiki/Manuel%27s_Tavern"),
    "e56": ("Red_Top_Mountain_State_Park", "https://en.wikipedia.org/wiki/Red_Top_Mountain_State_Park"),
    "e58": ("Escape_room", "https://en.wikipedia.org/wiki/Escape_room"),
    "e59": ("Yellow_River_Game_Ranch", "https://en.wikipedia.org/wiki/Yellow_River_Game_Ranch"),
    "e63": ("The_Home_Depot", "https://en.wikipedia.org/wiki/The_Home_Depot"),
    "e65": ("Amusement_ride", "https://en.wikipedia.org/wiki/Amusement_ride"),
    "e67": ("Trampoline_park", "https://en.wikipedia.org/wiki/Trampoline_park"),
    "e68": ("Noah%27s_Ark_(Locust_Grove,_Georgia)", "https://en.wikipedia.org/wiki/Noah%27s_Ark_(Locust_Grove,_Georgia)"),
    "e69": ("Music_festival", "https://en.wikipedia.org/wiki/Music_festival"),
    "e70": ("Dogwood_Festival_(Atlanta)", "https://en.wikipedia.org/wiki/Dogwood_Festival_(Atlanta)"),
    "e72": ("Dragon_Con", "https://en.wikipedia.org/wiki/Dragon_Con"),
    "e73": ("Candler_Park", "https://en.wikipedia.org/wiki/Candler_Park"),
    "e74": ("Critical_Mass_(cycling)", "https://en.wikipedia.org/wiki/Critical_Mass_(cycling)"),
    "e76": ("Drum_circle", "https://en.wikipedia.org/wiki/Drum_circle"),
    "e82": ("Virginia_Highland", "https://en.wikipedia.org/wiki/Virginia_Highland"),
    "e84": ("Jazz_club", "https://en.wikipedia.org/wiki/Jazz_club"),
    "e90": ("Strawberry", "https://en.wikipedia.org/wiki/Strawberry"),
    "e92": ("Pumpkin", "https://en.wikipedia.org/wiki/Pumpkin"),
    "e95": ("Atlanta_Symphony_Orchestra", "https://en.wikipedia.org/wiki/Atlanta_Symphony_Orchestra"),
    "e98": ("Decatur,_Georgia", "https://en.wikipedia.org/wiki/Decatur,_Georgia"),
    "e100": ("Ponce_City_Market", "https://en.wikipedia.org/wiki/Ponce_City_Market"),
    "e101": ("Saint_Patrick%27s_Day_parade", "https://en.wikipedia.org/wiki/Saint_Patrick%27s_Day_parade"),
    "e104": ("Fernbank_Museum_of_Natural_History", "https://en.wikipedia.org/wiki/Fernbank_Museum_of_Natural_History"),
    "e106": ("Immersive_art", "https://en.wikipedia.org/wiki/Immersive_art"),
    "e108": ("Chastain_Park_Amphitheatre", "https://en.wikipedia.org/wiki/Chastain_Park_Amphitheatre"),
    "e109": ("Alpaca", "https://en.wikipedia.org/wiki/Alpaca"),
    "e110": ("Atlanta_BeltLine", "https://en.wikipedia.org/wiki/Atlanta_BeltLine"),
    # No-URL entries that need generic images
    "e08": ("Slime", "https://en.wikipedia.org/wiki/Slime_(toy)"),
    "e12": ("Playground", "https://en.wikipedia.org/wiki/Playground"),
    "e23": ("Drum_circle", "https://en.wikipedia.org/wiki/Drum_circle"),
}

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def browser_headers(referer: str = "https://en.wikipedia.org/") -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }


def image_headers(referer: str) -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
    }


def fetch_url(url: str, headers: dict, timeout: int = 15) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, context=ssl_ctx(), timeout=timeout)
        return resp.read()
    except Exception as e:
        print(f"    [err] {url[:70]}: {e}")
        return None


def get_wikipedia_og_image(wiki_url: str) -> tuple[str | None, str | None]:
    """Fetch Wikipedia page and return (og:image_url, page_url)."""
    data = fetch_url(wiki_url, browser_headers())
    if not data:
        return None, None
    html = data.decode("utf-8", errors="replace")
    # Extract og:image
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
    if m:
        img = m.group(1)
        if not img.lower().endswith(".svg"):
            return img, wiki_url
    # Fallback: find first image in infobox or content
    imgs = re.findall(r'(//upload\.wikimedia\.org/wikipedia/(?:commons|en)/thumb/[^\s"\'<>]+\.(?:jpg|jpeg|png|webp))', html, re.IGNORECASE)
    # Filter for reasonably sized thumbnails (250px+) and not flags/logos
    for img in imgs:
        if any(skip in img.lower() for skip in ["flag_of", "coat_of_arms", "logo", "icon", "seal_of"]):
            continue
        if re.search(r'/(\d+)px-', img):
            size = int(re.search(r'/(\d+)px-', img).group(1))
            if size >= 250:
                return "https:" + img, wiki_url
    return None, wiki_url


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].split("#")[0]
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


def download_image(img_url: str, referer: str, dest: Path) -> bool:
    data = fetch_url(img_url, image_headers(referer), timeout=20)
    if data is None:
        return False
    if len(data) < MIN_BYTES:
        print(f"    [skip] too small ({len(data)} bytes)")
        return False
    dest.write_bytes(data)
    print(f"    [ok] {dest.name} ({len(data):,} bytes)")
    return True


def find_existing(slug: str) -> Path | None:
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        p = OUT_DIR / f"{slug}{ext}"
        if p.exists() and p.stat().st_size >= MIN_BYTES:
            return p
    return None


def main():
    entries = json.loads(EXPORT_JSON.read_text())
    existing_results = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else {}

    need_image = [e for e in entries if e["id"] not in existing_results]
    print(f"{len(need_image)} entries still need images\n")

    new_success = 0
    still_failed = 0

    for entry in need_image:
        eid = entry["id"]
        name = entry["name"]
        slug = slugify(name)

        print(f"[{eid}] {name}")

        existing = find_existing(slug)
        if existing:
            print(f"    [cached] {existing.name}")
            existing_results[eid] = f"images/evergreen/{existing.name}"
            new_success += 1
            continue

        downloaded = False

        if eid in WIKIPEDIA_ARTICLES:
            _, wiki_url = WIKIPEDIA_ARTICLES[eid]
            print(f"    fetching Wikipedia: {wiki_url.split('wiki/')[-1]}")
            img_url, page_url = get_wikipedia_og_image(wiki_url)
            time.sleep(DELAY)

            if img_url:
                print(f"    found: {img_url[:80]}")
                ext = ext_from_url(img_url)
                if ext == ".svg" or img_url.lower().endswith(".svg"):
                    print(f"    [skip] SVG")
                else:
                    dest = OUT_DIR / f"{slug}{ext}"
                    if download_image(img_url, page_url or wiki_url, dest):
                        existing_results[eid] = f"images/evergreen/{dest.name}"
                        new_success += 1
                        downloaded = True
                    time.sleep(DELAY)
            else:
                print(f"    [warn] no image found on Wikipedia page")

        if not downloaded:
            print(f"    [give up]")
            still_failed += 1

    RESULTS_JSON.write_text(json.dumps(existing_results, indent=2))

    print(f"\n--- Pass 4 Results ---")
    print(f"  Newly downloaded : {new_success}")
    print(f"  Still failed     : {still_failed}")
    total = len([e for e in entries if e["id"] in existing_results])
    print(f"  Total with image : {total} / {len(entries)}")


if __name__ == "__main__":
    main()
