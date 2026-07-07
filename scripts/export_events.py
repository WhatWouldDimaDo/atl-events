#!/usr/bin/env python3
"""Export EVENTS array from data.js to events.json.

Parses the JS object literal syntax into Python dicts using a
lightweight approach: extract the EVENTS block, normalize to valid
JSON, then json.loads(). Stdlib only — no Node, no pip deps.
"""
import json
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_JS = PROJECT_DIR / "data.js"
EVENTS_JSON = PROJECT_DIR / "scripts" / "events.json"


def extract_events_block(js_text: str) -> str:
    """Pull the EVENTS = [...]; block from data.js."""
    m = re.search(r"const EVENTS\s*=\s*\[", js_text)
    if not m:
        raise ValueError("Could not find 'const EVENTS = [' in data.js")
    start = m.start() + len("const EVENTS = ")
    depth = 0
    for i in range(start, len(js_text)):
        if js_text[i] == "[":
            depth += 1
        elif js_text[i] == "]":
            depth -= 1
            if depth == 0:
                return js_text[start : i + 1]
    raise ValueError("Unmatched brackets in EVENTS array")


def js_to_json(block: str) -> str:
    """Convert JS object literal syntax to valid JSON.

    Strategy: walk char-by-char to handle strings correctly,
    then fix unquoted keys and trailing commas on the non-string parts.
    """
    # Step 0: Remove JS comments (// and /* */) first
    # Handle // comments (single-line)
    out_lines = []
    for line in block.split('\n'):
        # Find // outside of strings
        in_string = False
        quote_char = None
        for i, c in enumerate(line):
            if c in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    quote_char = c
                elif c == quote_char:
                    in_string = False
            elif c == '/' and not in_string and i + 1 < len(line) and line[i + 1] == '/':
                # Found // outside string, truncate line here
                line = line[:i]
                break
        out_lines.append(line)
    block = '\n'.join(out_lines)

    # Handle /* */ block comments
    while '/*' in block:
        start = block.find('/*')
        end = block.find('*/', start)
        if end == -1:
            raise ValueError("Unclosed /* comment in EVENTS block")
        block = block[:start] + ' ' + block[end + 2:]

    # Step 1: Convert single-quoted JS strings to double-quoted JSON strings.
    # Walk char-by-char so we don't break on embedded quotes.
    out = []
    i = 0
    while i < len(block):
        c = block[i]
        if c == "'":
            # Start of a single-quoted string — collect until unescaped '
            out.append('"')
            i += 1
            while i < len(block) and block[i] != "'":
                if block[i] == "\\" and i + 1 < len(block):
                    if block[i + 1] == "'":
                        # \' → just '
                        out.append("'")
                        i += 2
                        continue
                    elif block[i + 1] == "\\":
                        out.append("\\\\")
                        i += 2
                        continue
                if block[i] == '"':
                    out.append('\\"')  # escape embedded double quotes
                    i += 1
                    continue
                out.append(block[i])
                i += 1
            out.append('"')
            i += 1  # skip closing '
        else:
            out.append(c)
            i += 1
    s = "".join(out)

    # Step 2: Quote unquoted object keys (word:)
    s = re.sub(r"(?m)^\s*(\w+)\s*:", r'"\1":', s)
    s = re.sub(r",\s*(\w+)\s*:", r', "\1":', s)
    s = re.sub(r"\{\s*(\w+)\s*:", r'{ "\1":', s)

    # Step 3: Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    return s


def main():
    js_text = DATA_JS.read_text(encoding="utf-8")
    block = extract_events_block(js_text)
    json_str = js_to_json(block)

    try:
        events = json.loads(json_str)
    except json.JSONDecodeError as e:
        # Find the error location and print context
        lines = json_str.splitlines()
        err_line = e.lineno - 1 if e.lineno else 0
        start = max(0, err_line - 3)
        end = min(len(lines), err_line + 4)
        print(f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")
        for i in range(start, end):
            marker = " >>>" if i == err_line else "    "
            print(f"{marker} {i+1}: {lines[i][:120]}")
        raise

    EVENTS_JSON.write_text(
        json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Exported {len(events)} events to {EVENTS_JSON.relative_to(PROJECT_DIR)}")

    # Quick stats
    with_img = sum(1 for e in events if e.get("imageUrl"))
    with_tix = sum(1 for e in events if e.get("ticketUrl"))
    with_off = sum(1 for e in events if e.get("officialUrl"))
    print(f"  Images: {with_img}/{len(events)}")
    print(f"  Tickets: {with_tix}/{len(events)}")
    print(f"  Official: {with_off}/{len(events)}")


if __name__ == "__main__":
    main()
