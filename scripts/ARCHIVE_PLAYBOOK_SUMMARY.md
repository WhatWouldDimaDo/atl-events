# ATL Events Archive Playbook Summary

**Source:** `/Users/dmitriyperkis/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List`  
**Generated:** 2026-04-21  
**Purpose:** Scraping strategies, venue refresh lists, and event data from archived ATL Events project

---

## One-Minute Overview

The archived project contains a battle-tested event discovery system covering 40+ Atlanta venues. Key insight: **Only 19hz.info works via WebFetch. Everything else requires browser automation.**

### Data Available
- **Master CSV:** 200-350 events (Nov 2025 - Aug 2026)
- **Venues tracked:** 20 primary venues
- **Scraping methods:** 8 documented approaches
- **Evergreen events:** 7 recurring seasonal/permanent offerings

---

## Priority Venues (Must-Have)

| Venue | Scrape Via | Events/Mo | Status |
|-------|-----------|-----------|--------|
| **Terminal West** | AXS.com | 20-30 | 403 blocked, use AXS |
| **Variety Playhouse** | AXS.com | 15-20 | 403 blocked, use AXS |
| **The Eastern** | AXS.com | 15-20 | 403 blocked, use AXS |
| **District Atlanta** | Eventbrite/Direct | 15-25 | Partially working |
| **The Masquerade** | Direct webfetch | 25-40 | Works for list, needs detail pages |

---

## Working Data Sources

### ✅ 19hz.info — Electronic Music (Already Scraped)
- **Coverage:** 25+ electronic events
- **Venues:** Terminal West, Masquerade, District, Believe, Tabernacle, Eastern, Lunchbox
- **Method:** Direct WebFetch (no bot protection)
- **Status:** Complete, ready to use

### ✅ Eventbrite — All Categories
- **Coverage:** 50-100+ events
- **Method:** Browser pagination required
- **Categories:** Music, Comedy, Food, Nightlife, Art, Family
- **Status:** Partially accessible without browser

### ✅ Direct Venue Scrapes (Already Done)
- Dad's Garage: 2 events ✓
- Georgia Aquarium: 3 events ✓
- Atlanta Botanical Garden: 4 events ✓
- Fox Theatre: 2 events ✓

---

## Blocked Sources (Need Browser Automation)

| Source | Events Expected | Challenge | Alternative |
|--------|-----------------|-----------|------------|
| **Ticketmaster** | 30-50 | 403 Forbidden | Use via aggregators |
| **AXS.com** | 60-90 | 403 Forbidden | *Must use browser* |
| **EDMTrain** | 40-60 | JavaScript-heavy | Browser render required |
| **RA.co** | 20-30 | 403 Forbidden | Use EDMTrain instead |
| **Bandsintown** | 30-50 | 403 Forbidden | Use Eventbrite instead |

---

## Key CSV Data

### Master File
- **Location:** `ATL Event List 2025-2026 - Master.csv`
- **Total Events:** ~200-350 (full coverage expected)
- **Date Range:** Nov 12, 2025 - Aug 31, 2026
- **Columns:** 15 (Start Date, Venue, Category, Price, Family Level, Notes, Spotify Link, etc.)

### Evergreen Candidates (Recurring/Seasonal)
1. Garden Lights Holiday Nights (Nov-Dec, annual)
2. Puppet shows at Center for Puppetry Arts (year-round schedule)
3. RNB at 9AM (The Eastern, weekly Saturday)
4. Reggae on the Roof (Cafe Circa, weekly Saturday)
5. LYFE ATL (Saturday night series, free RSVP)

---

## Technical Approach

### Scraping Playbook (Priority Order)

**Phase 1 — High ROI (Do First)**
1. AXS.com browser scrape → Terminal West, Variety, Eastern (50-90 events)
2. Ticketmaster browser scrape → Major venues (30-50 events)
3. EDMTrain browser scrape → Electronic completeness (40-60 events)

