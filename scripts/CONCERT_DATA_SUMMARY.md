# ATL Concert/Event Data Discovery Report
**Generated:** 2026-04-21

## Executive Summary
Located **14 data files** across two projects with **1,471 total event entries** and **127 unique venues**. High duplication across sources. Identified **37 new candidate events** for April 2026 not in current 28-event curated list.

## Data Files Found

### Primary Location: `/Users/dmitriyperkis/Documents/Coding/Projects/2026-01-24_atl-event-list/`

| File | Format | Events | Date Range | Notes |
|------|--------|--------|-----------|-------|
| `ATL Event List 2025-2026 - Master.csv` | CSV | 517 | Various | Most comprehensive; includes all categories |
| `results/batch_a_1.json` | JSON | 30 | Jan-Jun 2026 | From AXS, Songkick, Bandsintown |
| `results/batch_a_2.json` | JSON | 174 | Jan-Sep 2026 | **Largest batch; best for future events** |
| `results/batch_a_3.json` | JSON | 45 | Mar-Jun 2026 | Curated music events |
| `results/batch_b.json` | JSON | 13 | Apr-May 2026 | High Museum, cultural events |
| `results/batch_c.json` | JSON | 17 | Apr-Jun 2026 | Mixed genres |
| `results/batch_d.json` | JSON | 33 | Feb-Jun 2026 | Electronic & indie focus |
| `results/distilled_batch.json` | JSON | 82 | Various | Summarized with interest scores |
| `results/distilled_batch_2.json` | JSON | 60 | Various | Secondary distillation batch |
| `results/distilled_batch_summer.json` | JSON | 7 | Summer 2026 | Summer-specific events |
| `results/gap_fill_june_aug.json` | JSON | 2 | Jun-Aug 2026 | Fill gaps in summer schedule |

### Archive Location: `/Users/dmitriyperkis/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/`

| File | Format | Events | Date Range | Notes |
|------|--------|--------|-----------|-------|
| `ATL Event List 2025-2026 - Master.csv` | CSV | 344 | Various | Earlier version; lower event count |
| `Archive/2025-11-12-original-export/ATL Event List 2025 - ATL Events Aug-Oct.csv` | CSV | 128 | Aug-Oct 2025 | Seasonal focus; historical |
| `Archive/2025-11-12-original-export/ATL Event List 2025 - Sheet1.csv` | CSV | 27 | Various | Structured program data |
| `Archive/2025-11-12-original-export/Atlanta Events Hub - Expanded Through October 2025.csv` | CSV | 55 | Through Oct 2025 | Legacy listing |

## Key Venues (Top 10)

| Venue | Event Count |
|-------|------------|
| The Masquerade | 192 |
| Hell at The Masquerade | 123 |
| Purgatory at The Masquerade | 86 |
| Heaven at The Masquerade | 84 |
| Terminal West | 84 |
| Altar at The Masquerade | 72 |
| The Eastern | 67 |
| Believe Music Hall | 60 |
| Variety Playhouse | 59 |
| District Atlanta | 42 |

## Data Schema Differences

### CSV Format (Traditional)
```
Start Date | End | Event_Name | Venue | Going | Interested | Category | Sub_Category | Price_Range | Family_Level | Link
```

### JSON Format (New Data)
```json
{
  "event_name": "string",
  "start_date": "YYYY-MM-DD",
  "venue": "string",
  "ticket_link": "url",
  "price_range": "string",
  "description": "string",
  "image_url": "url",
  "scrape_source": "url"
}
```

## April 2026 Sample Events (Not in Curated 28)

1. **Varials** @ Hell at The Masquerade — 2026-04-01
2. **Bryant Barnes: SOLACE TOUR** @ Terminal West — 2026-04-01
3. **Slomosa** @ Purgatory at The Masquerade — 2026-04-02
4. **Boogie T** @ Believe Music Hall — 2026-04-03
5. **William Black** @ The Eastern — 2026-04-03
6. **Atlanta Ballet: Golden Hour** @ Cobb Energy Centre — 2026-04-03
7. **NateWantsToBattle** @ Hell at The Masquerade — 2026-04-04
8. **In Color** @ Altar at The Masquerade — 2026-04-04
9. **RJD2** @ Terminal West — 2026-04-04
10. **The Format** @ The Eastern — 2026-04-04

## Data Quality & Recommendations

### Issues Identified
- **High Duplication**: Same events appear in multiple CSVs and JSONs (need deduplication)
- **Inconsistent Venue Names**: "The Masquerade" vs "Hell at The Masquerade" vs "Masquerade (Hell)"
- **Placeholder Entries**: Many "The Masquerade presents..." entries without specific show details
- **Generic Descriptions**: JSON `description` fields often match ticket sources rather than curated commentary

### Recommendations for Expansion
1. **Primary Source**: Use `batch_a_2.json` (174 events, most complete 2026 data)
2. **Deduplication**: Match on (title + venue + date) to avoid duplicates
3. **Scoring**: Use `distilled_batch_*.json` interest_score fields for prioritization
4. **Summer Gap**: `gap_fill_june_aug.json` has only 2 events — need additional research
5. **Venue Consolidation**: Map venue variants to canonical names before insertion
6. **Image Priority**: Prefer events with `image_url` populated from JSON batches
7. **Ticket Links**: Prioritize events with valid `ticket_link` URLs for user engagement

## Quick Access Paths

**Best source for new events:**
```
/Users/dmitriyperkis/Documents/Coding/Projects/2026-01-24_atl-event-list/results/batch_a_2.json
```

**Full analysis report:**
```
/Users/dmitriyperkis/Documents/Coding/Projects/2026-04-21_ATL-Events-Site/scripts/concert_csv_report.json
```

**Comprehensive CSV listing:**
```
/Users/dmitriyperkis/Documents/Coding/Projects/2026-01-24_atl-event-list/ATL Event List 2025-2026 - Master.csv
```

## Next Steps
1. Load `batch_a_2.json` into processing pipeline
2. Deduplicate against current data.js events
3. Normalize venue names
4. Prioritize events with images + ticket links
5. Run through scoring algorithm (see atl-events skill)
6. QA before merging into curated list
