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

def fetch_og_image_with_referer(url, filename):
    """Try fetching with various referer headers to bypass 403s"""
    dest = f'/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/images/{filename}'
    if os.path.exists(dest):
        print(f'SKIP {filename} (exists)')
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': url,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        html = urllib.request.urlopen(req, context=ctx, timeout=10).read().decode('utf-8', errors='ignore')
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html) or \
            re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html)
        if m:
            img_url = m.group(1)
            print(f'  Found og:image: {img_url[:80]}...')

            # Try to download image with referer
            download_image(img_url, dest, url)
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

# Try Facebook and Piedmont Park with referer
print("Trying fallback approach for Facebook...\n")
fetch_og_image_with_referer('https://www.facebook.com/groups/AtlantaCM', 'critical_mass_atl.jpg')

print("\nTrying fallback approach for Piedmont Park...\n")
fetch_og_image_with_referer('https://piedmontpark.org', 'free_yoga_piedmont.jpg')
