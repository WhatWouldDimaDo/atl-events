/* ============================================================
   ATL Radar — app.js
   Wizard · Agenda Calendar · Events Grid + Drawers · Map · Evergreen
============================================================ */

const SITE_TODAY = new Date();

// ─── MODE DETECTION ───────────────────────────────────────────────────────
const INTERNAL = new URLSearchParams(location.search).get('mode') === 'internal';
if (INTERNAL) document.documentElement.classList.add('internal');

// ─── RSVP SIGNALS (localStorage, internal only) ──────────────────────────
function getRSVP(id) {
  if (!INTERNAL) return null;
  return localStorage.getItem(`rsvp_${id}`);
}

function setRSVP(id, signal) {
  if (!INTERNAL) return;
  const current = getRSVP(id);
  if (current === signal) {
    localStorage.removeItem(`rsvp_${id}`);
  } else {
    localStorage.setItem(`rsvp_${id}`, signal);
  }
  // Re-render buttons wherever they appear (peek row + bottom sheet)
  for (const cid of [`rsvp-${id}`, `bs-rsvp-${id}`]) {
    const container = document.getElementById(cid);
    if (container) container.innerHTML = rsvpButtonsHTML(id);
  }
  // Update card badge
  const card = document.querySelector(`.event-card[data-id="${id}"]`);
  if (card) {
    const newSignal = getRSVP(id);
    card.classList.remove('rsvp-in', 'rsvp-maybe', 'rsvp-pass', 'rsvp-attended');
    if (newSignal) card.classList.add(`rsvp-${newSignal}`);
  }
  updateHeroStats();
}

function rsvpButtonsHTML(id) {
  const current = getRSVP(id);
  // "Went" (Rec 2): only for past events, or to promote an existing "I'm In"
  const ev = EVENTS.find(e => e.id === id);
  const isPast = ev && new Date(ev.date) < SITE_TODAY;
  const wentBtn = (isPast || current === 'in' || current === 'attended')
    ? `<button class="rsvp-btn rsvp-went${current==='attended'?' active':''}" onclick="setRSVP(${id},'attended');event.stopPropagation()">Went ✓</button>`
    : '';
  return `<div class="rsvp-row">
    <button class="rsvp-btn${current==='in'?' active':''}" onclick="setRSVP(${id},'in');event.stopPropagation()">I'm In</button>
    <button class="rsvp-btn${current==='maybe'?' active':''}" onclick="setRSVP(${id},'maybe');event.stopPropagation()">Maybe</button>
    <button class="rsvp-btn${current==='pass'?' active':''}" onclick="setRSVP(${id},'pass');event.stopPropagation()">Pass</button>
    ${wentBtn}
  </div>`;
}

// ─── DRIVE TIME (item 9) — estimated minutes from Va-Highland, no API ───────
const HOME = { lat: 33.7885, lng: -84.3565 };

function driveMinutes(ev) {
  if (!ev.lat || !ev.lng) return null;
  const R = 3959, toR = d => d * Math.PI / 180;
  const dLat = toR(ev.lat - HOME.lat), dLng = toR(ev.lng - HOME.lng);
  const a = Math.sin(dLat/2)**2 + Math.cos(toR(HOME.lat)) * Math.cos(toR(ev.lat)) * Math.sin(dLng/2)**2;
  const miles = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  if (miles < 0.9) return null;             // walkable — skip the car icon
  return Math.round(5 + miles * 2.8);       // ~21 mph city avg + parking overhead
}

// ─── URGENCY DECAY (item 7) — ticketed events inside 10 days get a countdown ─
function soonChip(ev) {
  if (ev.urgent || ev.free || !ev.ticketUrl) return '';
  const days = Math.ceil((new Date(ev.date) - SITE_TODAY) / 86400000);
  if (days < 0 || days > 10) return '';
  if (INTERNAL && ['in', 'pass', 'attended'].includes(getRSVP(ev.id))) return '';
  return `<span class="er-soon">⏳${days === 0 ? 'today' : days + 'd'}</span>`;
}

// ─── SOCIAL LAYER (Track D / Rec 4 — internal mode only) ────────────────────
// First names only: this file ships publicly (repo + site), full identities
// stay in social_scan.py / the CRM. Panel renders only when INTERNAL.
const FRIEND_SLOTS = {
  GROUP_NIGHT: { label: 'Concert Squad',
                 names: ['David', 'Craig', 'Davis', 'Arjun', 'James', 'Jeff', 'Cole'] },
  FAMILY_OUT:  { label: 'Kids Crew',
                 names: ['Davis', 'Craig', 'Liam', 'Josh', 'Chris', 'Ted', 'Ben', 'Shubh'] },
  DATE_NIGHT:  { label: 'Couples',
                 names: ['Arjun+Kirsten', 'Jeff+Liz', 'James+Gray', 'Craig+Shannon'] },
  LAST_MINUTE: { label: 'Close By',
                 names: ['Davis', 'Robert', 'Craig', 'Jon'] },
};

function generateDraftText(ev, slot) {
  const when = ev.dateStr + (ev.time ? ` · ${ev.time}` : '');
  let msg;
  if (slot === 'FAMILY_OUT') {
    msg = `${ev.title} — ${when} at ${ev.venue}. Bringing Dean, want to join with the kids?`;
  } else if (slot === 'DATE_NIGHT') {
    msg = `${ev.title} — ${when} at ${ev.venue}. Want to make it a double date?`;
  } else {
    msg = `${ev.title} — ${when} at ${ev.venue}. You in?`;
  }
  const link = ev.ticketUrl || ev.officialUrl;
  return link ? `${msg}\n${link}` : msg;
}

function inviteSlotFor(ev) {
  return (ev.slots || []).find(s => FRIEND_SLOTS[s]) || null;
}

function copyInviteText(evId) {
  const ev = EVENTS.find(e => e.id === evId);
  if (!ev) return;
  const slot = inviteSlotFor(ev);
  if (!slot) return;
  navigator.clipboard.writeText(generateDraftText(ev, slot));
  const btn = document.querySelector(`.invite-copy-btn[data-id="${evId}"]`);
  if (btn) { btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy Text', 1400); }
}

// ─── WIZARD STATE ──────────────────────────────────────────────────────────
const wizard = { when: null, who: null, vibe: null };

function wizardSlotMap(who) {
  return { solo: ['SOLO_RESET'], dean: ['FAMILY_OUT'], family: ['FAMILY_OUT'],
           date: ['DATE_NIGHT'], friends: ['GROUP_NIGHT'], papa: ['PAPA_DEAN'] }[who] || null;
}

function wizardEventFilter(ev) {
  const evDate = new Date(ev.date);
  if (wizard.when) {
    if (wizard.when === 'now') {
      const diff = (evDate - SITE_TODAY) / 86400000;
      if (diff < 0 || diff > 3) return false;
    } else if (wizard.when === 'weekend') {
      const dow = SITE_TODAY.getDay();
      const satOff = dow === 0 ? -1 : 6 - dow;
      const sat = new Date(SITE_TODAY); sat.setDate(sat.getDate() + satOff);
      const sun = new Date(sat); sun.setDate(sun.getDate() + 1);
      const satStr = sat.toISOString().slice(0, 10);
      const sunStr = sun.toISOString().slice(0, 10);
      if (ev.date < satStr || ev.date > sunStr) return false;
    }
  }
  if (wizard.who) {
    const slots = wizardSlotMap(wizard.who);
    if (slots && !slots.some(s => ev.slots.includes(s))) return false;
  }
  if (wizard.vibe) {
    if (wizard.vibe === 'music'   && ev.category !== 'music') return false;
    if (wizard.vibe === 'outdoor' && ev.environment !== 'outdoor') return false;
    if (wizard.vibe === 'indoor'  && ev.environment !== 'indoor') return false;
    if (wizard.vibe === 'chill'   && ev.score >= 85) return false;
    if (wizard.vibe === 'food'    && ev.category !== 'food') return false;
  }
  return true;
}

function updateWizard() {
  const napBanner = document.getElementById('ruby-nap');
  napBanner.classList.toggle('hidden', wizard.who !== 'family');

  applyEventFilters();
  applyCalendarHighlight();
  applyEvergreenFilter();
  buildWizardPreview();

  const resultsBar = document.getElementById('wizard-results-bar');
  if (wizard.when || wizard.who || wizard.vibe) {
    const count = EVENTS.filter(ev => wizardEventFilter(ev) && new Date(ev.date) >= SITE_TODAY).length;
    const egCount = EVERGREEN.filter(eg => wizardEvergreenFilter(eg)).length;
    resultsBar.style.display = 'flex';
    document.getElementById('wizard-result-count').innerHTML =
      `${count} event${count !== 1 ? 's' : ''}, ${egCount} evergreen &nbsp;—&nbsp; <a href="#events" class="wiz-jump-link">See results ↓</a>`;
  } else {
    resultsBar.style.display = 'none';
  }
}

function wizardEvergreenFilter(eg) {
  if (!wizard.who && !wizard.vibe) return true;
  if (wizard.who) {
    const catMap = { solo: 'solo', dean: 'family', family: 'family',
                     date: 'date', friends: 'group', papa: 'papa' };
    const target = catMap[wizard.who];
    if (target && eg.category !== target) return false;
  }
  return true;
}

document.querySelectorAll('.wiz-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const step = btn.dataset.step, val = btn.dataset.val;
    if (wizard[step] === val) {
      wizard[step] = null; btn.classList.remove('active');
    } else {
      document.querySelectorAll(`.wiz-btn[data-step="${step}"]`).forEach(b => b.classList.remove('active'));
      btn.classList.add('active'); wizard[step] = val;
    }
    updateWizard();
  });
});

