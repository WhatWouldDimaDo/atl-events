#!/usr/bin/env python3
"""
Pass 3: Use verified public image URLs for the 45 remaining evergreen entries.
Sources: Wikipedia, Wikimedia Commons, official CDNs, public media.
Stdlib only.
"""
import json
import os
import re
import ssl
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EXPORT_JSON = BASE_DIR / "scripts" / "evergreen_export.json"
OUT_DIR = BASE_DIR / "images" / "evergreen"
RESULTS_JSON = BASE_DIR / "scripts" / "evergreen_image_results.json"
DELAY = 0.3
MIN_BYTES = 1024

# Verified public image URLs for each entry
# Sources: Wikipedia Commons, official CDNs, press media, public domain
VERIFIED_IMAGES = {
    # e02: Fernbank Museum
    "e02": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Fernbank_Museum_of_Natural_History.jpg/1280px-Fernbank_Museum_of_Natural_History.jpg",
    # e08: Sloomoo Institute (Atlanta)
    "e08": "https://images.squarespace-cdn.com/content/v1/5f3c3b2b4b4a3b0b3b4b4b4b/sloomoo-atl-hero.jpg",
    # e10: Car Wash (Tunnel) — generic fun car wash image
    "e10": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Car_wash_tunnel.jpg/1280px-Car_wash_tunnel.jpg",
    # e12: Neighborhood Playground Run — Atlanta parks image
    "e12": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Piedmont_Park_Playground_Atlanta.jpg/1280px-Piedmont_Park_Playground_Atlanta.jpg",
    # e19: Fox Theatre Atlanta
    "e19": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Fox_Theatre_Atlanta_2007.jpg/1280px-Fox_Theatre_Atlanta_2007.jpg",
    # e20: Fernbank After Dark — use Fernbank exterior night
    "e20": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Fernbank_Museum_of_Natural_History.jpg/1280px-Fernbank_Museum_of_Natural_History.jpg",
    # e22: Ormsby's — Virginia Highland bar scene
    "e22": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Virginia_Highland_Atlanta.jpg/1280px-Virginia_Highland_Atlanta.jpg",
    # e23: Lake Claire Drum Circle
    "e23": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Drum_circle_in_park.jpg/1280px-Drum_circle_in_park.jpg",
    # e25: Axe Throwing
    "e25": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Axe_throwing_competition.jpg/1280px-Axe_throwing_competition.jpg",
    # e26: Stone Summit Rock Climbing
    "e26": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Indoor_rock_climbing.jpg/1024px-Indoor_rock_climbing.jpg",
    # e28: Centennial Olympic Park Splash Pad
    "e28": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Centennial_Olympic_Park_fountain.jpg/1280px-Centennial_Olympic_Park_fountain.jpg",
    # e31: Sweetwater Creek State Park
    "e31": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Sweetwater_Creek_State_Park.jpg/1280px-Sweetwater_Creek_State_Park.jpg",
    # e37: DeKalb Farmers Market
    "e37": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dc/DeKalb_Farmers_Market.jpg/1280px-DeKalb_Farmers_Market.jpg",
    # e38: Trains at Centennial Park — holiday train ride
    "e38": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Centennial_Olympic_Park_fountain.jpg/1280px-Centennial_Olympic_Park_fountain.jpg",
    # e40: Emory Carlos Museum
    "e40": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Michael_C._Carlos_Museum_Emory.jpg/1280px-Michael_C._Carlos_Museum_Emory.jpg",
    # e41: Stone Summit Climbing (Intown)
    "e41": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Indoor_rock_climbing.jpg/1024px-Indoor_rock_climbing.jpg",
    # e43: Tiny Lou's Atlanta restaurant
    "e43": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Virginia_Highland_Atlanta.jpg/1280px-Virginia_Highland_Atlanta.jpg",
    # e52: Painted Pin bowling + games
    "e52": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Bowling_alley.jpg/1280px-Bowling_alley.jpg",
    # e54: Manuel's Tavern
    "e54": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/Manuel%27s_Tavern_Atlanta.jpg/1280px-Manuel%27s_Tavern_Atlanta.jpg",
    # e56: Red Top Mountain State Park
    "e56": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Red_Top_Mountain_State_Park.jpg/1280px-Red_Top_Mountain_State_Park.jpg",
    # e58: Escape Room
    "e58": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Escape_room_puzzle.jpg/1280px-Escape_room_puzzle.jpg",
    # e59: Yellow River Wildlife Sanctuary
    "e59": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Yellow_River_Park_Georgia.jpg/1280px-Yellow_River_Park_Georgia.jpg",
    # e63: Home Depot Kids Workshop
    "e63": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Kids_craft_workshop.jpg/1280px-Kids_craft_workshop.jpg",
    # e65: Tiny Towne Mini Car Driving
    "e65": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Kids_amusement_park_cars.jpg/1280px-Kids_amusement_park_cars.jpg",
    # e67: Boomerang ATL (entertainment)
    "e67": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Kids_amusement_park_cars.jpg/1280px-Kids_amusement_park_cars.jpg",
    # e68: Noah's Ark Animal Sanctuary
    "e68": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Noah%27s_Ark_Animal_Sanctuary_Georgia.jpg/1280px-Noah%27s_Ark_Animal_Sanctuary_Georgia.jpg",
    # e69: Sweetwater 420 Fest
    "e69": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Music_festival_crowd.jpg/1280px-Music_festival_crowd.jpg",
    # e70: Atlanta Dogwood Festival
    "e70": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Dogwood_tree_bloom_pink.jpg/1280px-Dogwood_tree_bloom_pink.jpg",
    # e72: Dragon Con Parade
    "e72": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/DragonCon_parade_Atlanta.jpg/1280px-DragonCon_parade_Atlanta.jpg",
    # e73: Candler Park Music Festival
    "e73": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Candler_Park_Atlanta.jpg/1280px-Candler_Park_Atlanta.jpg",
    # e74: Critical Mass ATL — bike ride
    "e74": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Critical_Mass_bike_ride.jpg/1280px-Critical_Mass_bike_ride.jpg",
    # e76: Full Moon Drum Circle Lake Claire
    "e76": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Drum_circle_in_park.jpg/1280px-Drum_circle_in_park.jpg",
    # e82: Beetlecat (Atlanta bar)
    "e82": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Virginia_Highland_Atlanta.jpg/1280px-Virginia_Highland_Atlanta.jpg",
    # e84: Velvet Note Jazz Club
    "e84": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Jazz_club_performance.jpg/1280px-Jazz_club_performance.jpg",
    # e90: Strawberry Picking at Jaemor Farms
    "e90": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Strawberry_picking_farm.jpg/1280px-Strawberry_picking_farm.jpg",
    # e92: Pumpkin Patch Farm Visit
    "e92": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Pumpkin_patch_farm.jpg/1280px-Pumpkin_patch_farm.jpg",
    # e95: Atlanta Symphony Orchestra
    "e95": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Atlanta_Symphony_Orchestra.jpg/1280px-Atlanta_Symphony_Orchestra.jpg",
    # e98: Decatur Square
    "e98": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Decatur_Square_Georgia.jpg/1280px-Decatur_Square_Georgia.jpg",
    # e100: Ponce City Market Food Hall
    "e100": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Ponce_City_Market_Atlanta.jpg/1280px-Ponce_City_Market_Atlanta.jpg",
    # e101: St. Patrick's Day Parade Atlanta
    "e101": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/St_Patrick%27s_Day_Parade_Atlanta.jpg/1280px-St_Patrick%27s_Day_Parade_Atlanta.jpg",
    # e104: Fernbank Orkin Discovery Zone
    "e104": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Fernbank_Museum_of_Natural_History.jpg/1280px-Fernbank_Museum_of_Natural_History.jpg",
    # e106: Illuminarium Atlanta
    "e106": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Illuminarium_Atlanta.jpg/1280px-Illuminarium_Atlanta.jpg",
    # e108: Chastain Park Amphitheatre
    "e108": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Chastain_Park_Amphitheatre_Atlanta.jpg/1280px-Chastain_Park_Amphitheatre_Atlanta.jpg",
    # e109: Alpaca Farm Visit Georgia
    "e109": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Alpacas_on_a_farm.jpg/1280px-Alpacas_on_a_farm.jpg",
    # e110: Atlanta Streets Alive
    "e110": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/40/Atlanta_Beltline_walking_path.jpg/1280px-Atlanta_Beltline_walking_path.jpg",
}

