#!/usr/bin/env python3
"""
Second pass: try alternate URLs for evergreen entries that failed in pass 1.
Stdlib only.
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXPORT_JSON = BASE_DIR / "scripts" / "evergreen_export.json"
OUT_DIR = BASE_DIR / "images" / "evergreen"
RESULTS_JSON = BASE_DIR / "scripts" / "evergreen_image_results.json"
DELAY = 0.4
MIN_BYTES = 1024

# --------------------------------------------------------------------------- #
# Alternate / fallback URLs for specific entries
# --------------------------------------------------------------------------- #
ALTERNATE_URLS = {
    # OG image of specific subpages or known CDN assets
    "e01": "https://atlantabg.org/visit/",  # Atlanta Botanical Garden
    "e02": "https://fernbankmuseum.org/visit/",  # Fernbank Museum
    "e03": "https://zooatlanta.org/visit/",  # Zoo Atlanta
    "e05": "https://beltline.org",  # Beltline + Krog Street Market
    "e08": "https://sloomooinstitute.com",  # Sloomoo Institute
    "e09": "https://legodiscoverycenter.com/atlanta/",  # LEGO
    "e11": "https://www.fulcolibrary.org",  # Morningside Library
    "e12": "https://www.atlantaga.gov",  # Neighborhood Playground
    "e15": "https://atlantabg.org/visit/",  # ABG Quiet Hours
    "e17": "https://starprovisions.com",  # Bacchanalia
    "e19": "https://foxtheatre.org/visit/",  # Fox Theatre
    "e20": "https://fernbankmuseum.org",  # Fernbank After Dark
    "e22": "https://www.instagram.com/ormsbysatl/",  # Ormsby's - skip, use fallback
    "e23": "https://www.instagram.com/lakeclairelandtrust/",  # Lake Claire
    "e25": "https://www.burythehatchet.com/locations/atlanta-ga/",  # Axe Throwing
    "e26": "https://stonesummit.com/locations/",  # Stone Summit
    "e28": "https://centennialpark.com",  # Centennial Park
    "e31": "https://gastateparks.org/SweetwaterCreek/",  # Sweetwater Creek
    "e34": "https://www.dekalbcountyga.gov/airports",  # PDK Airport
    "e35": "https://beltline.org/trails/",  # Freedom Park
    "e37": "https://dekalbfarmersmarket.com/about/",  # DeKalb Farmers Market
    "e38": "https://centennialpark.com",  # Trains at Centennial
    "e40": "https://carlos.emory.edu/visit",  # Emory Carlos Museum
    "e41": "https://stonesummit.com/locations/intown/",  # Stone Summit
    "e43": "https://www.instagram.com/tinylousatl/",  # Tiny Lou's
    "e51": "https://topgolf.com/us/atlanta-midtown/",  # Topgolf Midtown
    "e52": "https://www.paintedpin.com",  # Painted Pin
    "e54": "https://manuelstavern.com/events/",  # Manuel's Tavern
    "e56": "https://gastateparks.org/RedTopMountain/",  # Red Top Mountain
    "e57": "https://beltline.org/programs/art/",  # Beltline ArtWalk
    "e58": "https://escapology.com/en/atlanta-ga/",  # Escape Room
    "e59": "https://yellowriverwildlife.org",  # Yellow River
    "e61": "https://pullmanyards.com",  # Pullman Yards
    "e63": "https://www.homedepot.com/c/workshops",  # Home Depot
    "e64": "https://www.lowes.com/l/about/building-safety-week",  # Lowe's
    "e65": "https://tinytowne.com/atlanta/",  # Tiny Towne
    "e67": "https://boomerangatl.com/about/",  # Boomerang ATL
    "e68": "https://noahs-ark.org/visit/",  # Noah's Ark
    "e69": "https://sweetwater420fest.com/about/",  # Sweetwater 420 Fest
    "e70": "https://dogwood.org/festival/",  # Atlanta Dogwood Festival
    "e72": "https://dragoncon.org/about/parade/",  # Dragon Con Parade
    "e73": "https://candlerparkmusicfestival.org/about/",  # Candler Park Music Fest
    "e74": "https://criticalmassatlanta.wordpress.com",  # Critical Mass ATL
    "e76": "https://lakeclairelandtrust.org/drum-circle",  # Full Moon Drum Circle
    "e81": "https://tabernacleatl.com",  # Tabernacle Atlanta
    "e82": "https://beetlecatatl.com/about/",  # Beetlecat
    "e84": "https://thevelvetnote.com/visit/",  # Velvet Note
    "e90": "https://jaemorfarms.com/berries/",  # Strawberry Picking
    "e92": "https://bbsplantfarm.com/pumpkins/",  # Pumpkin Patch
    "e93": "https://atlanticstation.com",  # Outdoor Movie Night
    "e94": "https://plazaatlanta.com/events/",  # Plaza Theatre
    "e95": "https://aso.org",  # Atlanta Symphony Orchestra
    "e98": "https://visitdecaturga.com",  # Decatur Square
    "e100": "https://poncecitymarket.com/eat-drink/",  # Ponce City Market Food
    "e101": "https://atlantastpatsparade.com/about/",  # St. Patrick's Day
    "e102": "https://rejuvenationspa.com/services/",  # Sauna / Spa Day
    "e104": "https://fernbankmuseum.org/explore/",  # Fernbank Orkin
    "e106": "https://illuminarium.com/atlanta/",  # Illuminarium
    "e108": "https://www.chastainparkamphitheatre.com",  # Chastain
    "e109": "https://georgialpacas.com",  # Alpaca Farm
    "e110": "https://atlantastreetsalive.com/events/",  # Atlanta Streets Alive
}

# Hardcoded image URLs for entries where og:image won't work
HARDCODED_IMAGES = {
    "e03": "https://zooatlanta.org/wp-content/uploads/zoo-atlanta-aerial.jpg",
    "e05": "https://beltline.org/wp-content/uploads/2021/09/beltline-krog-eastside.jpg",
    "e08": "https://cdn.shopify.com/s/files/1/0578/7234/5474/files/SLOOMOO_ATL_HERO.jpg",
    "e09": "https://legodiscoverycenter.com/media/1051/ldc-atlanta.jpg",
    "e19": "https://foxtheatre.org/wp-content/uploads/fox-theatre-exterior.jpg",
    "e20": "https://fernbankmuseum.org/media/aad_img_remote_4987/fernbank-afterdark.jpg",
    "e22": "https://fastly.4sqi.net/img/general/600x600/ormsbys-atl.jpg",
    "e25": "https://www.burythehatchet.com/wp-content/uploads/bth-atlanta.jpg",
    "e26": "https://stonesummit.com/wp-content/uploads/stone-summit-climbing-hero.jpg",
    "e28": "https://centennialpark.com/wp-content/uploads/centennial-splash-pad.jpg",
    "e31": "https://gastateparks.org/sites/default/files/parks/hero/sweetwater-creek.jpg",
    "e34": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Dekalb_Peachtree_Airport.jpg/1200px-Dekalb_Peachtree_Airport.jpg",
    "e37": "https://dekalbfarmersmarket.com/wp-content/uploads/dekalb-farmers-market-interior.jpg",
    "e40": "https://carlos.emory.edu/sites/default/files/2021-02/carlos-museum-hero.jpg",
    "e41": "https://stonesummit.com/wp-content/uploads/stone-summit-intown.jpg",
    "e51": "https://topgolf.com/content/dam/topgolf/images/venues/atlanta-midtown/TopGolf_Midtown_Hero.jpg",
    "e54": "https://manuelstavern.com/wp-content/uploads/manuelstavern-hero.jpg",
    "e56": "https://gastateparks.org/sites/default/files/parks/hero/red-top-mountain.jpg",
    "e58": "https://escapology.com/wp-content/uploads/escapology-atlanta.jpg",
    "e63": "https://images.thdstatic.com/productImages/kids-workshop.jpg",
    "e65": "https://tinytowne.com/wp-content/uploads/tinytowne-atlanta.jpg",
    "e68": "https://noahs-ark.org/wp-content/uploads/noahs-ark-sanctuary.jpg",
    "e70": "https://dogwood.org/wp-content/uploads/dogwood-festival-hero.jpg",
    "e72": "https://dragoncon.org/wp-content/uploads/dragon-con-parade.jpg",
    "e73": "https://candlerparkmusicfestival.org/wp-content/uploads/candler-park-festival.jpg",
    "e76": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Drum_circle_at_lake_claire.jpg/1200px-Drum_circle_at_lake_claire.jpg",
    "e81": "https://tabernacleatl.com/wp-content/uploads/tabernacle-atlanta.jpg",
    "e82": "https://beetlecatatl.com/wp-content/uploads/beetlecat-atlanta.jpg",
    "e84": "https://thevelvetnote.com/wp-content/uploads/velvet-note-hero.jpg",
    "e90": "https://jaemorfarms.com/wp-content/uploads/strawberry-picking-jaemor.jpg",
    "e92": "https://bbsplantfarm.com/wp-content/uploads/pumpkin-patch-atlanta.jpg",
    "e93": "https://atlanticstation.com/wp-content/uploads/outdoor-movie-night.jpg",
    "e94": "https://plazaatlanta.com/wp-content/uploads/plaza-theatre-atlanta.jpg",
    "e95": "https://aso.org/wp-content/uploads/aso-hero.jpg",
    "e98": "https://visitdecaturga.com/wp-content/uploads/decatur-square-aerial.jpg",
    "e100": "https://poncecitymarket.com/wp-content/uploads/food-hall-hero.jpg",
    "e101": "https://atlantastpatsparade.com/wp-content/uploads/stpats-parade-atlanta.jpg",
    "e102": "https://rejuvenationspa.com/wp-content/uploads/rejuvenation-spa-hero.jpg",
    "e104": "https://fernbankmuseum.org/media/orkin-discovery-zone-hero.jpg",
    "e106": "https://illuminarium.com/wp-content/uploads/illuminarium-atlanta-hero.jpg",
    "e108": "https://chastainparkamphitheatre.com/wp-content/uploads/chastain-park-hero.jpg",
    "e109": "https://maplewoodfarmalpacas.com/wp-content/uploads/alpaca-farm-georgia.jpg",
    "e110": "https://atlantastreetsalive.com/wp-content/uploads/streets-alive-hero.jpg",
}

# --------------------------------------------------------------------------- #
# Helpers (same as pass 1)
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
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )
    return urllib.request.urlopen(req, context=ssl_ctx(), timeout=timeout)


class OGImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_image = None
        self.twitter_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            prop = d.get("property", "") or d.get("name", "")
            content = d.get("content", "")
            if prop == "og:image" and content and not self.og_image:
                self.og_image = content
            if prop in ("twitter:image", "twitter:image:src") and content and not self.twitter_image:
                self.twitter_image = content


def fetch_best_image(url: str) -> str | None:
    try:
        resp = make_request(url)
        raw = resp.read(600_000)
        html = raw.decode("utf-8", errors="replace")
        parser = OGImageParser()
        parser.feed(html)
        # Prefer og:image, fall back to twitter:image
        img = parser.og_image or parser.twitter_image
        return img
    except Exception as e:
        print(f"    [warn] fetch({url}): {e}")
        return None


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].split("#")[0]
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


def download_image(url: str, dest: Path) -> bool:
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
        print(f"    [err] {url}: {e}")
        return False


def find_existing(slug: str) -> Path | None:
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".jpeg"]:
        p = OUT_DIR / f"{slug}{ext}"
        if p.exists() and p.stat().st_size >= MIN_BYTES:
            return p
    return None


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    entries = json.loads(EXPORT_JSON.read_text())
    existing_results = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else {}

    # Find which IDs still need images
    need_image = [e for e in entries if e["id"] not in existing_results]
    print(f"{len(need_image)} entries still need images\n")

    new_success = 0
    still_failed = 0

    for entry in need_image:
        eid = entry["id"]
        name = entry["name"]
        slug = slugify(name)

        print(f"[{eid}] {name}")

        # Double-check it's not already on disk (maybe from a different run)
        existing = find_existing(slug)
        if existing:
            print(f"    [cached] {existing.name}")
            existing_results[eid] = f"images/evergreen/{existing.name}"
            new_success += 1
            continue

        image_url = None

        # Strategy 1: Try hardcoded image URL directly
        if eid in HARDCODED_IMAGES:
            candidate = HARDCODED_IMAGES[eid]
            print(f"    trying hardcoded: {candidate}")
            ext = ext_from_url(candidate)
            dest = OUT_DIR / f"{slug}{ext}"
            if download_image(candidate, dest):
                existing_results[eid] = f"images/evergreen/{dest.name}"
                new_success += 1
                time.sleep(DELAY)
                continue
            print(f"    hardcoded failed, trying alternate URL…")

        # Strategy 2: Try alternate URL og:image
        if eid in ALTERNATE_URLS:
            alt_url = ALTERNATE_URLS[eid]
            print(f"    og:image from alternate: {alt_url}")
            og = fetch_best_image(alt_url)
            if og and not og.lower().endswith(".svg"):
                image_url = og
            time.sleep(DELAY)

        # Strategy 3: Try original URL og:image (may have been 404 before, try base domain)
        if not image_url:
            base_url = entry.get("url", "")
            if base_url and eid not in ALTERNATE_URLS:
                # already tried in pass 1, skip
                pass
            elif base_url and eid in ALTERNATE_URLS and not image_url:
                # Alternate URL also failed, try base domain root
                parsed = urllib.parse.urlparse(base_url)
                root_url = f"{parsed.scheme}://{parsed.netloc}/"
                if root_url != alt_url:
                    print(f"    og:image from root: {root_url}")
                    og = fetch_best_image(root_url)
                    if og and not og.lower().endswith(".svg"):
                        image_url = og
                    time.sleep(DELAY)

        if image_url:
            ext = ext_from_url(image_url)
            dest = OUT_DIR / f"{slug}{ext}"
            if download_image(image_url, dest):
                existing_results[eid] = f"images/evergreen/{dest.name}"
                new_success += 1
            else:
                still_failed += 1
        else:
            print(f"    [give up] no image found")
            still_failed += 1

        time.sleep(DELAY)

    # Save updated results
    RESULTS_JSON.write_text(json.dumps(existing_results, indent=2))

    print(f"\n--- Pass 2 Results ---")
    print(f"  Newly downloaded : {new_success}")
    print(f"  Still failed     : {still_failed}")
    total = len([e for e in entries if e["id"] in existing_results])
    print(f"  Total with image : {total} / {len(entries)}")


if __name__ == "__main__":
    main()
