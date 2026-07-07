#!/usr/bin/env python3
import urllib.request
import ssl
import re
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def download_image(img_url, dest, referer):
    """Download image with proper headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': referer,
    }
    img_req = urllib.request.Request(img_url, headers=headers)
    with urllib.request.urlopen(img_req, context=ctx, timeout=10) as response:
        with open(dest, 'wb') as f:
            f.write(response.read())

def try_url(url, filename, description):
    """Try to fetch og:image from a URL"""
    dest = f'/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/images/{filename}'
    if os.path.exists(dest):
        print(f'  SKIP (exists)')
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': url,
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')

        # Also look for image URLs in page content
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)

        if m:
            img_url = m.group(1)
            print(f'    og:image: {img_url[:70]}...')
            download_image(img_url, dest, url)
            sz = os.path.getsize(dest)
            if sz < 1024:
                os.remove(dest)
                print(f'    Size too small ({sz}B), skipped')
            else:
                print(f'    SUCCESS ({sz} bytes)')
        else:
            print(f'    No og:image found')
    except Exception as e:
        print(f'    ERROR: {str(e)[:60]}')

# Try alternate URLs
print("Searching for better Piedmont Park Yoga image...\n")
print("  Try 1: piedmontpark.org\n  [Already have: 5.7K PNG - Home Depot logo]\n")

print("  Try 2: freeyogapiedmontpark.com\n")
try_url('https://freeyogapiedmontpark.com', 'free_yoga_piedmont_v2.jpg', 'Free Yoga Piedmont Park')

print("\n  Try 3: atlantaparkfoundation.org\n")
try_url('https://www.atlantaparkfoundation.org', 'free_yoga_piedmont_v3.jpg', 'Atlanta Park Foundation')

print("\n\nSearching for Critical Mass Atlanta image...\n")
print("  Try 1: Facebook (already failed with 400/403)\n")

print("  Try 2: criticalmassbikes.com\n")
try_url('https://www.criticalmassbikes.com', 'critical_mass_atl_v2.jpg', 'Critical Mass Bikes')

print("\n  Try 3: Facebook group page via different domain\n")
try_url('https://facebook.com/groups/AtlantaCM/', 'critical_mass_atl_v2b.jpg', 'Critical Mass ATL Facebook')
