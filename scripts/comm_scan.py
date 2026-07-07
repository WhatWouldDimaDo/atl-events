#!/usr/bin/env python3
"""Communication Intelligence Scanner — Phase A

Reads iMessage (chat.db) and Call History (CallHistory.storedata) to produce
per-person last_contact dates, matched against the CRM database.

New in Phase A:
  --write-crm     Write last_contact_date, last_platform, contact_count_90d
                  back to crm_database.json AND advance SAE cadence last: dates
  iMessage_handle field in CRM is used as an alternate match handle (email or
                  phone) — useful for contacts added in-person with no phone yet.
  New contacts    Unmatched handles with 3+ msgs or 1+ calls in 90d are collected
                  and written to comm_scan_results.json under 'new_contacts'.

Usage:
    python3 scripts/comm_scan.py                 # Scan only, write JSON
    python3 scripts/comm_scan.py --dry-run       # Print results + preview CRM/SAE changes, no writes
    python3 scripts/comm_scan.py --write-crm     # Scan + write back to CRM JSON + update SAE cadence
"""
import json
import os
import plistlib
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- Paths ---
PROJECT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_DIR / "scripts"
OUTPUT_FILE = SCRIPTS_DIR / "comm_scan_results.json"
LOG_DIR = SCRIPTS_DIR

CRM_DB  = Path.home() / "Documents/Brain/02_Areas/Friends/crm_database.json"
# batch2 was merged into crm_database.json on 2026-07-06 (FR-07 fix — batch2 rows
# were silently skipped by writeback). Path kept for backward compat; file is
# archived in 2026-04-18_Personal-CRM/backups/ and load_crm() tolerates absence.
CRM_DB2 = Path.home() / "Documents/Brain/02_Areas/Friends/crm_database_batch2.json"

# Google Contacts phone index — 1,014 entries, the phone master
GC_PHONE_INDEX = Path.home() / "Documents/Coding/Projects/2026-04-18_Personal-CRM/derived/gc_phone_index.json"

# Social Activation Engine — cadence last: dates live here
SAE_FILE = Path.home() / "Documents/Coding/Projects/2026-04-18_Personal-CRM/derived/social_activation_engine.md"

IMESSAGE_DB = Path.home() / "Library/Messages/chat.db"
CALL_DB     = Path.home() / "Library/Application Support/CallHistoryDB/CallHistory.storedata"

# AddressBook sources — checked in order, highest phone count wins
ADDRESSBOOK_SOURCES = [
    Path.home() / "Library/Application Support/AddressBook/Sources/5E8E9AC9-85D0-43CA-A150-69EC83398F4B/AddressBook-v22.abcddb",
    Path.home() / "Library/Application Support/AddressBook/Sources/2569E867-E137-4340-B8C1-F691AEE8E5A6/AddressBook-v22.abcddb",
    Path.home() / "Library/Application Support/AddressBook/AddressBook-v22.abcddb",
]

# Epoch references
APPLE_EPOCH          = datetime(2001, 1, 1)
IMESSAGE_NS_DIVISOR  = 1_000_000_000       # iMessage date: nanoseconds since Apple epoch
NINETY_DAYS_AGO      = datetime.now() - timedelta(days=90)

# Platform enum — canonical values
PLATFORM_IMESSAGE = "imessage"
PLATFORM_CALL     = "call"
PLATFORM_IN_PERSON = "in_person"

# Minimum activity thresholds for new-contact detection
NEW_CONTACT_MIN_MSGS  = 3
NEW_CONTACT_MIN_CALLS = 1


# --- Phone / handle normalization ---

def normalize_phone(raw: str) -> str | None:
    """Normalize to E.164 (+1XXXXXXXXXX for US). Returns None for non-phone input."""
    if not raw:
        return None
    if "@" in raw:
        return raw.lower().strip()          # email handle — return as-is
    cleaned = re.sub(r"[^\d+]", "", raw)
    if not cleaned:
        return None
    digits = cleaned.lstrip("+")
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if len(digits) > 11:
        return f"+{digits}"
    return None