document.getElementById('wizard-reset').addEventListener('click', () => {
  wizard.when = wizard.who = wizard.vibe = null;
  document.querySelectorAll('.wiz-btn').forEach(b => b.classList.remove('active'));
  updateWizard();
});

// ─── SEARCH (inline grid filter state) ────────────────────────────────────
let searchQuery = '';

function initSearch() {
  const input = document.getElementById('search-input');
  if (!input) return;
  input.addEventListener('input', () => {
    searchQuery = input.value.trim().toLowerCase();
    applyEventFilters();
    applyEvergreenSearch();
  });
}

function evMatchesSearch(ev) {
  if (!searchQuery) return true;
  const hay = [ev.title, ev.subtitle, ev.venue, ev.note, ...(ev.genres||[]), ...(ev.lineup||[])].filter(Boolean).join(' ').toLowerCase();
  return hay.includes(searchQuery);
}

function egMatchesSearch(eg) {
  if (!searchQuery) return true;
  const hay = [eg.name, eg.description, eg.category, eg.notes].filter(Boolean).join(' ').toLowerCase();
  return hay.includes(searchQuery);
}

function applyEvergreenSearch() {
  document.querySelectorAll('.eg-card').forEach(card => {
    const egId = card.dataset.id;
    const eg   = EVERGREEN.find(e => e.id === egId);
    if (eg && !egMatchesSearch(eg)) card.classList.add('search-hidden');
    else card.classList.remove('search-hidden');
  });
}

// ─── EVENTS GRID ───────────────────────────────────────────────────────────
let activeFilter = 'all';
let activeTier   = 'all';
let activeSort   = 'date';
const renderedRadars = new Set();

const CAT_EMOJI = { music:'🎵', family:'👨‍👧', comedy:'😂', outdoor:'🌿', social:'🥁', date:'💑', group:'👥' };
const CAT_LABEL = { music:'Music', family:'Family', comedy:'Comedy', outdoor:'Outdoor', social:'Community', date:'Date', group:'Group' };

const AGE_EMOJI = { 'All ages':'👶 All ages', '21+':'🔞 21+', '18+':'🔞 18+' };

function scoreDots(n, max=5) {
  let out = '';
  for (let i = 1; i <= max; i++) out += `<span class="sdot${i <= n ? ' filled' : ''}"></span>`;
  return out;
}

function renderEventCard(ev, idx) {
  const delay    = Math.min(idx * 0.04, 0.30);
  const catEmoji = CAT_EMOJI[ev.category] || '📍';

  // Thumbnail: local image → YouTube → category emoji
  const thumbInner = ev.imageUrl
    ? `<img src="${ev.imageUrl}" alt="" loading="lazy">`
    : ev.youtubeId
    ? `<img src="https://img.youtube.com/vi/${ev.youtubeId}/mqdefault.jpg" alt="" loading="lazy" onerror="this.style.display='none'">`
    : catEmoji;

  // RSVP badge class
  const rsvpSignal = getRSVP(ev.id);
  const rsvpClass = rsvpSignal ? ` rsvp-${rsvpSignal}` : '';

  // Peek tags
  const urgTag  = ev.urgent ? `<span class="tag urgent">⚡ Act Now</span>` : '';
  const freeTag = ev.free   ? `<span class="tag free">💸 Free</span>` : '';
  const ageTag  = `<span class="tag">${AGE_EMOJI[ev.age] || ev.age}</span>`;
  const envTag  = ev.environment === 'outdoor'
    ? `<span class="tag outdoor">🌿 Outdoor</span>`
    : `<span class="tag indoor">🏠 Indoor</span>`;
  const genreTags = ev.genres.slice(0, 2).map(g => `<span class="tag">${g}</span>`).join('');
  const distTag = ev.distance === 'road-trip' ? `<span class="tag">🚗 Road Trip</span>` : '';
  const recTag  = ev.recurring ? `<span class="tag">↺ Recurring</span>` : '';

  const buyBtn = ev.ticketUrl
    ? `<a href="${ev.ticketUrl}" target="_blank" rel="noopener" class="btn-sm btn-buy" onclick="event.stopPropagation()">Buy Tickets →</a>`
    : '';

  const rsvpSection = INTERNAL
    ? `<div id="rsvp-${ev.id}" onclick="event.stopPropagation()">${rsvpButtonsHTML(ev.id)}</div>`
    : '';

  return `
    <div class="event-card tier-${ev.tier}${ev.urgent?' urgent-ev':''}${rsvpClass}"
         style="animation-delay:${delay}s"
         data-id="${ev.id}" data-category="${ev.category}"
         data-slots="${ev.slots.join(',')}" data-tier="${ev.tier}"
         data-free="${ev.free}" data-score="${ev.score}" data-date="${ev.date}">

      <div class="er-collapsed" onclick="togglePeek(${ev.id})">
        <div class="er-thumb cat-${ev.category}">${thumbInner}</div>
        <div class="er-main">
          <div class="er-title">${ev.title}${ev.subtitle ? `<span class="er-sub"> — ${ev.subtitle}</span>` : ''}</div>
          <div class="er-meta">${ev.dateStr}${ev.time ? ' · '+ev.time : ''} · 📍 ${ev.venue}${driveMinutes(ev) ? ` · 🚗 ~${driveMinutes(ev)} min` : ''}</div>
        </div>
        <div class="er-right">
          ${soonChip(ev)}
          ${ev.urgent ? `<span class="er-urgent-dot"></span>` : ''}
          ${topScoreAxis(ev)}
          <span class="er-score tier-${ev.tier}">${ev.score}</span>
          <span class="er-chevron">›</span>
        </div>
      </div>

      <div class="er-peek">
        <div class="er-peek-inner">
          <div class="ev-tags">${urgTag}${freeTag}${ageTag}${envTag}${genreTags}${distTag}${recTag}</div>
          <div class="er-note">${ev.note}</div>
          ${rsvpSection}
          <div class="er-actions">
            ${buyBtn}
            <button class="btn-sm btn-details" onclick="openDetails(${ev.id});event.stopPropagation()">Full Details →</button>
          </div>
        </div>
      </div>
    </div>`;
}

