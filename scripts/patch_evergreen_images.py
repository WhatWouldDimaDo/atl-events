#!/usr/bin/env python3
"""Patch EVERGREEN entries in data.js with imageUrl from evergreen_image_results.json."""
import json, re, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(BASE, 'data.js')
RESULTS = os.path.join(BASE, 'scripts', 'evergreen_image_results.json')

with open(RESULTS) as f:
    results = json.load(f)

with open(DATA_JS) as f:
    content = f.read()

patched = 0
failed = 0

for entry_id, image_path in results.items():
    # Find the block: id: 'eXX', ... notes: '...'
    # Insert imageUrl after the url: line
    pattern = rf"(id: '{re.escape(entry_id)}',.*?url: '[^']*')"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        old = match.group(1)
        # Check if imageUrl already exists in the block
        block_end = content.find('},', match.start())
        block = content[match.start():block_end]
        if 'imageUrl:' in block:
            print(f"  SKIP {entry_id} — already has imageUrl")
            continue
        new = old + f", imageUrl: '{image_path}'"
        content = content.replace(old, new, 1)
        patched += 1
    else:
        # Try with url: null
        pattern2 = rf"(id: '{re.escape(entry_id)}',.*?url: null)"
        match2 = re.search(pattern2, content, re.DOTALL)
        if match2:
            old = match2.group(1)
            block_end = content.find('},', match2.start())
            block = content[match2.start():block_end]
            if 'imageUrl:' in block:
                print(f"  SKIP {entry_id} — already has imageUrl")
                continue
            new = old + f", imageUrl: '{image_path}'"
            content = content.replace(old, new, 1)
            patched += 1
        else:
            print(f"  FAIL {entry_id} — pattern not found")
            failed += 1

with open(DATA_JS, 'w') as f:
    f.write(content)

print(f"\nPatched: {patched}, Failed: {failed}, Total: {len(results)}")
