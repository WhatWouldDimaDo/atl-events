#!/usr/bin/env python3
"""Patch remaining EVERGREEN entries missing imageUrl."""
import json, re, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(BASE, 'data.js')
RESULTS = os.path.join(BASE, 'scripts', 'evergreen_image_results.json')

with open(RESULTS) as f:
    results = json.load(f)

with open(DATA_JS) as f:
    content = f.read()

# Find entries missing imageUrl
missing = ['e10', 'e58', 'e59', 'e63', 'e65', 'e67', 'e68', 'e69', 'e70',
           'e72', 'e73', 'e74', 'e76', 'e82', 'e84', 'e90', 'e92', 'e95',
           'e98', 'e100', 'e101', 'e104', 'e106']

patched = 0
for eid in missing:
    if eid not in results:
        print(f"  {eid} — no image result")
        continue
    img = results[eid]
    # Strategy: find "notes: '" in the entry block and insert imageUrl before it
    # First, find the entry block
    id_pattern = f"id: '{eid}',"
    idx = content.find(id_pattern)
    if idx == -1:
        print(f"  {eid} — id not found")
        continue
    # Find the notes: field in this block (within next 800 chars)
    block = content[idx:idx+800]
    notes_match = re.search(r"notes: '", block)
    if notes_match:
        insert_pos = idx + notes_match.start()
        content = content[:insert_pos] + f"imageUrl: '{img}', " + content[insert_pos:]
        patched += 1
        print(f"  {eid} — patched (before notes)")
    else:
        # Try notes: null
        notes_null = re.search(r"notes: null", block)
        if notes_null:
            insert_pos = idx + notes_null.start()
            content = content[:insert_pos] + f"imageUrl: '{img}', " + content[insert_pos:]
            patched += 1
            print(f"  {eid} — patched (before notes null)")
        else:
            print(f"  {eid} — notes field not found")

with open(DATA_JS, 'w') as f:
    f.write(content)

print(f"\nPatched: {patched}/{len(missing)}")