function renderGrid(events) {
  const grid = document.getElementById('events-grid');
  const showMoreBtn = document.getElementById('show-more-btn');
  if (!events.length) {
    grid.innerHTML = '<div class="no-results">No events match the current filters.</div>';
    if (showMoreBtn) showMoreBtn.style.display = 'none';
    return;
  }
  grid.innerHTML = events.map((ev, i) => renderEventCard(ev, i)).join('');
  if (showMoreBtn) showMoreBtn.style.display = 'none';
}

function applyEventFilters() {
  let filtered = EVENTS.filter(ev => {
    if (new Date(ev.date) < SITE_TODAY) return false;
    if (activeFilter === 'music'  && ev.category !== 'music') return false;
    if (activeFilter === 'family' && ev.category !== 'family') return false;
    if (activeFilter === 'comedy' && ev.category !== 'comedy') return false;
    if (activeFilter === 'group'  && !ev.slots.includes('GROUP_NIGHT')) return false;
    if (activeFilter === 'date'   && !ev.slots.includes('DATE_NIGHT')) return false;
    if (activeFilter === 'free'   && !ev.free) return false;
    if (activeTier !== 'all' && ev.tier !== activeTier) return false;
    if (!evMatchesSearch(ev)) return false;
    return true;
  });

  if (activeSort === 'score') filtered.sort((a, b) => b.score - a.score);
  else filtered.sort((a, b) => {
    const dc = a.date.localeCompare(b.date);
    if (dc !== 0) return dc;
    if (a.urgent && !b.urgent) return -1;
    if (!a.urgent && b.urgent) return 1;
    return b.score - a.score;
  });

  renderGrid(filtered);

  if (wizard.when || wizard.who || wizard.vibe) {
    document.querySelectorAll('.event-card[data-id]').forEach(card => {
      const id = parseInt(card.dataset.id);
      const ev = EVENTS.find(e => e.id === id);
      card.classList.toggle('wizard-dim', ev && !wizardEventFilter(ev));
    });
  }
  renderSurpriseStrip(filtered);
}

document.querySelectorAll('.chip[data-filter]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chip[data-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeFilter = btn.dataset.filter; applyEventFilters();
  });
});
document.querySelectorAll('.chip[data-tier]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.chip[data-tier]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeTier = btn.dataset.tier; applyEventFilters();
  });
});
document.getElementById('sort-date').addEventListener('click', () => {
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('sort-date').classList.add('active');
  activeSort = 'date'; applyEventFilters();
});
document.getElementById('sort-score').addEventListener('click', () => {
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('sort-score').classList.add('active');
  activeSort = 'score'; applyEventFilters();
});

// ─── CALENDAR + SHARE HELPERS ────────────────────────────────────────────
function parseEventTime(dateStr, timeStr) {
  const d = dateStr.replace(/-/g, '');
  if (!timeStr || /all day|afternoon|morning|noon/i.test(timeStr)) {
    return { start: d, allDay: true };
  }
  const m = timeStr.match(/(\d+)(?::(\d+))?\s*(AM|PM)/i);
  if (!m) return { start: d, allDay: true };
  let h = parseInt(m[1]);
  const min = m[2] ? parseInt(m[2]) : 0;
  if (/PM/i.test(m[3]) && h < 12) h += 12;
  if (/AM/i.test(m[3]) && h === 12) h = 0;
  const hh = String(h).padStart(2,'0'), mm = String(min).padStart(2,'0');
  const eh = Math.min(h + 2, 23);
  return { start: `${d}T${hh}${mm}00`, end: `${d}T${String(eh).padStart(2,'0')}${mm}00` };
}

function generateICS(evId) {
  const ev = EVENTS.find(e => e.id === evId);
  if (!ev) return;
  const { start, end, allDay } = parseEventTime(ev.date, ev.time);
  const dtStart = allDay ? `DTSTART;VALUE=DATE:${start}` : `DTSTART:${start}`;
  const dtEnd   = allDay ? `DTEND;VALUE=DATE:${end || start}` : `DTEND:${end}`;
  const loc = ev.address ? `${ev.venue}\\, ${ev.address}` : ev.venue;
  const desc = `Score: ${ev.score}${ev.ticketUrl ? '\\nTickets: ' + ev.ticketUrl : ''}`;
  const ics = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ATL Radar//EN',
    'BEGIN:VEVENT',
    dtStart, dtEnd,
    `SUMMARY:${ev.title}${ev.subtitle ? ' — ' + ev.subtitle : ''}`,
    `LOCATION:${loc}`,
    `DESCRIPTION:${desc}`,
    ev.ticketUrl ? `URL:${ev.ticketUrl}` : '',
    'END:VEVENT', 'END:VCALENDAR'
  ].filter(Boolean).join('\r\n');
  const blob = new Blob([ics], { type: 'text/calendar' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `${ev.title.replace(/[^a-zA-Z0-9]/g,'-')}.ics`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function generateGCalUrl(ev) {
  const { start, end, allDay } = parseEventTime(ev.date, ev.time);
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: ev.title + (ev.subtitle ? ' — ' + ev.subtitle : ''),
    dates: allDay ? `${start}/${start}` : `${start}/${end}`,
    location: ev.address ? `${ev.venue}, ${ev.address}` : ev.venue,
    details: ev.ticketUrl ? `Tickets: ${ev.ticketUrl}` : ev.note ? ev.note.slice(0,200) : ''
  });
  return `https://www.google.com/calendar/render?${params.toString()}`;
}

