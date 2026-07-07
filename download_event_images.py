#!/usr/bin/env python3
import urllib.request
import ssl
import re
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_og_image(url, filename):
    dest = f'/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/images/{filename}'
    if os.path.exists(dest):
        print(f'SKIP {filename} (exists)')
        return
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
        if m:
            img_url = m.group(1)
            print(f'  Found og:image: {img_url[:80]}...')
            urllib.request.urlretrieve(img_url, dest)
            sz = os.path.getsize(dest)
            if sz < 1024:
                os.remove(dest)
                print(f'SKIP {filename} (too small: {sz})')
            else:
                print(f'OK {filename} ({sz} bytes)')
        else:
            print(f'NO OG:IMAGE for {url}')
    except Exception as e:
        print(f'ERROR {filename}: {e}')

# Events to process
events = [
    ('https://www.facebook.com/groups/AtlantaCM', 'critical_mass_atl.jpg'),
    ('https://juliestuart5rhythms.com', 'five_rhythms_atl.jpg'),
    ('https://www.castleberryhill.org', 'castleberry_art_stroll.jpg'),
    ('https://www.castleberryhillartstroll.com', 'castleberry_art_stroll_alt.jpg'),
    ('https://piedmontpark.org', 'free_yoga_piedmont.jpg'),
]

print("Starting og:image download...\n")
for url, filename in events:
    print(f'Fetching {filename} from {url}')
    fetch_og_image(url, filename)
    print()