**Phase 2 — Medium ROI**
4. Eventbrite pagination → All categories (50-100 events)
5. RA.co browser scrape → Underground/club (20-30 events)

**Phase 3 — Gap Filling**
6. Bandsintown → Touring acts (20-30 events)
7. High Museum browser → Exhibitions (10-15 events)
8. Fernbank Museum browser → Exhibits (5-10 events)

### Python Scripts Available
- `add_new_events.py` — Template for bulk event ingestion
- `consolidate_csvs.py` — Merge, dedupe, filter past events
- `taste_matcher_v2.py` — LLM enrichment (rewrite descriptions by taste)
- `fetch_assets.py` — Download posters & venue logos

### Workflow
1. Scrape data → JSON intermediate format
2. Validate & deduplicate (Event_Name + Venue + Date)
3. Run enrichment pipeline (descriptions, interest scores)
4. Consolidate to Master CSV
5. Remove past events monthly

**Time per refresh:** ~60 minutes (including browser tasks)

---

## Data Quality Standards

### Duplicate Rule
An event is duplicate if: **Event_Name + Venue + Date match exactly**  
Resolution: Keep entry with most complete metadata (longest notes)

### Required Fields
- **Start Date:** "Fri 11/15" or "2025-11-15"
- **Category:** Music, Comedy, Family, Theatre, Cultural, Festival
- **Family_Level:** All Ages, 18+, 21+, Family Friendly
- **Price_Range:** "$20-30", "TBD", or "Free"

### Good vs Excellent Refresh

**Good:**
- 15-30 new events/session
- 0 duplicates in final CSV
- 80%+ events have notes/links

**Excellent:**
- 30-50 new events
- Spotify/Setlist.fm links added
- Rich "why this matches you" notes
- Family_Level verified
- All links tested

---

## Critical Blockers & Workarounds

### 403 Forbidden → Use Aggregators
- Ticketmaster blocked → Use AXS/Eventbrite for same venues
- Terminal West blocked → Use AXS.com search
- Variety Playhouse blocked → Use AXS.com search
- The Eastern blocked → Use AXS.com search

### JavaScript-Heavy → Browser Required
- EDMTrain → Wait for JavaScript render, then scroll
- High Museum → Use browser for calendar search
- Zoo Atlanta → Access via Eventbrite instead

### Missing Data → Use Alternative Source
- Individual venue pages all blocked → Pivot to ticketing platforms
- Minimal descriptions on list views → Scrape individual event pages

---

## Expected Coverage After Full Implementation

- **Total Events:** 200-350
- **Venues Fully Covered:** 40+
- **Electronic Music:** 100-150
- **Comedy/Theater:** 30-50
- **Family Activities:** 20-30
- **Food/Festival:** 20-40
- **Other:** 30-50

---

## Files in Archive

**Documentation:**
- ALTERNATIVE_DATA_SOURCES.md (comprehensive source analysis)
- REFRESH_WORKFLOW.md (step-by-step refresh process)
- BROWSER_AUTOMATION_GUIDE.md (browser task instructions)
- Atlanta_Events_Guide.md (PRD + venue directory)
- REFRESH_PLAN_JAN_AUG_2026.md (agentic execution plan)
- SCRAPING_TECHNICAL_LOG.md (technical methods used)
- REMEDIATION_LOG_JAN_2026.md (quality improvements applied)

**Data:**
- ATL Event List 2025-2026 - Master.csv (primary event database)
- Archive/ subfolder with original exports

---

## Recommendations for Current Site

1. **Immediate:** Use 19hz.info as data source (working today)
2. **Short-term:** Implement AXS.com browser scraping (highest ROI)
3. **Medium-term:** Set up taste_matcher_v2.py enrichment pipeline
4. **Ongoing:** Weekly refresh of priority venues, monthly deep refresh

---

**Full JSON report available:** `archive_playbook_report.json`