function copyEventShare(evId) {
  const ev = EVENTS.find(e => e.id === evId);
  if (!ev) return;
  const parts = [`${ev.title} — ${ev.dateStr} @ ${ev.venue}`];
  if (ev.ticketUrl) parts.push(ev.ticketUrl);
  navigator.clipboard.writeText(parts.join('\n'));
  const btn = document.querySelector(`.share-btn[data-id="${evId}"]`);
  if (btn) { btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Share', 1400); }
}

function topScoreAxis(ev) {
  if (!ev.scoreReasoning) return '';
  const axes = [
    ['Genre Match', ev.scoreReasoning.genreMatch],
    ['Venue', ev.scoreReasoning.venueQuality],
    ['Rare Format', ev.scoreReasoning.formatRarity],
    ['Lineup', ev.scoreReasoning.lineupStrength],
    ['Value', ev.scoreReasoning.valueForMoney]
  ].sort((a,b) => b[1] - a[1]);
  return axes[0][1] >= 90 ? `<span class="er-axis-star">★ ${axes[0][0]}</span>` : '';
}

function renderSurpriseStrip(filtered) {
  const strip = document.getElementById('surprise-strip');
  if (!strip) return;
  if (!wizard.when && !wizard.who && !wizard.vibe) { strip.style.display = 'none'; return; }
  const filteredIds = new Set(filtered.map(e => e.id));
  const surprises = EVENTS
    .filter(ev => new Date(ev.date) >= SITE_TODAY && !filteredIds.has(ev.id) && ev.score >= 70)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
  if (!surprises.length) { strip.style.display = 'none'; return; }
  strip.style.display = 'block';
  strip.innerHTML = `<div class="surprise-label">🎲 Outside your filter — you might like:</div>
    <div class="surprise-cards">${surprises.map(ev => `
      <div class="surprise-card" onclick="openBottomSheet(${ev.id})">
        <span class="surprise-title">${ev.title}</span>
        <span class="surprise-meta">${ev.dateStr}</span>
        <span class="er-score tier-${ev.tier}">${ev.score}</span>
      </div>`).join('')}
    </div>`;
}

// ─── MOBILE BOTTOM SHEET ──────────────────────────────────────────────────
const isMobile = () => window.matchMedia('(max-width: 768px)').matches;

function buildBottomSheetHTML(ev) {
  const catEmoji = CAT_EMOJI[ev.category] || '📍';
  const catLabel = CAT_LABEL[ev.category] || ev.category;

  const imgHtml = ev.imageUrl
    ? `<img class="bs-hero-img" src="${ev.imageUrl}" alt="${ev.title}">`
    : ev.youtubeId
    ? `<img class="bs-hero-img" src="https://img.youtube.com/vi/${ev.youtubeId}/maxresdefault.jpg" alt="${ev.title}" onerror="this.src='https://img.youtube.com/vi/${ev.youtubeId}/hqdefault.jpg'">`
    : '';

  const urgTag  = ev.urgent ? `<span class="tag urgent">⚡ Act Now</span>` : '';
  const freeTag = ev.free   ? `<span class="tag free">💸 Free</span>` : '';
  const ageTag  = `<span class="tag">${AGE_EMOJI[ev.age] || ev.age}</span>`;
  const envTag  = ev.environment === 'outdoor'
    ? `<span class="tag outdoor">🌿 Outdoor</span>`
    : `<span class="tag indoor">🏠 Indoor</span>`;
  const genreTags = ev.genres.slice(0, 3).map(g => `<span class="tag">${g}</span>`).join('');

  const buyBtn = ev.ticketUrl
    ? `<a href="${ev.ticketUrl}" target="_blank" rel="noopener" class="btn-sm btn-buy" onclick="event.stopPropagation()">Buy Tickets →</a>`
    : '';

  const ytSection = ev.youtubeId ? `
    <div class="bs-section">
      <div class="drawer-section-label">Watch</div>
      <div class="yt-wrap" id="bs-yt-${ev.id}">
        <div class="yt-placeholder" onclick="loadBsYT(${ev.id},'${ev.youtubeId}')">
          <img class="yt-thumb-bg" src="https://img.youtube.com/vi/${ev.youtubeId}/hqdefault.jpg" alt="" loading="lazy">
          <div class="play-icon">▶</div>
        </div>
      </div>
    </div>` : '';

  const lineupSection = (ev.lineup && ev.lineup.length) ? `
    <div class="bs-section">
      <div class="drawer-section-label">Lineup</div>
      ${ev.lineup.map((a, i) => {
        const st = ev.setTimes ? ev.setTimes.split(' · ')[i] || '' : '';
        return `<div class="lineup-artist"><span>${a}</span>${st ? `<span class="set-time">${st}</span>` : ''}</div>`;
      }).join('')}
    </div>` : '';

  const radarSection = ev.scoreReasoning ? `
    <div class="bs-section radar-wrap">
      <div class="drawer-section-label">Score Breakdown</div>
      <div class="radar-canvas-wrap"><canvas id="bs-radar-${ev.id}" width="220" height="220"></canvas></div>
    </div>` : '';

  const linksSection = (ev.officialUrl || ev.instagramUrl) ? `
    <div class="bs-section drawer-links">
      ${ev.officialUrl ? `<a href="${ev.officialUrl}" target="_blank" rel="noopener" class="drawer-link">🎟 Tickets / Info</a>` : ''}
      ${ev.instagramUrl ? `<a href="${ev.instagramUrl}" target="_blank" rel="noopener" class="drawer-link">📷 Instagram</a>` : ''}
    </div>` : '';

  const rsvpSection = INTERNAL ? `
    <div class="bs-section">
      <div class="drawer-section-label">Going?</div>
      <div id="bs-rsvp-${ev.id}">${rsvpButtonsHTML(ev.id)}</div>
    </div>` : '';

  // Track D / Rec 4: who to invite + copy-paste draft (internal only)
  const inviteSlot = INTERNAL ? inviteSlotFor(ev) : null;
  const inviteSection = inviteSlot ? `
    <div class="bs-section invite-panel">
      <div class="drawer-section-label">Invite</div>
      <div class="invite-group">${FRIEND_SLOTS[inviteSlot].label} — ${FRIEND_SLOTS[inviteSlot].names.join(', ')}</div>
      <div class="invite-draft">${generateDraftText(ev, inviteSlot).split('\n')[0]}</div>
      <button class="btn-sm invite-copy-btn" data-id="${ev.id}" onclick="copyInviteText(${ev.id});event.stopPropagation()">Copy Text</button>
    </div>` : '';

  const gcalUrl = generateGCalUrl(ev);
  const calSection = `
    <div class="bs-section bs-cal-section">
      <div class="drawer-section-label">Add to Calendar</div>
      <div class="bs-cal-btns">
        <a href="${gcalUrl}" target="_blank" rel="noopener" class="btn-sm btn-cal">Google Cal</a>
        <button class="btn-sm btn-cal" onclick="generateICS(${ev.id})">Download .ics</button>
      </div>
    </div>`;

  return `
    ${imgHtml ? `<div class="bs-hero">${imgHtml}</div>` : ''}
    <div class="bs-header">
      <div class="bs-cat-row">
        <span class="ev-cat-badge cat-${ev.category}">${catEmoji} ${catLabel}</span>
        <span class="bs-date-pill">${ev.dateStr}${ev.time ? ' · '+ev.time : ''}</span>
      </div>
      <div class="bs-title">${ev.title}</div>
      ${ev.subtitle ? `<div class="bs-subtitle">${ev.subtitle}</div>` : ''}
      <div class="bs-venue">📍 ${ev.venue}</div>
      <div class="ev-tags" style="margin-top:8px">${urgTag}${freeTag}${ageTag}${envTag}${genreTags}</div>
    </div>
    <div class="bs-actions">
      ${buyBtn}
      <button class="share-btn" data-id="${ev.id}" onclick="copyEventShare(${ev.id})">Share</button>
    </div>
    <div class="bs-body">
      <div class="bs-section"><div class="drawer-note">${ev.note}</div></div>
      ${rsvpSection}
      ${inviteSection}
      ${calSection}
      ${ytSection}
      ${lineupSection}
      ${radarSection}
      ${linksSection}
      ${ev.recurringNote ? `<div class="bs-section recurring-note">↺ ${ev.recurringNote}</div>` : ''}
    </div>`;
}

function loadBsYT(evId, ytId) {
  const wrap = document.getElementById(`bs-yt-${evId}`);
  if (!wrap) return;
  wrap.innerHTML = `<iframe src="https://www.youtube.com/embed/${ytId}?autoplay=1&rel=0&modestbranding=1"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen loading="lazy"></iframe>`;
}

let bsCurrentId = null;

function openBottomSheet(id) {
  const ev = EVENTS.find(e => e.id === id);
  if (!ev) return;
  bsCurrentId = id;
  const overlay = document.getElementById('bs-overlay');
  const content = document.getElementById('bs-content');
  content.innerHTML = buildBottomSheetHTML(ev);
  content.scrollTop = 0;
  document.body.style.overflow = 'hidden';
  requestAnimationFrame(() => {
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
  });
  if (ev.scoreReasoning) {
    requestAnimationFrame(() => {
      const canvas = document.getElementById(`bs-radar-${ev.id}`);
      if (canvas) {
        new Chart(canvas, {
          type: 'radar',
          data: {
            labels: ['Genre\nMatch', 'Venue\nQuality', 'Format\nRarity', 'Lineup\nStrength', 'Value\nfor Money'],
            datasets: [{
              data: [ev.scoreReasoning.genreMatch, ev.scoreReasoning.venueQuality, ev.scoreReasoning.formatRarity, ev.scoreReasoning.lineupStrength, ev.scoreReasoning.valueForMoney],
              backgroundColor: ev.tier==='S' ? 'rgba(245,158,11,0.18)' : ev.tier==='A' ? 'rgba(139,92,246,0.18)' : 'rgba(20,184,166,0.15)',
              borderColor: ev.tier==='S' ? '#F59E0B' : ev.tier==='A' ? '#8B5CF6' : '#14B8A6',
              borderWidth: 1.5,
              pointBackgroundColor: ev.tier==='S' ? '#F59E0B' : ev.tier==='A' ? '#8B5CF6' : '#14B8A6',
              pointRadius: 3,
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: {display:false}, tooltip: {callbacks:{label: c => ` ${c.raw}`}} },
            scales: { r: {
              min:0, max:100, beginAtZero:true,
              ticks: {display:false, stepSize:25},
              pointLabels: {color:'#94A3B8', font:{size:9}},
              grid: {color:'rgba(255,255,255,0.06)'},
              angleLines: {color:'rgba(255,255,255,0.06)'}
            }}
          }
        });
      }
    });
  }
}

function closeBottomSheet() {
  const overlay = document.getElementById('bs-overlay');
  if (!overlay.classList.contains('active')) return;
  overlay.classList.remove('active');
  overlay.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  bsCurrentId = null;
}

// Backdrop click
document.getElementById('bs-overlay')?.addEventListener('click', e => {
  if (e.target.id === 'bs-overlay') closeBottomSheet();
});

// ESC key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && bsCurrentId !== null) closeBottomSheet();
});