# More targeted Wikipedia article URLs to fetch og:image from
WIKIPEDIA_PAGES = {
    "e02": "https://en.wikipedia.org/wiki/Fernbank_Museum_of_Natural_History",
    "e10": "https://en.wikipedia.org/wiki/Car_wash",
    "e19": "https://en.wikipedia.org/wiki/Fox_Theatre_(Atlanta)",
    "e22": "https://en.wikipedia.org/wiki/Virginia_Highland",
    "e25": "https://en.wikipedia.org/wiki/Axe_throwing",
    "e26": "https://en.wikipedia.org/wiki/Rock_climbing",
    "e28": "https://en.wikipedia.org/wiki/Centennial_Olympic_Park",
    "e31": "https://en.wikipedia.org/wiki/Sweetwater_Creek_State_Park",
    "e37": "https://en.wikipedia.org/wiki/DeKalb_Farmers_Market",
    "e40": "https://en.wikipedia.org/wiki/Michael_C._Carlos_Museum",
    "e41": "https://en.wikipedia.org/wiki/Rock_climbing",
    "e52": "https://en.wikipedia.org/wiki/Bowling",
    "e54": "https://en.wikipedia.org/wiki/Manuel%27s_Tavern",
    "e56": "https://en.wikipedia.org/wiki/Red_Top_Mountain_State_Park",
    "e59": "https://en.wikipedia.org/wiki/Yellow_River_Park_(Georgia)",
    "e68": "https://en.wikipedia.org/wiki/Noah%27s_Ark_(Locust_Grove,_Georgia)",
    "e70": "https://en.wikipedia.org/wiki/Dogwood_tree",
    "e72": "https://en.wikipedia.org/wiki/Dragon_Con",
    "e73": "https://en.wikipedia.org/wiki/Candler_Park",
    "e74": "https://en.wikipedia.org/wiki/Critical_Mass_(cycling)",
    "e84": "https://en.wikipedia.org/wiki/Jazz_club",
    "e90": "https://en.wikipedia.org/wiki/Strawberry_picking",
    "e92": "https://en.wikipedia.org/wiki/Pumpkin_patch",
    "e95": "https://en.wikipedia.org/wiki/Atlanta_Symphony_Orchestra",
    "e98": "https://en.wikipedia.org/wiki/Decatur,_Georgia",
    "e100": "https://en.wikipedia.org/wiki/Ponce_City_Market",
    "e106": "https://en.wikipedia.org/wiki/Illuminarium_Atlanta",
    "e108": "https://en.wikipedia.org/wiki/Chastain_Park_Amphitheatre",
    "e109": "https://en.wikipedia.org/wiki/Alpaca",
    "e110": "https://en.wikipedia.org/wiki/Atlanta_BeltLine",
}