def normalize_platform(raw: str) -> str:
    """Normalize last_platform to canonical enum."""
    if not raw:
        return PLATFORM_IMESSAGE
    r = raw.lower().strip()
    if r in ("imessage", "imessage", "sms", "text"):
        return PLATFORM_IMESSAGE
    if r in ("call", "phone", "facetime"):
        return PLATFORM_CALL
    if r in ("in_person", "in-person", "inperson", "person"):
        return PLATFORM_IN_PERSON
    return r  # pass through unknown values (linkedin, email, facebook, etc.)


def extract_message_text(text_val, attributed_body_val) -> str | None:
    """Extract text from a message row, handling attributedBody for macOS Ventura+.

    On Ventura+, many messages store content in attributedBody (NSArchiver
    streamtyped format) rather than the plain text column.

    Two formats handled:
    1. NSKeyedArchiver (bplist00) — newer format, parseable with plistlib
    2. NSArchiver streamtyped — older format, requires byte-level extraction
       via NSString marker at offset +14
    """
    if text_val:
        return text_val
    if not attributed_body_val:
        return None
    data = bytes(attributed_body_val)
    # Try NSKeyedArchiver (bplist00) first
    if data[:6] == b'bplist':
        try:
            plist = plistlib.loads(data)
            for obj in plist.get("$objects", []):
                if (
                    isinstance(obj, str)
                    and obj
                    and obj != "$null"
                    and not obj.startswith("NS")
                    and len(obj) > 3
                ):
                    return obj
        except Exception:
            pass
    # NSArchiver streamtyped — length-aware NSString marker extraction
    # iMessage uses this format for most attributedBody blobs.
    # Layout: NSString(8) + \x01\x94\x84\x01+(5) + length_byte(s) + text
    try:
        idx = data.rfind(b'NSString')
        if idx > -1:
            offset = idx + 13  # position of length indicator
            lb = data[offset]
            if lb < 0x80:
                # Single-byte length
                text = data[offset + 1:offset + 1 + lb].decode('utf-8', errors='ignore')
            elif lb == 0x81:
                # Two-byte: length in next byte; text may have an extra \x00 padding
                length = data[offset + 1]
                cand_a = data[offset + 2:offset + 2 + length].decode('utf-8', errors='ignore')
                cand_b = data[offset + 3:offset + 3 + length].decode('utf-8', errors='ignore')
                pa = ''.join(c for c in cand_a if c.isprintable() or c in ('\n', '\t'))
                pb = ''.join(c for c in cand_b if c.isprintable() or c in ('\n', '\t'))
                text = pa if len(pa) >= len(pb) else pb
            else:
                return None
            cleaned = ''.join(c for c in text if c.isprintable() or c in ('\n', '\t')).strip()
            if len(cleaned) > 3:
                return cleaned
    except Exception:
        pass
    return None


# --- Apple Contacts (AddressBook) lookup ---

def load_address_book() -> dict[str, str]:
    """Load Apple Contacts → {normalized_handle: "Full Name"}.

    Tries each known AddressBook source, uses the one with the most phone records.
    Returns a dict keyed by E.164 phone numbers and lowercase email addresses.
    """
    best_db = None
    best_count = 0
    for path in ADDRESSBOOK_SOURCES:
        if not path.exists():
            continue
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
            count = conn.execute("SELECT COUNT(*) FROM ZABCDPHONENUMBER").fetchone()[0]
            conn.close()
            if count > best_count:
                best_count = count
                best_db = path
        except Exception:
            continue

    if not best_db or best_count == 0:
        return {}

    ab: dict[str, str] = {}
    try:
        conn = sqlite3.connect(f"file:{best_db}?mode=ro&immutable=1", uri=True)
        conn.execute("PRAGMA query_only=ON")

        name_expr = "COALESCE(NULLIF(TRIM(COALESCE(r.ZFIRSTNAME,'') || ' ' || COALESCE(r.ZLASTNAME,'')), ''), r.ZNICKNAME, r.ZORGANIZATION)"

        # Phones
        for full_number, name in conn.execute(f"""
            SELECT p.ZFULLNUMBER, {name_expr}
            FROM ZABCDPHONENUMBER p
            JOIN ZABCDRECORD r ON p.ZOWNER = r.Z_PK
            WHERE p.ZFULLNUMBER IS NOT NULL
              AND (r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL OR r.ZORGANIZATION IS NOT NULL)
        """):
            if not full_number or not name:
                continue
            norm = normalize_phone(full_number)
            if norm and "@" not in norm:
                ab[norm] = name.strip()

        # Emails
        for email, name in conn.execute(f"""
            SELECT e.ZADDRESS, {name_expr}
            FROM ZABCDEMAILADDRESS e
            JOIN ZABCDRECORD r ON e.ZOWNER = r.Z_PK
            WHERE e.ZADDRESS IS NOT NULL
              AND (r.ZFIRSTNAME IS NOT NULL OR r.ZLASTNAME IS NOT NULL OR r.ZORGANIZATION IS NOT NULL)
        """):
            if not email or not name:
                continue
            ab[email.lower().strip()] = name.strip()

        conn.close()
    except Exception as e:
        print(f"  [WARN] AddressBook lookup failed: {e}")

    return ab