// Swipe-to-dismiss on handle
(function initBsSwipe() {
  const sheet = document.getElementById('bs-sheet');
  const handle = sheet?.querySelector('.bs-handle');
  if (!sheet || !handle) return;
  let startY = 0, currentY = 0, dragging = false;

  handle.addEventListener('touchstart', e => {
    startY = e.touches[0].clientY;
    currentY = startY;
    dragging = true;
    sheet.style.transition = 'none';
  }, { passive: true });

  sheet.addEventListener('touchmove', e => {
    if (!dragging) return;
    currentY = e.touches[0].clientY;
    const dy = Math.max(0, currentY - startY);
    sheet.style.transform = `translateY(${dy}px)`;
  }, { passive: true });

  sheet.addEventListener('touchend', () => {
    if (!dragging) return;
    dragging = false;
    sheet.style.transition = '';
    const dy = currentY - startY;
    if (dy > 100) {
      closeBottomSheet();
    }
    sheet.style.transform = '';
  });
})();

// ─── ROW PEEK + DETAIL ────────────────────────────────────────────────────
function togglePeek(id) {
  const card = document.querySelector(`.event-card[data-id="${id}"]`);
  if (!card) return;
  card.classList.toggle('peeked');
}

function openDetails(id) {
  openBottomSheet(id);
}

// kept for backward compat (jumpToEvent, calendar pill clicks)
function toggleDrawer(id) {
  togglePeek(id);
}

function loadYT(evId, ytId) {
  const wrap = document.getElementById(`yt-${evId}`);
  if (!wrap) return;
  wrap.innerHTML = `<iframe src="https://www.youtube.com/embed/${ytId}?autoplay=1&rel=0&modestbranding=1"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen loading="lazy"></iframe>`;
}

// Jump from calendar to event card
function jumpToEvent(evId) {
  // Ensure the event is visible in the grid (reset filters if needed)
  const evSection = document.getElementById('events');
  if (evSection) evSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  setTimeout(() => {
    let card = document.querySelector(`.event-card[data-id="${evId}"]`);
    if (!card) {
      // Card may be filtered out — reset filters
      activeFilter = 'all'; activeTier = 'all'; searchQuery = '';
      const si = document.getElementById('search-input');
      if (si) si.value = '';
      applyEventFilters();
      card = document.querySelector(`.event-card[data-id="${evId}"]`);
    }
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (!card.classList.contains('open')) toggleDrawer(evId);
      card.classList.add('highlight-flash');
      setTimeout(() => card.classList.remove('highlight-flash'), 1800);
    }
  }, 420);
}

// ─── RADAR CHART ───────────────────────────────────────────────────────────
function renderRadar(ev) {
  const canvas = document.getElementById(`radar-${ev.id}`);
  if (!canvas) return;
  const r = ev.scoreReasoning;
  new Chart(canvas, {
    type: 'radar',
    data: {
      labels: ['Genre\nMatch', 'Venue\nQuality', 'Format\nRarity', 'Lineup\nStrength', 'Value\nfor Money'],
      datasets: [{
        data: [r.genreMatch, r.venueQuality, r.formatRarity, r.lineupStrength, r.valueForMoney],
        backgroundColor: ev.tier==='S' ? 'rgba(245,158,11,0.18)' : ev.tier==='A' ? 'rgba(139,92,246,0.18)' : 'rgba(20,184,166,0.15)',
        borderColor: ev.tier==='S' ? '#F59E0B' : ev.tier==='A' ? '#8B5CF6' : '#14B8A6',
        borderWidth: 1.5,
        pointBackgroundColor: ev.tier==='S' ? '#F59E0B' : ev.tier==='A' ? '#8B5CF6' : '#14B8A6',
        pointRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: {display:false}, tooltip: {callbacks:{label: c => ` ${c.raw}`}} },
      scales: { r: {
        min:0, max:100, beginAtZero:true,
        ticks: {display:false, stepSize:25},
        pointLabels: {color:'#94A3B8', font:{size:9}},
        grid: {color:'rgba(255,255,255,0.06)'},
        angleLines: {color:'rgba(255,255,255,0.06)'}
      }}
    }
  });
}

// ─── CALENDAR — SINGLE MONTH WIDGET ─────────────────────────────────────
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DOW_LABELS  = ['Mo','Tu','We','Th','Fr','Sa','Su'];

let calYear  = SITE_TODAY.getFullYear();
let calMonth = SITE_TODAY.getMonth();

function buildCalendar() {
  const container = document.getElementById('cal-body');
  if (!container) return;

  // Update header label
  const lbl = document.getElementById('cal-month-label');
  if (lbl) lbl.textContent = `${MONTH_NAMES[calMonth]} ${calYear}`;

  // Group all events by ISO date string
  const evByDate = {};
  EVENTS.forEach(ev => {
    if (!evByDate[ev.date]) evByDate[ev.date] = [];
    evByDate[ev.date].push(ev);
  });

  const todayStr = SITE_TODAY.toISOString().slice(0, 10);
  const firstDay = new Date(calYear, calMonth, 1);
  const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
  let offset = firstDay.getDay() - 1;
  if (offset < 0) offset = 6;

  let html = `<div class="cal-dow-row">${DOW_LABELS.map(d => `<div class="cal-dow">${d}</div>`).join('')}</div><div class="cal-days-grid">`;

  for (let i = 0; i < offset; i++) html += `<div class="cal-cell cal-cell-empty"></div>`;

  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const isPast  = dateStr < todayStr;
    const isToday = dateStr === todayStr;
    const evs     = evByDate[dateStr] || [];
    const cls     = ['cal-cell', evs.length ? 'has-ev' : '', isToday ? 'is-today' : '', isPast ? 'is-past' : ''].filter(Boolean).join(' ');

    html += `<div class="${cls}">
      <span class="cal-cell-num">${day}</span>
      ${evs.map(ev => `<div class="cal-ev-pill tier-${ev.tier}" data-ev-id="${ev.id}" onclick="jumpToEvent(${ev.id})" title="${ev.title} — ${ev.venue}">${ev.title}</div>`).join('')}
    </div>`;
  }

  html += '</div>';
  container.innerHTML = html;
  applyCalendarHighlight();
}

function initCalendarNav() {
  const prevBtn = document.getElementById('cal-prev');
  const nextBtn = document.getElementById('cal-next');
  if (!prevBtn || !nextBtn) return;

  function updateCalNavState() {
    prevBtn.disabled = (calYear === 2026 && calMonth <= 3);
    nextBtn.disabled = (calYear === 2026 && calMonth >= 8);
    prevBtn.classList.toggle('cal-nav-disabled', prevBtn.disabled);
    nextBtn.classList.toggle('cal-nav-disabled', nextBtn.disabled);
  }

  prevBtn.addEventListener('click', () => {
    if (prevBtn.disabled) return;
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    buildCalendar();
    updateCalNavState();
  });
  nextBtn.addEventListener('click', () => {
    if (nextBtn.disabled) return;
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    buildCalendar();
    updateCalNavState();
  });
  updateCalNavState();
}

function applyCalendarHighlight() {
  const hasFilter = !!(wizard.when || wizard.who || wizard.vibe);
  document.querySelectorAll('.cal-ev-pill[data-ev-id]').forEach(pill => {
    const ev = EVENTS.find(e => e.id === parseInt(pill.dataset.evId));
    pill.classList.toggle('cal-pill-dim', hasFilter && ev && !wizardEventFilter(ev));
  });
}