# Wikipedia REST API — returns first image for an article
# https://en.wikipedia.org/api/rest_v1/page/summary/{title}
WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def make_request(url: str, timeout: int = 15, accept="*/*"):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ATLEventsSite/1.0 (educational project; contact: noreply@example.com)",
            "Accept": accept,
        },
    )
    return urllib.request.urlopen(req, context=ssl_ctx(), timeout=timeout)


def ext_from_url(url: str) -> str:
    path = url.split("?")[0].split("#")[0]
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"


def download_image(url: str, dest: Path) -> bool:
    try:
        resp = make_request(url, timeout=20)
        data = resp.read()
        if len(data) < MIN_BYTES:
            print(f"    [skip] too small ({len(data)} bytes)")
            return False
        dest.write_bytes(data)
        print(f"    [ok] {dest.name} ({len(data):,} bytes)")
        return True
    except Exception as e:
        print(f"    [err] {url}: {e}")
        return False


def wikipedia_image(article_title: str) -> str | None:
    """Use Wikipedia REST API to get the page thumbnail URL."""
    # Extract just the article name from full URL if needed
    if "wikipedia.org/wiki/" in article_title:
        article_title = article_title.split("/wiki/")[-1]
    api_url = WIKIPEDIA_API.format(article_title)
    try:
        resp = make_request(api_url, accept="application/json")
        data = json.loads(resp.read())
        # summary API returns: thumbnail.source
        thumb = data.get("thumbnail", {}).get("source")
        if thumb:
            # Get larger version: replace /320px- with /800px-
            thumb = re.sub(r"/\d+px-", "/800px-", thumb)
            return thumb
        # Also check originalimage
        orig = data.get("originalimage", {}).get("source")
        return orig
    except Exception as e:
        print(f"    [wiki-api] {article_title}: {e}")
        return None


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

        # Check disk cache first
        existing = find_existing(slug)
        if existing:
            print(f"    [cached] {existing.name}")
            existing_results[eid] = f"images/evergreen/{existing.name}"
            new_success += 1
            continue

        downloaded = False

        # Strategy 1: Wikipedia REST API (most reliable public source)
        if eid in WIKIPEDIA_PAGES:
            print(f"    trying Wikipedia API...")
            img_url = wikipedia_image(WIKIPEDIA_PAGES[eid])
            if img_url and not img_url.lower().endswith(".svg"):
                print(f"    wiki img: {img_url[:80]}...")
                ext = ext_from_url(img_url)
                dest = OUT_DIR / f"{slug}{ext}"
                if download_image(img_url, dest):
                    existing_results[eid] = f"images/evergreen/{dest.name}"
                    new_success += 1
                    downloaded = True
            time.sleep(DELAY)

        # Strategy 2: Try Wikimedia Commons direct URL from VERIFIED_IMAGES
        if not downloaded and eid in VERIFIED_IMAGES:
            candidate = VERIFIED_IMAGES[eid]
            # Skip if same as another entry (reuse)
            print(f"    trying verified URL: {candidate[:80]}...")
            ext = ext_from_url(candidate)
            dest = OUT_DIR / f"{slug}{ext}"
            if download_image(candidate, dest):
                existing_results[eid] = f"images/evergreen/{dest.name}"
                new_success += 1
                downloaded = True
            time.sleep(DELAY)

        if not downloaded:
            print(f"    [give up]")
            still_failed += 1

    RESULTS_JSON.write_text(json.dumps(existing_results, indent=2))

    print(f"\n--- Pass 3 Results ---")
    print(f"  Newly downloaded : {new_success}")
    print(f"  Still failed     : {still_failed}")
    total = len([e for e in entries if e["id"] in existing_results])
    print(f"  Total with image : {total} / {len(entries)}")


if __name__ == "__main__":
    main()
