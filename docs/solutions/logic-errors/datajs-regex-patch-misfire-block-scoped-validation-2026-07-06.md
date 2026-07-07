---
title: "Cross-event regex patching of data.js misfires on out-of-order IDs — block-scope + validate"
module: atl-events-site
date: "2026-07-06"
problem_type: logic_error
component: tooling
symptoms:
  - "st_lucia.jpg (event id 84) applied to Magic for Adults (id 83)"
  - "field changes on events that were not in the patch list"
root_cause: "EVENTS blocks in data.js are not in strict id order; regex `id: N,.*?field:` with DOTALL crosses event boundaries and patches the first `field:` after the id match — which can belong to a different event"
resolution_type: code_fix
tags:
  - regex
  - "data.js"
  - enrichment
  - validation
---

# Cross-event regex patching misfires — block-scope + mandatory validation

## Problem
`enrich_events.py --apply` patched event fields with `re.search(rf"(id:\s*{eid},.*?){field}:...", js, re.DOTALL)`. Because events are not stored in id order, the lazy `.*?` crossed into the next event's block and patched the wrong event.

## Symptoms
St. Lucia's image landed on Magic for Adults (Jul 2026). Silent — nothing failed; the wrong event just changed.

## What Didn't Work
- "Be careful with --apply" as a doc warning (ENRICHMENT-METHODOLOGY.md) — humans forget; the call site still used the raw regex two months later

## Solution
Two layers, both in `scripts/enrich_events.py`:

1. **Block-scoped patcher** — find `(?<!\d)id: N,`, bound the block at the next `\n  [{\]]`, substitute only inside:
```python
def patch_event_field(js, eid, field, value):
    m = re.search(rf'(?<!\d)id:\s*{eid},', js)
    if not m: return js, False
    start = m.start()
    nxt = re.search(r'\n  [{\]]', js[start+10:])
    end = start + 10 + nxt.start() if nxt else len(js)
    block = js[start:end]
    new_block, n = re.subn(rf"({re.escape(field)}:\s*)(?:null|'[^']*'|\"[^\"]*\")",
                           lambda mm: f"{mm.group(1)}'{value}'", block, count=1)
    return js[:start] + new_block + js[end:], n > 0
```

2. **Mandatory post-apply validation** — export events.json before and after, diff imageUrl/ticketUrl/officialUrl/youtubeId/instagramUrl across ALL events; any change not in the intended (id, field, value) set → restore data.js from backup and `sys.exit(1)`.

## Why This Works
The block scope makes the misfire class impossible; the validator makes any *new* silent-corruption class loud. Correct-by-construction plus verify-by-diff.

## Prevention
- Never patch structured-ish text files with cross-boundary DOTALL regex; bound the edit region first
- Any silent-write pipeline deserves a before/after diff of the fields it is allowed to touch
- Unit-test the boundary cases: out-of-order ids, id-prefix collisions (id 8 vs 86), missing ids