// ─── LEAFLET MAP ───────────────────────────────────────────────────────────
let atlMap = null;
const mapMarkers = []; // {marker, layer:'events'|'evergreen', category:string}

function initMap() {
  atlMap = L.map('atl-map', { center:[33.775,-84.39], zoom:12, zoomControl:true, attributionControl:false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { subdomains:'abcd', maxZoom:19 }).addTo(atlMap);
  function makeIcon(color) {
    return L.divIcon({ className:'', html:`<div style="width:14px;height:14px;background:${color};border:2px solid rgba(255,255,255,0.6);border-radius:50%;box-shadow:0 0 8px ${color}55;"></div>`, iconSize:[14,14], iconAnchor:[7,7] });
  }
  const catColors = { music:'#F59E0B', family:'#22C55E', date:'#EC4899', group:'#8B5CF6', comedy:'#FBBF24', social:'#06B6D4', outdoor:'#14B8A6', free:'#60A5FA' };
  function evColor(ev) { return catColors[ev.category] || '#94A3B8'; }
  EVENTS.filter(ev => new Date(ev.date) >= SITE_TODAY && ev.lat).forEach(ev => {
    const m = L.marker([ev.lat,ev.lng],{icon:makeIcon(evColor(ev))}).addTo(atlMap);
    m.bindPopup(`<div class="popup-title">${ev.title}</div><div class="popup-sub">${ev.venue} · ${ev.dateStr}</div><span class="popup-tier ${ev.tier}">${ev.score}</span>${ev.ticketUrl?`<a href="${ev.ticketUrl}" target="_blank" class="popup-link">Get Tickets →</a>`:''}`);
    mapMarkers.push({marker:m, layer:'events', category:ev.category});
  });
  EVERGREEN.filter(eg => eg.lat).forEach(eg => {
    const m = L.marker([eg.lat,eg.lng],{icon:makeIcon('#10B981')}).addTo(atlMap);
    m.bindPopup(`<div class="popup-title">${eg.emoji} ${eg.name}</div><div class="popup-sub">${eg.description.slice(0,80)}…</div><span class="popup-tier EG">${eg.membershipIncluded?`Member · ${eg.membershipVenue}`:eg.free?'Free':eg.cost||''}</span>${eg.url?`<a href="${eg.url}" target="_blank" class="popup-link">Learn more →</a>`:''}`);
    mapMarkers.push({marker:m, layer:'evergreen', category:eg.category});
  });
  const legend = L.control({position:'bottomright'});
  legend.onAdd = () => {
    const div = L.DomUtil.create('div');
    div.innerHTML = `<div style="background:rgba(13,13,25,0.92);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px 14px;font-size:11px;color:#94A3B8;line-height:1.9"><div style="color:#E2E8F0;font-weight:700;margin-bottom:4px;font-size:10px;letter-spacing:.08em">EVENT TYPE</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#F59E0B;margin-right:6px"></span>🎵 Music</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#EC4899;margin-right:6px"></span>💑 Date Night</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#8B5CF6;margin-right:6px"></span>👥 Group</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#22C55E;margin-right:6px"></span>👨‍👧 Family</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#10B981;margin-right:6px"></span>🌿 Evergreen</div></div>`;
    return div;
  };
  legend.addTo(atlMap);

  // Filter controls
  document.querySelectorAll('.map-toggle').forEach(btn => {
    btn.addEventListener('click', () => { btn.classList.toggle('active'); applyMapFilters(); });
  });
  document.querySelectorAll('.map-cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.map-cat-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyMapFilters();
    });
  });
}

function applyMapFilters() {
  const showEvents = document.querySelector('.map-toggle[data-layer="events"]')?.classList.contains('active');
  const showEvergreen = document.querySelector('.map-toggle[data-layer="evergreen"]')?.classList.contains('active');
  const activeCat = document.querySelector('.map-cat-btn.active')?.dataset.cat || 'all';

  mapMarkers.forEach(({marker, layer, category}) => {
    const layerOk = (layer === 'events' && showEvents) || (layer === 'evergreen' && showEvergreen);
    const catOk = activeCat === 'all' || category === activeCat;
    if (layerOk && catOk) {
      if (!atlMap.hasLayer(marker)) atlMap.addLayer(marker);
    } else {
      if (atlMap.hasLayer(marker)) atlMap.removeLayer(marker);
    }
  });
}

// ─── EVERGREEN SECTION ─────────────────────────────────────────────────────
let activeEgCat   = 'all';
let activeEgTime  = 'any';
let activeEgDay   = 'any';
let activeEgAvail = 'all';
const openEgCards = new Set();

function buildEvergreenGrid() {
  const grid = document.getElementById('eg-grid');
  grid.innerHTML = EVERGREEN.map(eg => {
    const memTag  = eg.membershipIncluded ? `<span class="eg-tag member">🏅 Member · ${eg.membershipVenue}</span>` : '';
    const freeTag = eg.free && !eg.membershipIncluded ? `<span class="eg-tag free">💸 Free</span>` : '';
    const costTag = !eg.free && !eg.membershipIncluded && eg.cost ? `<span class="eg-tag">${eg.cost}</span>` : '';
    const effortTag = `<span class="eg-tag">${eg.effort === 'low' ? '🟢' : eg.effort === 'medium' ? '🟡' : '🔴'} ${eg.effort}</span>`;
    const distTag  = `<span class="eg-tag">📍 ${eg.distance}</span>`;
    const timeTag  = eg.timeOfDay !== 'anytime' ? `<span class="eg-tag">${eg.timeOfDay === 'morning' ? '🌅' : eg.timeOfDay === 'afternoon' ? '☀️' : '🌙'} ${eg.timeOfDay}</span>` : '';

    const hbDean   = scoreDots(eg.deanScore);
    const hbParent = scoreDots(eg.parentScore);

    const notesHtml = eg.notes ? `<div class="eg-notes">${eg.notes}</div>` : '';
    const urlHtml = eg.url ? `<a href="${eg.url}" target="_blank" rel="noopener" class="eg-link" onclick="event.stopPropagation()">Visit website →</a>` : '';
    const imgHtml = eg.imageUrl ? `<div class="eg-img"><img src="${eg.imageUrl}" alt="${eg.name}" loading="lazy"></div>` : '';

    const availIcon = eg.availability === 'seasonal' ? '🌸' : eg.availability === 'scheduled' ? '🗓' : null;
    const availTag = availIcon && eg.availabilityNote ? `<span class="eg-tag eg-avail-tag">${availIcon} ${eg.availabilityNote}</span>` : '';

    return `
      <div class="eg-card" data-id="${eg.id}" data-category="${eg.category}"
           data-effort="${eg.effort}" data-distance="${eg.distance}"
           data-timeofday="${eg.timeOfDay}" data-bestdays="${eg.bestDays||'any'}"
           data-availability="${eg.availability||'year-round'}"
           onclick="toggleEgCard('${eg.id}')">
        <div class="eg-card-top">
          <div class="eg-emoji">${eg.emoji}</div>
          <div class="eg-harvey-row">
            <span class="eg-hb-label">👦</span>${hbDean}
            <span class="eg-hb-label" style="margin-left:6px">🧑</span>${hbParent}
          </div>
        </div>
        <div class="eg-name">${eg.name}</div>
        <div class="eg-desc">${eg.description}</div>
        <div class="eg-meta">${availTag}${memTag}${freeTag}${costTag}${effortTag}${distTag}${timeTag}</div>
        <div class="eg-drawer">
          ${imgHtml}
          ${notesHtml}
          ${urlHtml}
          ${eg.address ? `<div class="eg-address">📍 ${eg.address}</div>` : ''}
        </div>
      </div>`;
  }).join('');
}

function toggleEgCard(id) {
  const card = document.querySelector(`.eg-card[data-id="${id}"]`);
  if (!card) return;
  const isOpen = card.classList.contains('open');
  card.classList.toggle('open', !isOpen);
}

