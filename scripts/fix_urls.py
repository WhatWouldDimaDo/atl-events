#!/usr/bin/env python3
"""
fix_urls.py — Patch missing URLs into evergreen entries in data.js.

Strategy: find each entry by id string, then replace the first `url: null`
or `url: ''` within a small window after that id.
"""

import re

DATA_JS = '/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/data.js'

# Map of entry id → correct URL (None = leave as null)
URLS = {
    'e05': 'https://beltline.org/trails/eastside-trail/',
    'e28': 'https://centennialpark.com/plan-your-visit/',
    'e31': 'https://gastateparks.org/SweetwaterCreek',
    'e34': 'https://www.dekalbcountyga.gov/airports/dekalb-peachtree-airport',
    'e35': 'https://beltline.org/trails/freedom-park-trail/',
    'e10': None,                                                         # generic car wash, leave null
    'e11': 'https://www.fulcolibrary.org/branches/morningside/',
    'e12': 'https://www.atlantaga.gov/government/departments/parks-recreation/park-listing',
    'e36': 'https://www.chick-fil-a.com',
    'e38': 'https://centennialpark.com/plan-your-visit/',
    'e15': 'https://atlantabg.org',
    'e42': 'https://piedmontpark.org',
    'e18': 'https://www.littlebearatl.com',
    'e21': 'https://poncecitymarket.com/skyline-park/',
    'e22': 'https://ormsbysatl.com',
    'e23': 'https://www.lakeclairelandtrust.org',
    'e24': 'https://krogstreetmarket.com',
    'e25': 'https://www.burythehatchet.com/locations/atlanta/',
    'e53': 'https://vahi.org',
    'e54': 'https://manuelstavern.com',
    'e56': 'https://gastateparks.org/RedTopMountain',
    'e57': 'https://beltline.org/events/artwalk/',
}


def patch_url(content: str, entry_id: str, new_url) -> str:
    """
    Locate `id: 'eXX'` then replace url: null or url: '' within the next 600 chars.
    """
    id_pattern = f"id: '{entry_id}'"
    pos = content.find(id_pattern)
    if pos == -1:
        print(f"  ERROR: id '{entry_id}' not found in data.js")
        return content

    window_end = pos + 1000
    window = content[pos:window_end]

    if new_url is None:
        new_val = 'url: null'
    else:
        new_val = f"url: '{new_url}'"

    url_null_match = re.search(r"url: null", window)
    url_empty_match = re.search(r"url: ''", window)

    if url_null_match:
        match_start = pos + url_null_match.start()
        match_end   = pos + url_null_match.end()
        content = content[:match_start] + new_val + content[match_end:]
        status = 'null' if new_url is None else f"null → {new_url}"
        print(f"  {entry_id}: {status}")
    elif url_empty_match:
        match_start = pos + url_empty_match.start()
        match_end   = pos + url_empty_match.end()
        content = content[:match_start] + new_val + content[match_end:]
        print(f"  {entry_id}: '' → {new_url}")
    else:
        existing = re.search(r"url: '(https?://[^']+)'", window)
        if existing:
            print(f"  {entry_id}: already set to '{existing.group(1)}' — skipping")
        else:
            print(f"  {entry_id}: WARNING — no url field found in window")

    return content


def main():
    with open(DATA_JS, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Loaded data.js ({len(content):,} chars)")
    print("Patching URLs...\n")

    for entry_id, url in URLS.items():
        content = patch_url(content, entry_id, url)

    with open(DATA_JS, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\nWrote updated data.js ({len(content):,} chars)")


if __name__ == '__main__':
    main()
