# Venue Refresh Guide — Monthly Event Monitoring

## How to Use

Run venue calendar checks on this schedule to keep the curated EVENTS list fresh. Each venue has a proven scrape method and calendar URL.

---

## Tier 1 — Weekly (High-Volume Music Venues)

These generate 4-8 new events per month. Check every Monday.

| Venue | Calendar URL | Scrape Method | Notes |
|-------|-------------|---------------|-------|
| Terminal West | https://www.terminalwestatl.com/events | AXS API or scrape | ~900 cap, best sound in ATL |
| The Eastern | https://www.easternatl.com/events | AXS API or scrape | ~1000 cap, EAV |
| Variety Playhouse | https://www.variety-playhouse.com/events | Aggregator fallback (concerts50.com) | 403 on direct scrape |
| The Masquerade | https://www.masqueradeatlanta.com/events | Direct HTML scrape | 3 rooms: Heaven/Purgatory/Hell |
| District Atlanta | https://www.districtatlanta.com/events | Eventbrite search | Warehouse/techno, 21+ |
| Believe Music Hall | https://www.believeatl.com/events | IRIS Presents listings | EDM-heavy programming |

**Scrape command:**
```bash
# AXS venues (Terminal West, The Eastern)
npx firecrawl-cli scrape "https://www.axs.com/venues/1182/terminal-west" --format json

# District Atlanta (Eventbrite)
npx firecrawl-cli search "site:eventbrite.com district atlanta 2026"

# 19hz.info (best for underground electronic)
npx firecrawl-cli scrape "https://19hz.info/eventlisting_Atlanta.php"
```

---

## Tier 2 — Biweekly (Cultural & Family Institutions)

Check every other Monday. Seasonal programming changes quarterly.

| Venue | Calendar URL | Scrape Method | Notes |
|-------|-------------|---------------|-------|
| High Museum of Art | https://high.org/events | og:image works, scrape event list | Second Sundays free, Jazz Fridays |
| Fernbank Museum | https://www.fernbankmuseum.org/experiences | Direct scrape | After Dark (monthly), seasonal exhibits |
| Atlanta Botanical Garden | https://atlantabg.org/events | Direct scrape | Garden Lights (winter), Summer Nights |
| Georgia Aquarium | https://www.georgiaaquarium.org/events | Direct scrape | Sips Under the Sea (adults), seasonal |
| Fox Theatre | https://www.foxtheatre.org/events | Direct scrape or Ticketmaster | Broadway, concerts, comedy |
| Center for Puppetry Arts | https://puppet.org/shows | Direct scrape | Family shows, Jim Henson museum |
| Alliance Theatre | https://www.alliancetheatre.org/season | Direct scrape | Season announced annually |
| Atlanta History Center | https://www.atlantahistorycenter.com/events | Direct scrape | Spring Fest, seasonal exhibits |

---

## Tier 3 — Monthly (Comedy, Jazz, Intimate)

Check first Monday of each month.

| Venue | Calendar URL | Scrape Method | Notes |
|-------|-------------|---------------|-------|
| Dad's Garage | https://dadsgarage.com/shows | Direct scrape | Improv, original shows, kids shows |
| Laughing Skull Lounge | https://www.laughingskulllounge.com/shows | Direct scrape | Stand-up, open mic |
| Eddie's Attic | https://www.eddiesattic.com/calendar | Direct scrape | Acoustic, singer-songwriter |
| Blind Willie's | https://www.blindwillies.com/ | Direct scrape | Blues, jazz |
| The Earl | https://www.theearlatl.com/calendar | Direct scrape | Indie, punk, EAV |
| 529 | https://www.529atlanta.com/ | Direct scrape | Punk, hardcore, EAV |
| Plaza Theatre | https://www.plazaatlanta.com/calendar | Direct scrape | Indie film, midnight movies |
| Velvet Note | https://www.thevelvetnote.com/events | Direct scrape | Jazz supper club, Alpharetta |
| The Moth Atlanta | https://themoth.org/events | Direct scrape | StorySLAM monthly |
| Atlanta Comedy Theater | https://atlantacomedytheater.com/ | Direct scrape | Improv, sketch |

---

## Tier 4 — Discovery (Aggregators)

Check monthly for new/unknown events.