function applyEvergreenFilter() {
  document.querySelectorAll('.eg-card').forEach(card => {
    const cat  = card.dataset.category;
    const tod  = card.dataset.timeofday;
    const days = card.dataset.bestdays;
    const egId = card.dataset.id;
    const eg   = EVERGREEN.find(e => e.id === egId);

    let show = (activeEgCat === 'all' || cat === activeEgCat);
    if (show && activeEgTime !== 'any') show = (tod === activeEgTime || tod === 'anytime');
    if (show && activeEgDay  !== 'any') show = (days === activeEgDay  || days === 'any');
    if (show && activeEgAvail !== 'all') show = (card.dataset.availability === activeEgAvail);
    if (show && eg && !egMatchesSearch(eg)) show = false;

    card.classList.toggle('hidden', !show);
  });

  if (wizard.who) {
    const catMap = { solo:'solo', dean:'family', family:'family', date:'date', friends:'group', papa:'papa' };
    const target = catMap[wizard.who];
    document.querySelectorAll('.eg-card:not(.hidden)').forEach(card => {
      card.style.opacity = (target && card.dataset.category !== target) ? '0.35' : '1';
    });
  } else {
    document.querySelectorAll('.eg-card').forEach(c => { c.style.opacity='1'; });
  }
}

document.querySelectorAll('.eg-chip').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.eg-chip').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeEgCat = btn.dataset.cat; applyEvergreenFilter();
  });
});
document.querySelectorAll('.eg-chip-time').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.eg-chip-time').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeEgTime = btn.dataset.time; applyEvergreenFilter();
  });
});
document.querySelectorAll('.eg-chip-day').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.eg-chip-day').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeEgDay = btn.dataset.day; applyEvergreenFilter();
  });
});
document.querySelectorAll('.eg-chip-avail').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.eg-chip-avail').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeEgAvail = btn.dataset.avail; applyEvergreenFilter();
  });
});

// ─── UNIVERSAL SEARCH MODAL (⌘K) ─────────────────────────────────────────────
function initSearchModal() {
  const overlay = document.getElementById('search-overlay');
  const input   = document.getElementById('search-modal-input');
  const results = document.getElementById('search-modal-results');
  const navBtn  = document.getElementById('nav-search-btn');
  let focusedIdx = -1;
  let allResults = [];

  function openModal() {
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(() => { input.focus(); }, 40);
    input.value = '';
    renderResults('');
  }
  function closeModal() {
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    focusedIdx = -1;
  }
  window.openSearchModal = openModal;

  function renderResults(query) {
    const q = query.trim().toLowerCase();
    if (!q) {
      results.innerHTML = '<div class="search-empty-hint">Start typing to search all events and activities</div>';
      allResults = []; return;
    }
    const evMatches = EVENTS.filter(ev => {
      const hay = [ev.title, ev.subtitle, ev.venue, ev.note, ...(ev.genres||[]), ...(ev.lineup||[])].filter(Boolean).join(' ').toLowerCase();
      return hay.includes(q) && new Date(ev.date) >= SITE_TODAY;
    }).slice(0, 6);
    const egMatches = EVERGREEN.filter(eg => {
      const hay = [eg.name, eg.description, eg.category, eg.notes].filter(Boolean).join(' ').toLowerCase();
      return hay.includes(q);
    }).slice(0, 5);
    allResults = [...evMatches.map(ev=>({type:'event',ev})), ...egMatches.map(eg=>({type:'eg',eg}))];
    if (!allResults.length) { results.innerHTML = '<div class="search-empty-hint">No results found</div>'; return; }

    function scoreBadgeStyle(score) {
      if (score >= 90) return 'rgba(245,158,11,0.22);color:var(--amber)';
      if (score >= 75) return 'rgba(139,92,246,0.22);color:var(--purple)';
      if (score >= 60) return 'rgba(20,184,166,0.15);color:var(--teal)';
      return 'rgba(75,85,99,0.15);color:var(--text-dim)';
    }
    let html = '';
    if (evMatches.length) {
      html += `<div class="search-section-label">Upcoming Events</div>`;
      evMatches.forEach((ev, i) => {
        const bg = scoreBadgeStyle(ev.score);
        const img = ev.imageUrl
          ? `<img class="search-result-img" src="${ev.imageUrl}" alt="" loading="lazy">`
          : ev.youtubeId
          ? `<img class="search-result-img" src="https://img.youtube.com/vi/${ev.youtubeId}/mqdefault.jpg" alt="" loading="lazy">`
          : `<div class="search-result-fallback cat-${ev.category}">${CAT_EMOJI[ev.category]||'📍'}</div>`;
        html += `<div class="search-result-item" data-idx="${i}" onclick="selectSearchResult(${i})">${img}<div class="search-result-info"><div class="search-result-title">${ev.title}</div><div class="search-result-sub">${ev.venue} · ${ev.dateStr}</div></div><span class="search-result-badge" style="background:${bg.split(';')[0]};${bg.split(';')[1]}">${ev.score}</span></div>`;
      });
    }
    if (egMatches.length) {
      html += `<div class="search-section-label">Evergreen Activities</div>`;
      egMatches.forEach((eg, i) => {
        const idx = evMatches.length + i;
        const badge = eg.free ? `<span class="search-result-badge" style="background:rgba(16,185,129,0.15);color:var(--green)">Free</span>` : eg.membershipIncluded ? `<span class="search-result-badge" style="background:rgba(245,158,11,0.15);color:var(--amber)">Member</span>` : '';
        html += `<div class="search-result-item" data-idx="${idx}" onclick="selectSearchResult(${idx})"><div class="search-result-fallback">${eg.emoji}</div><div class="search-result-info"><div class="search-result-title">${eg.name}</div><div class="search-result-sub">${eg.description.slice(0,60)}…</div></div>${badge}</div>`;
      });
    }
    results.innerHTML = html;
    focusedIdx = -1;
  }

  window.selectSearchResult = function(idx) {
    const r = allResults[idx]; if (!r) return;
    closeModal();
    if (r.type === 'event') {
      jumpToEvent(r.ev.id);
    } else {
      const egSection = document.getElementById('evergreen');
      if (egSection) egSection.scrollIntoView({behavior:'smooth',block:'start'});
      setTimeout(() => {
        let card = document.querySelector(`.eg-card[data-id="${r.eg.id}"]`);
        if (card && card.classList.contains('hidden')) {
          activeEgCat = 'all'; activeEgTime = 'any'; activeEgDay = 'any'; activeEgAvail = 'all';
          document.querySelectorAll('.eg-chip').forEach(b => b.classList.toggle('active', b.dataset.cat==='all'));
          document.querySelectorAll('.eg-chip-time').forEach(b => b.classList.toggle('active', b.dataset.time==='any'));
          document.querySelectorAll('.eg-chip-day').forEach(b => b.classList.toggle('active', b.dataset.day==='any'));
          document.querySelectorAll('.eg-chip-avail').forEach(b => b.classList.toggle('active', b.dataset.avail==='all'));
          applyEvergreenFilter();
          card = document.querySelector(`.eg-card[data-id="${r.eg.id}"]`);
        }
        if (card) {
          card.scrollIntoView({behavior:'smooth',block:'center'});
          if (!card.classList.contains('open')) toggleEgCard(r.eg.id);
          card.classList.add('highlight-flash');
          setTimeout(() => card.classList.remove('highlight-flash'), 1800);
        }
      }, 420);
    }
  };

  function moveFocus(dir) {
    const items = results.querySelectorAll('.search-result-item');
    if (!items.length) return;
    items[focusedIdx]?.classList.remove('focused');
    focusedIdx = Math.max(0, Math.min(items.length - 1, focusedIdx + dir));
    items[focusedIdx].classList.add('focused');
    items[focusedIdx].scrollIntoView({block:'nearest'});
  }

  input.addEventListener('input', () => renderResults(input.value));
  input.addEventListener('keydown', e => {
    if      (e.key === 'ArrowDown')                 { e.preventDefault(); moveFocus(1); }
    else if (e.key === 'ArrowUp')                   { e.preventDefault(); moveFocus(-1); }
    else if (e.key === 'Enter' && focusedIdx >= 0)  { selectSearchResult(focusedIdx); }
    else if (e.key === 'Escape')                    { closeModal(); }
  });
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  navBtn?.addEventListener('click', openModal);
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openModal(); }
    if (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) { e.preventDefault(); openModal(); }
  });
}