# --- CRM loading ---

def load_crm() -> dict[str, dict]:
    """Load both CRM JSON files. Returns {name: {phone, email, ...}}."""
    people = {}
    for path in [CRM_DB, CRM_DB2]:
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for name, info in data.items():
                people[name] = info
    return people


def build_phone_index(crm: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Build reverse lookup: normalized_handle -> name.

    Checks both 'phone' and 'iMessage_handle' fields. The 'iMessage_handle'
    field allows matching contacts who use iMessage via email (common for
    contacts met in-person before getting their phone number).
    """
    phone_to_name = {}
    email_to_name = {}
    for name, info in crm.items():
        # Primary phone
        phone = normalize_phone(info.get("phone", ""))
        if phone and "@" not in phone:
            phone_to_name[phone] = name
        # Email
        email = (info.get("email") or "").lower().strip()
        if email:
            email_to_name[email] = name
        # iMessage_handle override (can be phone or email for iMessage matching)
        handle = normalize_phone(info.get("iMessage_handle", ""))
        if handle:
            if "@" in handle:
                email_to_name[handle] = name
            else:
                phone_to_name[handle] = name
    return phone_to_name, email_to_name


def load_gc_phone_index(crm_phones: set, crm_emails: set) -> dict[str, str]:
    """Load Google Contacts phone index → {normalized_phone: "Name"}.

    Only returns entries NOT already covered by crm_database.json so the CRM
    layer takes precedence. gc_phone_index.json has 1,014 entries and is the
    authoritative phone master for the full contacts list.

    Returns {normalized_handle: display_name} for GC-only contacts.
    """
    if not GC_PHONE_INDEX.exists():
        return {}
    try:
        with open(GC_PHONE_INDEX) as f:
            raw = json.load(f)
    except Exception:
        return {}

    gc = {}
    for handle, info in raw.items():
        name = info.get("name", "").strip()
        if not name:
            continue
        norm = normalize_phone(handle) if "@" not in handle else handle.lower().strip()
        if not norm:
            continue
        # Skip if already covered by CRM (CRM takes precedence)
        if norm in crm_phones or norm in crm_emails:
            continue
        gc[norm] = name
    return gc


# --- iMessage scanner ---

def scan_imessage(
    phone_to_name: dict, email_to_name: dict, all_phones: set,
    gc_phone_to_name: dict | None = None,
) -> tuple[dict[str, dict], dict[str, dict], list[dict]]:
    """Scan iMessage for last message date per CRM person + GC contacts + new contact detection.

    Returns:
        matched:      {name: {last_imessage, imessage_count_90d}}   — CRM people
        gc_matched:   {name: {last_imessage, imessage_count_90d}}   — GC-only people
        new_contacts: [{handle, message_count_90d, first_seen}]     — truly unknown
    """
    gc_phone_to_name = gc_phone_to_name or {}
    if not IMESSAGE_DB.exists():
        print(f"  [WARN] iMessage DB not found: {IMESSAGE_DB}")
        return {}, {}, []

    try:
        conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro&immutable=1", uri=True)
    except Exception as e:
        print(f"  [WARN] Cannot access iMessage DB (TCC/FDA restricted): {e}")
        return {}, {}, []
    conn.execute("PRAGMA query_only=ON")

    ninety_days_ns = int((NINETY_DAYS_AGO - APPLE_EPOCH).total_seconds() * IMESSAGE_NS_DIVISOR)
    # For new contact detection: first_seen
    ninety_days_first_ns = ninety_days_ns

    query = """
        SELECT
            h.id AS handle_id,
            MAX(m.date) AS last_date,
            COUNT(CASE WHEN m.date >= ? THEN 1 END) AS count_90d,
            MIN(CASE WHEN m.date >= ? THEN m.date END) AS first_seen_90d
        FROM message m
        JOIN handle h ON m.handle_id = h.ROWID
        GROUP BY h.id
    """

    matched    = {}   # CRM people
    gc_matched = {}   # GC-only people
    new_contacts = []

    for handle_id, last_date_ns, count_90d, first_seen_ns in conn.execute(
        query, (ninety_days_ns, ninety_days_first_ns)
    ):
        if not handle_id:
            continue

        # Resolve — CRM first, then GC
        name    = None
        gc_name = None
        if "@" in handle_id:
            h = handle_id.lower().strip()
            name = email_to_name.get(h)
            if not name:
                gc_name = gc_phone_to_name.get(h)
        else:
            norm = normalize_phone(handle_id)
            if norm:
                name = phone_to_name.get(norm)
                if not name:
                    gc_name = gc_phone_to_name.get(norm)

        last_date_str = None
        if last_date_ns and last_date_ns > 0:
            last_dt = APPLE_EPOCH + timedelta(seconds=last_date_ns / IMESSAGE_NS_DIVISOR)
            last_date_str = last_dt.strftime("%Y-%m-%d")

        def _accumulate(bucket: dict, key: str) -> None:
            if key in bucket:
                ex = bucket[key]
                if last_date_str and (not ex["last_imessage"] or last_date_str > ex["last_imessage"]):
                    ex["last_imessage"] = last_date_str
                ex["imessage_count_90d"] += count_90d
            else:
                bucket[key] = {"last_imessage": last_date_str, "imessage_count_90d": count_90d}

        if name:
            _accumulate(matched, name)
        elif gc_name:
            _accumulate(gc_matched, gc_name)
        else:
            # Truly unknown — collect for new contact detection
            if count_90d >= NEW_CONTACT_MIN_MSGS:
                first_seen_str = None
                if first_seen_ns and first_seen_ns > 0:
                    first_dt = APPLE_EPOCH + timedelta(seconds=first_seen_ns / IMESSAGE_NS_DIVISOR)
                    first_seen_str = first_dt.strftime("%Y-%m-%d")
                new_contacts.append({
                    "handle": handle_id,
                    "message_count_90d": count_90d,
                    "first_seen": first_seen_str,
                    "source": "imessage",
                })

    conn.close()
    return matched, gc_matched, new_contacts


# --- Call history scanner ---

def scan_calls(
    phone_to_name: dict, all_phones: set,
    gc_phone_to_name: dict | None = None,
) -> tuple[dict[str, dict], dict[str, dict], list[dict]]:
    """Scan call history. Returns CRM matched + GC matched + new contacts."""
    gc_phone_to_name = gc_phone_to_name or {}
    if not CALL_DB.exists():
        print(f"  [WARN] Call history DB not found: {CALL_DB}")
        return {}, {}, []

    try:
        conn = sqlite3.connect(f"file:{CALL_DB}?mode=ro&immutable=1", uri=True)
    except Exception as e:
        print(f"  [WARN] Cannot access Call history DB (TCC/FDA restricted): {e}")
        return {}, {}, []
    conn.execute("PRAGMA query_only=ON")

    ninety_days_s = (NINETY_DAYS_AGO - APPLE_EPOCH).total_seconds()

    query = """
        SELECT
            ZADDRESS,
            MAX(ZDATE) AS last_date,
            COUNT(CASE WHEN ZDATE >= ? THEN 1 END) AS count_90d,
            ZORIGINATED,
            MIN(CASE WHEN ZDATE >= ? THEN ZDATE END) AS first_seen_90d
        FROM ZCALLRECORD
        WHERE ZADDRESS IS NOT NULL AND ZADDRESS != ''
        GROUP BY ZADDRESS
    """

    matched    = {}
    gc_matched = {}
    new_contacts = []

    for address, last_date_s, count_90d, originated, first_seen_s in conn.execute(
        query, (ninety_days_s, ninety_days_s)
    ):
        if not address:
            continue
        norm = normalize_phone(address)
        if not norm:
            continue

        name    = phone_to_name.get(norm)
        gc_name = gc_phone_to_name.get(norm) if not name else None

        last_date_str = None
        if last_date_s and last_date_s > 0:
            last_dt = APPLE_EPOCH + timedelta(seconds=last_date_s)
            last_date_str = last_dt.strftime("%Y-%m-%d")

        direction = "outgoing" if originated == 1 else "incoming"

        def _accumulate_call(bucket: dict, key: str) -> None:
            if key in bucket:
                ex = bucket[key]
                if last_date_str and (not ex["last_call"] or last_date_str > ex["last_call"]):
                    ex["last_call"] = last_date_str
                    ex["last_call_direction"] = direction
                ex["call_count_90d"] += count_90d
            else:
                bucket[key] = {
                    "last_call": last_date_str,
                    "call_count_90d": count_90d,
                    "last_call_direction": direction,
                }

        if name:
            _accumulate_call(matched, name)
        elif gc_name:
            _accumulate_call(gc_matched, gc_name)
        else:
            if count_90d >= NEW_CONTACT_MIN_CALLS:
                first_seen_str = None
                if first_seen_s and first_seen_s > 0:
                    first_dt = APPLE_EPOCH + timedelta(seconds=first_seen_s)
                    first_seen_str = first_dt.strftime("%Y-%m-%d")
                new_contacts.append({
                    "handle": norm,
                    "call_count_90d": count_90d,
                    "first_seen": first_seen_str,
                    "source": "call",
                })

    conn.close()
    return matched, gc_matched, new_contacts


# --- Merge ---

def merge_results(crm: dict, imessage: dict, calls: dict) -> dict:
    """Merge iMessage and call data per CRM person."""
    people = {}
    for name in crm:
        im = imessage.get(name, {})
        cl = calls.get(name, {})

        last_imessage = im.get("last_imessage")
        last_call     = cl.get("last_call")

        dates = [d for d in [last_imessage, last_call] if d]
        last_contact = max(dates) if dates else None

        contact_count_90d = im.get("imessage_count_90d", 0) + cl.get("call_count_90d", 0)

        if last_contact or contact_count_90d > 0:
            # Determine platform from whichever was more recent
            if last_imessage and last_call:
                platform = PLATFORM_IMESSAGE if last_imessage >= last_call else PLATFORM_CALL
            elif last_imessage:
                platform = PLATFORM_IMESSAGE
            elif last_call:
                platform = PLATFORM_CALL
            else:
                platform = None

            entry = {
                "last_imessage": last_imessage,
                "last_call": last_call,
                "last_contact": last_contact,
                "contact_count_90d": contact_count_90d,
                "last_platform_detected": platform,
            }
            if cl.get("last_call_direction"):
                entry["last_call_direction"] = cl["last_call_direction"]
            people[name] = entry

    return people


def merge_new_contacts(im_new: list, call_new: list) -> list:
    """Deduplicate new contacts across iMessage and calls."""
    seen = {}
    for nc in im_new + call_new:
        h = nc["handle"]
        if h not in seen:
            seen[h] = nc
        else:
            # Merge counts
            seen[h]["message_count_90d"] = seen[h].get("message_count_90d", 0) + nc.get("message_count_90d", 0)
            seen[h]["call_count_90d"]    = seen[h].get("call_count_90d", 0) + nc.get("call_count_90d", 0)
            # Keep earliest first_seen
            if nc.get("first_seen") and (not seen[h].get("first_seen") or nc["first_seen"] < seen[h]["first_seen"]):
                seen[h]["first_seen"] = nc["first_seen"]
    return sorted(seen.values(), key=lambda x: -(x.get("message_count_90d", 0) + x.get("call_count_90d", 0)))


def merge_gc_results(im_gc: dict, call_gc: dict) -> dict:
    """Merge GC-only iMessage + call data into a contact activity dict.

    Same shape as merge_results() output but for people in Google Contacts
    who are not in crm_database.json. No CRM writeback for these.
    Returns {name: {last_contact, contact_count_90d, last_imessage, last_call, last_platform_detected}}
    """
    all_names = set(im_gc) | set(call_gc)
    result = {}
    for name in all_names:
        im = im_gc.get(name, {})
        cl = call_gc.get(name, {})
        last_imessage = im.get("last_imessage")
        last_call     = cl.get("last_call")
        dates = [d for d in [last_imessage, last_call] if d]
        last_contact = max(dates) if dates else None
        count = im.get("imessage_count_90d", 0) + cl.get("call_count_90d", 0)
        if last_imessage and last_call:
            platform = PLATFORM_IMESSAGE if last_imessage >= last_call else PLATFORM_CALL
        elif last_imessage:
            platform = PLATFORM_IMESSAGE
        elif last_call:
            platform = PLATFORM_CALL
        else:
            platform = None
        entry = {
            "last_imessage": last_imessage,
            "last_call": last_call,
            "last_contact": last_contact,
            "contact_count_90d": count,
            "last_platform_detected": platform,
        }
        if cl.get("last_call_direction"):
            entry["last_call_direction"] = cl["last_call_direction"]
        result[name] = entry
    return result


# --- CRM writeback ---

def write_crm_updates(people: dict, crm: dict, dry_run: bool = False) -> list[dict]:
    """Write last_contact_date, last_platform, contact_count_90d back to CRM JSON.

    Only updates if the new last_contact is more recent than what's stored.
    Never overwrites a more-recent date or an 'in_person' platform with a digital one.
    Returns list of change records for logging.
    """
    changes = []
    today = datetime.now().strftime("%Y-%m-%d")

    # Load the CRM file (single file since the 2026-07-06 batch2 merge —
    # every scanned person should now be present)
    with open(CRM_DB) as f:
        db = json.load(f)

    skipped = []
    for name, scan_data in people.items():
        if name not in db:
            skipped.append(name)  # should not happen post-merge — surface it
            continue

        entry = db[name]
        change = {"name": name, "fields": {}}

        # last_contact_date — only advance, never backdate
        scan_date = scan_data.get("last_contact")
        existing_date = entry.get("last_contact_date", "")
        if scan_date and (not existing_date or scan_date > existing_date):
            change["fields"]["last_contact_date"] = {
                "from": existing_date, "to": scan_date
            }
            if not dry_run:
                entry["last_contact_date"] = scan_date

        # last_platform — don't overwrite in_person with digital
        scan_platform = scan_data.get("last_platform_detected")
        existing_platform_raw = entry.get("last_platform")  # raw value, may be None
        existing_platform = normalize_platform(existing_platform_raw or "")
        if scan_platform and existing_platform_raw != PLATFORM_IN_PERSON:
            # Update if unset OR if detected platform differs from stored value
            if not existing_platform_raw or scan_platform != existing_platform:
                change["fields"]["last_platform"] = {
                    "from": entry.get("last_platform"), "to": scan_platform
                }
                if not dry_run:
                    entry["last_platform"] = scan_platform

        # contact_count_90d — always overwrite (it's a rolling window)
        new_count = scan_data.get("contact_count_90d", 0)
        existing_count = entry.get("contact_count_90d")
        if new_count != existing_count:
            change["fields"]["contact_count_90d"] = {
                "from": existing_count, "to": new_count
            }
            if not dry_run:
                entry["contact_count_90d"] = new_count

        # last_comm_scan — always set to today
        if not dry_run:
            entry["last_comm_scan"] = today

        if change["fields"]:
            changes.append(change)

    if skipped:
        print(f"  [WARN] {len(skipped)} scanned people missing from CRM DB (post-merge this "
              f"should be empty): {', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")

    if not dry_run:
        with open(CRM_DB, "w") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)

    return changes


# --- SAE cadence update ---

def update_sae_cadence(people: dict, gc_known: dict, dry_run: bool = False) -> int:
    """Advance 'last:' dates in the SAE Cadence Targets section from scan results.

    Matches each entry in the SAE cadence section by name, then advances its
    'last:' date if the scan found more recent activity. Never backdates.
    Updates both CRM people and GC-known people (SAE may contain either).

    Returns the number of entries updated.
    """
    if not SAE_FILE.exists():
        print(f"  [WARN] SAE file not found: {SAE_FILE}")
        return 0

    content = SAE_FILE.read_text(encoding="utf-8")

    # Build {name: last_contact} from both CRM and GC scan buckets
    scan_dates: dict[str, str] = {}
    for name, data in {**people, **gc_known}.items():
        last = data.get("last_contact")
        if last:
            scan_dates[name] = last

    updated = 0
    new_content = content

    for name, scan_date in scan_dates.items():
        # Match: "- Name (last: YYYY-MM-DD)" or "- Name (last: unknown)"
        pattern = rf"(- {re.escape(name)} \(last: )([^\)]+)(\))"
        match = re.search(pattern, new_content)
        if not match:
            continue

        current_str = match.group(2)

        if current_str == "unknown":
            should_update = True
        else:
            try:
                should_update = scan_date > current_str   # ISO date string comparison works
            except Exception:
                should_update = False

        if should_update:
            new_content = re.sub(pattern, rf"\g<1>{scan_date}\3", new_content, count=1)
            updated += 1
            print(f"    {name}: {current_str} → {scan_date}")

    if updated > 0 and not dry_run:
        SAE_FILE.write_text(new_content, encoding="utf-8")

    return updated


# --- Logging ---

def write_log(changes: list, people: dict, new_contacts: list, dry_run: bool):
    """Write a dated log file summarizing what changed."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"comm_scan_log_{today}.json"
    log = {
        "date": today,
        "dry_run": dry_run,
        "crm_updates": changes,
        "new_contacts_detected": new_contacts,
        "total_matched": len(people),
        "total_changes": len(changes),
    }
    if not dry_run:
        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)
        print(f"  Log written: {log_path}")
    else:
        print(f"  [DRY RUN] Would write log to {log_path}")
    return log