| Source | URL | Method | Best For |
|--------|-----|--------|----------|
| 19hz.info | https://19hz.info/eventlisting_Atlanta.php | WebFetch + parse HTML table | Underground electronic, warehouse |
| Songkick | https://www.songkick.com/metro/26330-atlanta | Firecrawl scrape | Concert aggregation |
| Bandsintown | https://www.bandsintown.com/ | Needs browser automation (403) | Artist-based discovery |
| EDMTrain | https://edmtrain.com/atlanta-ga | Needs browser (JS-heavy) | Electronic music calendar |
| Resident Advisor | https://ra.co/events/us/atlanta | Needs browser (403) | Club/electronic scene |
| Eventbrite Atlanta | https://www.eventbrite.com/d/ga--atlanta/events/ | Firecrawl search | Mixed: workshops, markets, fairs |

---

## Seasonal Refresh Triggers

| When | What to Check |
|------|---------------|
| January | Garden Lights wrap-up, spring festival announcements |
| March | Dogwood Festival, Atlanta Film Festival, SweetWater 420 |
| April | Inman Park Festival, Jazz Fest lineup, Shaky Knees early-bird |
| May | Summerfest announcements, outdoor season begins |
| July | 4th of July events (Peachtree Road Race), summer concert series |
| September | Shaky Knees, Music Midtown, Dragon Con |
| October | Halloween events, fall festivals, pumpkin patches |
| November | Holiday market season begins, Garden Lights tickets |

---

## Scraping Playbooks (Proven)

### What Works Now
| Method | Tool | Venues |
|--------|------|--------|
| Direct HTML scrape | `npx firecrawl-cli scrape [url]` | Most venue sites |
| AXS event listings | `npx firecrawl-cli scrape "axs.com/venues/[id]"` | Terminal West, The Eastern, Variety |
| Eventbrite search | `npx firecrawl-cli search "site:eventbrite.com [venue]"` | District, Believe, general |
| 19hz.info table | `urllib.request` + HTML table parse | Electronic scene |
| og:image extraction | `scripts/enrich_events.py --fetch` | Any site with meta tags |

### What's Broken (Need Browser Automation)
| Source | Issue | Workaround |
|--------|-------|------------|
| Variety Playhouse direct | 403 Forbidden | Use concerts50.com or AXS |
| RA.co | Bot protection | Manual browse or Firecrawl browser mode |
| Bandsintown | API requires auth | Use Songkick instead |
| EDMTrain | JavaScript-rendered | Firecrawl browser mode: `npx firecrawl-cli browser` |
| Ticketmaster | Rate limiting | Search via firecrawl, not direct scrape |

### Full Refresh Workflow (60 min)
From `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/REFRESH_WORKFLOW.md`:

1. **19hz.info scan** (10 min) — electronic events, parse table
2. **Tier 1 venue scrapes** (15 min) — Terminal West, Eastern, Masquerade, District, Believe
3. **Tier 2 institutional check** (10 min) — museums, gardens, theaters
4. **Aggregator sweep** (10 min) — Songkick, Eventbrite
5. **Dedup + score** (15 min) — consolidate_scrape.py pattern, taste_matcher_v2.py scoring

---

## Reference Files

| File | Location | Purpose |
|------|----------|---------|
| ALTERNATIVE_DATA_SOURCES.md | `~/Documents/Brain/04_Archive/Projects/2025-12-06_ATL-Event-List/` | Source reliability ratings |
| REFRESH_WORKFLOW.md | same | 60-min weekly refresh cycle |
| REFRESH_PLAN_JAN_AUG_2026.md | same/planning/ | Venue batches by priority |
| Atlanta_Events_Guide.md | same | Full venue directory + calendar URLs |
| venue_branding.json | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/planning/` | Venue logos, colors, vibes |
| TASTE_PROFILE.md | same | Genre scoring framework |
| consolidate_scrape.py | `~/Documents/Coding/Projects/2026-01-24_atl-event-list/` | Batch JSON merge + dedup |
| taste_matcher_v2.py | same | Two-mode enrichment pipeline |
| firecrawl-batch.sh | `~/Documents/Coding/Projects/2025-11-06_brain-scripts/` | Batch scraping with rate limiting |
| enrich_events.py | `ATL-Events-Site/scripts/` | Current enrichment pipeline |
| ENRICHMENT-METHODOLOGY.md | `ATL-Events-Site/` | How the enrichment pipeline works |