// ─── WIZARD PREVIEW STRIP ────────────────────────────────────────────────────
function buildWizardPreview() {
  const strip = document.getElementById('wizard-preview');
  if (!strip) return;
  const hasFilter = wizard.when || wizard.who || wizard.vibe;
  if (!hasFilter) { strip.style.display = 'none'; return; }

  const matched = EVENTS.filter(ev => new Date(ev.date) >= SITE_TODAY && wizardEventFilter(ev))
    .sort((a, b) => b.score - a.score).slice(0, 12);

  if (!matched.length) { strip.style.display = 'none'; return; }

  strip.style.display = 'flex';
  strip.innerHTML = matched.map(ev => {
    const imgContent = ev.imageUrl
      ? `<img class="wiz-mini-img" src="${ev.imageUrl}" alt="" loading="lazy">`
      : ev.youtubeId
      ? `<img class="wiz-mini-img" src="https://img.youtube.com/vi/${ev.youtubeId}/mqdefault.jpg" alt="" loading="lazy">`
      : `<div class="wiz-mini-img-fallback cat-${ev.category}">${CAT_EMOJI[ev.category]||'📍'}</div>`;
    return `<div class="wiz-mini-card" onclick="jumpToEvent(${ev.id})">
      <div class="wiz-mini-img-wrap">${imgContent}</div>
      <div class="wiz-mini-info">
        <div class="wiz-mini-title">${ev.title}</div>
        <div class="wiz-mini-meta">
          <span class="wiz-mini-tier tier-${ev.tier}">${ev.score}</span>
          <span class="wiz-mini-date">${ev.dateStr}</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

// ─── BACK TO TOP ────────────────────────────────────────────────────────────
const bttBtn = document.getElementById('back-to-top');
if (bttBtn) bttBtn.addEventListener('click', () => window.scrollTo({top:0,behavior:'smooth'}));

// ─── MAP FAB (mobile) ───────────────────────────────────────────────────────
const mapFab = document.getElementById('map-fab');
if (mapFab) {
  mapFab.addEventListener('click', () => {
    const mapSection = document.getElementById('map-section');
    if (mapSection) {
      mapSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      mapSection.classList.add('highlight-flash');
      setTimeout(() => mapSection.classList.remove('highlight-flash'), 1800);
    }
  });
}

// ─── SCROLL: PROGRESS + NAV + BACK-TO-TOP + MAP FAB ────────────────────────
window.addEventListener('scroll', () => {
  const pct = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
  document.getElementById('progress').style.width = pct + '%';
  if (bttBtn) bttBtn.classList.toggle('visible', window.scrollY > window.innerHeight * 0.5);
  if (mapFab) {
    const mapEl = document.getElementById('map-section');
    const mapVisible = mapEl && window.scrollY >= mapEl.offsetTop - window.innerHeight && window.scrollY <= mapEl.offsetTop + mapEl.offsetHeight;
    mapFab.classList.toggle('visible', window.scrollY > window.innerHeight * 0.3 && !mapVisible);
  }
  // Nav: compress links to emoji once hero is scrolled past
  document.getElementById('site-nav')?.classList.toggle('scrolled', window.scrollY > 80);
  const sections = ['wizard','events','map-section','evergreen','taste'];
  let current = '';
  for (const id of sections) {
    const el = document.getElementById(id);
    if (el && window.scrollY >= el.offsetTop - 120) current = id;
  }
  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#'+current);
  });
}, { passive: true });

// ─── HERO STATS ─────────────────────────────────────────────────────────────
function updateHeroStats() {
  const in3mo    = new Date(SITE_TODAY.getFullYear(), SITE_TODAY.getMonth() + 3, SITE_TODAY.getDate());
  const next3    = EVENTS.filter(ev => { const d = new Date(ev.date); return d >= SITE_TODAY && d <= in3mo; });
  const upcoming = EVENTS.filter(ev => new Date(ev.date) >= SITE_TODAY);

  // Event count + breakdown
  const adultOnly  = next3.filter(ev => ev.age === '21+').length;
  const familyFr   = next3.filter(ev => (ev.slots.includes('FAMILY_OUT')||ev.slots.includes('PAPA_DEAN')) && ev.age !== '21+').length;
  const allAges    = next3.length - adultOnly - familyFr;

  const elEv = document.getElementById('stat-ev-count');
  const elBr = document.getElementById('stat-ev-breakdown');
  if (elEv) elEv.textContent = next3.length;
  if (elBr) elBr.textContent = `${adultOnly} adults · ${familyFr} family · ${allAges} all-ages`;

  // Evergreen breakdown
  const egCats = {};
  EVERGREEN.forEach(eg => { egCats[eg.category] = (egCats[eg.category]||0)+1; });
  const catLabels = { family:'Family', solo:'Solo Reset', date:'Date Night', group:'Group', papa:'Papa+Dean' };
  const egBreak = Object.entries(egCats).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([k,v])=>`${catLabels[k]||k} ${v}`).join(' · ');
  const elEg  = document.getElementById('stat-eg-count');
  const elEgB = document.getElementById('stat-eg-breakdown');
  if (elEg)  elEg.textContent  = EVERGREEN.length;
  if (elEgB) elEgB.textContent = egBreak;

  // S+A tier
  const elSA = document.getElementById('stat-sa-count');
  if (elSA) elSA.textContent = upcoming.filter(e => e.score >= 75).length;

  // RSVP count (internal only)
  if (INTERNAL) {
    const rsvpIn = upcoming.filter(e => getRSVP(e.id) === 'in').length;
    const elRsvp = document.getElementById('stat-rsvp-count');
    const elRsvpSub = document.getElementById('stat-rsvp-sub');
    if (elRsvp) elRsvp.textContent = rsvpIn;
    if (elRsvpSub) {
      const maybe = upcoming.filter(e => getRSVP(e.id) === 'maybe').length;
      const attended = EVENTS.filter(e => getRSVP(e.id) === 'attended').length;
      const bits = [];
      if (maybe) bits.push(`${maybe} maybe`);
      if (attended) bits.push(`${attended} attended`);
      elRsvpSub.textContent = bits.length ? bits.join(' · ') : 'Mark events below';
    }
  }
}

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateHeroStats();
  applyEventFilters();
  buildCalendar();
  initCalendarNav();
  initSearch();

  buildEvergreenGrid();
  applyEvergreenFilter();
  initMap();
  initSearchModal();
  document.getElementById('wizard-results-bar').style.display = 'none';

  // Hero stat: "Top Picks" click → jump to events sorted by score
  const saCard = document.getElementById('stat-sa-count')?.closest('.stat-card');
  if (saCard) {
    saCard.style.cursor = 'pointer';
    saCard.title = 'Click to sort by score';
    saCard.addEventListener('click', () => {
      document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('sort-score').classList.add('active');
      activeSort = 'score';
      applyEventFilters();
      document.getElementById('events').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // Mobile wizard toggle
  const wizMobileToggle = document.getElementById('wizard-mobile-toggle');
  if (wizMobileToggle) {
    wizMobileToggle.addEventListener('click', () => {
      const wrap = document.querySelector('.wizard-wrap');
      const isOpen = wrap.classList.toggle('mobile-open');
      wizMobileToggle.classList.toggle('open', isOpen);
    });
  }

  // Sticky wizard results bar detection
  const wizBar = document.getElementById('wizard-results-bar');
  if (wizBar && 'IntersectionObserver' in window) {
    const sentinel = document.createElement('div');
    sentinel.style.height = '1px';
    wizBar.parentNode.insertBefore(sentinel, wizBar);
    new IntersectionObserver(([e]) => {
      wizBar.classList.toggle('stuck', !e.isIntersecting && wizBar.style.display !== 'none');
    }, { threshold: 0 }).observe(sentinel);
  }

});