# --- Main ---

def main():
    dry_run   = "--dry-run"   in sys.argv
    write_crm = "--write-crm" in sys.argv

    print("=== Communication Intelligence Scanner (Phase A) ===\n")

    # 1. Load CRM
    print("[1/5] Loading CRM database...")
    crm = load_crm()
    phone_to_name, email_to_name = build_phone_index(crm)
    all_phones = set(phone_to_name.keys())
    print(f"  {len(crm)} people  |  {len(phone_to_name)} phones  |  {len(email_to_name)} emails")

    # Identify manual-only contacts (no phone, no email, no iMessage_handle)
    manual_only = [
        name for name, info in crm.items()
        if not info.get("phone") and not info.get("email") and not info.get("iMessage_handle")
    ]
    if manual_only:
        print(f"  Manual-only (no trackable handle): {', '.join(manual_only[:8])}{'...' if len(manual_only) > 8 else ''}")

    # Load Google Contacts phone index (1,014 entries — the phone master)
    gc_phone_to_name = load_gc_phone_index(set(phone_to_name.keys()), set(email_to_name.keys()))
    print(f"  GC phone index: {len(gc_phone_to_name)} additional contacts loaded")

    # 2. Scan iMessage
    print("[2/5] Scanning iMessage...")
    imessage, im_gc, im_new = scan_imessage(phone_to_name, email_to_name, all_phones, gc_phone_to_name)
    print(f"  {len(imessage)} CRM  |  {len(im_gc)} GC contacts  |  {len(im_new)} unknown candidates")

    # 3. Scan calls
    print("[3/5] Scanning call history...")
    calls, call_gc, call_new = scan_calls(phone_to_name, all_phones, gc_phone_to_name)
    print(f"  {len(calls)} CRM  |  {len(call_gc)} GC contacts  |  {len(call_new)} unknown candidates")

    # 4. Merge
    print("[4/5] Merging results...")
    people       = merge_results(crm, imessage, calls)
    gc_known     = merge_gc_results(im_gc, call_gc)
    new_contacts = merge_new_contacts(im_new, call_new)

    # Enrich truly-unknown new_contacts with AddressBook names as last resort
    print("  Loading AddressBook for unknown handle enrichment...")
    address_book = load_address_book()
    print(f"  {len(address_book)} AddressBook entries")
    for nc in new_contacts:
        handle = nc["handle"]
        if "@" in handle:
            nc["name"] = address_book.get(handle.lower())
        else:
            norm = normalize_phone(handle)
            nc["name"] = address_book.get(norm) if norm else None

    output = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "source": "iMessage + CallHistory",
        "crm_total": len(crm),
        "matched": len(people),
        "gc_known_count": len(gc_known),
        "manual_only_contacts": manual_only,
        "people": dict(sorted(people.items(), key=lambda x: x[1].get("last_contact") or "", reverse=True)),
        "gc_known": dict(sorted(gc_known.items(), key=lambda x: x[1].get("last_contact") or "", reverse=True)),
        "new_contacts": new_contacts[:20],  # cap at 20 — truly unknown handles
    }

    if dry_run:
        print(json.dumps(output, indent=2))
    else:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2)
        print(f"  Written: {OUTPUT_FILE}")

    # 5. CRM writeback + SAE cadence update (if requested)
    changes = []
    if write_crm or dry_run:
        label = "[DRY RUN] " if dry_run else ""
        print(f"[5/5] {label}Writing back to CRM database...")
        changes = write_crm_updates(people, crm, dry_run=dry_run)
        print(f"  {len(changes)} records would be updated" if dry_run else f"  {len(changes)} records updated")
        for c in changes[:10]:
            fields_str = ", ".join(f"{k}: {v['from']} → {v['to']}" for k, v in c["fields"].items())
            print(f"    {c['name']}: {fields_str}")
        if len(changes) > 10:
            print(f"    ... and {len(changes)-10} more")

        print(f"  {label}Updating SAE cadence dates...")
        sae_updates = update_sae_cadence(people, gc_known, dry_run=dry_run)
        verb = "would advance" if dry_run else "advanced"
        print(f"  {sae_updates} SAE cadence dates {verb}")

        write_log(changes, people, new_contacts, dry_run=dry_run)
    else:
        print("[5/5] Skipped CRM writeback (use --write-crm to apply)")

    # Summary
    print(f"\n=== Summary ===")
    print(f"  CRM ({len(crm)}): {len(people)} matched  |  GC-known: {len(gc_known)}  |  Unknown: {len(new_contacts)}  |  Manual-only: {len(manual_only)}")
    if write_crm and not dry_run:
        print(f"  CRM records updated: {len(changes)}")

    sorted_people = sorted(people.items(), key=lambda x: x[1].get("last_contact") or "", reverse=True)
    print(f"\n  Most recent CRM contacts:")
    for name, info in sorted_people[:5]:
        print(f"    {name}: {info['last_contact']}  (90d: {info['contact_count_90d']})")

    if gc_known:
        sorted_gc = sorted(gc_known.items(), key=lambda x: x[1].get("last_contact") or "", reverse=True)
        print(f"\n  Most recent GC contacts (in Google Contacts, not CRM):")
        for name, info in sorted_gc[:5]:
            print(f"    {name}: {info['last_contact']}  (90d: {info['contact_count_90d']})")

    if new_contacts:
        print(f"\n  Truly unknown handles (not in any contact list):")
        for nc in new_contacts[:5]:
            msgs = nc.get("message_count_90d", 0)
            calls_c = nc.get("call_count_90d", 0)
            label = f" ({nc['name']})" if nc.get("name") else ""
            print(f"    {nc['handle']}{label}  msgs:{msgs}  calls:{calls_c}  first:{nc.get('first_seen')}")


if __name__ == "__main__":
    main()
