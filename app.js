/* ============================================================
   ATL Events V2 — app.js
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
  // Re-render buttons in drawer
  const container = document.getElementById(`rsvp-${id}`);
  if (container) container.innerHTML = rsvpButtonsHTML(id);
  // Update card badge
  const card = document.querySelector(`.event-card[data-id="${id}"]`);
  if (card) {
    const newSignal = getRSVP(id);
    card.classList.remove('rsvp-in', 'rsvp-maybe', 'rsvp-pass');
    if (newSignal) card.classList.add(`rsvp-${newSignal}`);
  }
  updateHeroStats();
}

function rsvpButtonsHTML(id) {
  const current = getRSVP(id);
  return `<div class="rsvp-row">
    <button class="rsvp-btn${current==='in'?' active':''}" onclick="setRSVP(${id},'in');event.stopPropagation()">I'm In</button>
    <button class="rsvp-btn${current==='maybe'?' active':''}" onclick="setRSVP(${id},'maybe');event.stopPropagation()">Maybe</button>
    <button class="rsvp-btn${current==='pass'?' active':''}" onclick="setRSVP(${id},'pass');event.stopPropagation()">Pass</button>
  </div>`;
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
  const catLabel = CAT_LABEL[ev.category] || ev.category;

  // Image strip: local image → YouTube thumbnail → styled poster fallback
  const imgHtml = ev.imageUrl
    ? `<div class="ev-img-wrap"><img class="ev-img" src="${ev.imageUrl}" alt="${ev.title}" loading="lazy" onerror="this.style.display='none';this.nextSibling.style.display='flex'"><div class="ev-img-fallback cat-${ev.category}" style="display:none">${catEmoji}</div></div>`
    : ev.youtubeId
    ? `<div class="ev-img-wrap"><img class="ev-img" src="https://img.youtube.com/vi/${ev.youtubeId}/maxresdefault.jpg" alt="${ev.title}" loading="lazy" onerror="this.src='https://img.youtube.com/vi/${ev.youtubeId}/hqdefault.jpg'"><div class="ev-img-fallback cat-${ev.category}" style="display:none">${catEmoji}</div></div>`
    : `<div class="ev-img-poster cat-${ev.category}"><div class="ev-poster-content"><div class="ev-poster-emoji">${catEmoji}</div><div class="ev-poster-title">${ev.title}</div><div class="ev-poster-venue">${ev.venue}</div></div></div>`;

  // RSVP badge class
  const rsvpSignal = getRSVP(ev.id);
  const rsvpClass = rsvpSignal ? ` rsvp-${rsvpSignal}` : '';

  // Tags with emojis
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
    ? `<a href="${ev.ticketUrl}" target="_blank" rel="noopener" class="btn-sm btn-buy${ev.tier==='S'?' amber-btn':''}" onclick="event.stopPropagation()">${ev.tier==='S'?'Buy S-Tier →':'Buy Tickets →'}</a>`
    : '';

  // Drawer sections
  const ytSection = ev.youtubeId ? `
    <div>
      <div class="drawer-section-label">Watch</div>
      <div class="yt-wrap" id="yt-${ev.id}">
        <div class="yt-placeholder" data-ytid="${ev.youtubeId}" onclick="loadYT(${ev.id},'${ev.youtubeId}')">
          <img class="yt-thumb-bg" src="https://img.youtube.com/vi/${ev.youtubeId}/hqdefault.jpg" alt="" loading="lazy">
          <div class="play-icon">▶</div>
        </div>
        <div class="yt-label">${ev.title}</div>
      </div>
    </div>` : '';

  const lineupSection = (ev.lineup && ev.lineup.length) ? `
    <div class="lineup-block">
      <div class="drawer-section-label">Lineup</div>
      ${ev.lineup.map((a, i) => {
        const st = ev.setTimes ? ev.setTimes.split(' · ')[i] || '' : '';
        return `<div class="lineup-artist"><span>${a}</span>${st ? `<span class="set-time">${st}</span>` : ''}</div>`;
      }).join('')}
    </div>` : '';

  const radarSection = ev.scoreReasoning ? `
    <div class="radar-wrap">
      <div class="drawer-section-label">Score Breakdown</div>
      <div class="radar-canvas-wrap"><canvas id="radar-${ev.id}" width="220" height="220"></canvas></div>
    </div>` : '';

  const linksSection = (ev.officialUrl || ev.instagramUrl) ? `
    <div class="drawer-links">
      ${ev.officialUrl ? `<a href="${ev.officialUrl}" target="_blank" rel="noopener" class="drawer-link" onclick="event.stopPropagation()">🎟 Tickets / Info</a>` : ''}
      ${ev.instagramUrl ? `<a href="${ev.instagramUrl}" target="_blank" rel="noopener" class="drawer-link" onclick="event.stopPropagation()">📷 Instagram</a>` : ''}
    </div>` : '';

  const noteInDrawer = `<div class="drawer-note">${ev.note}</div>`;

  const rsvpSection = INTERNAL ? `
    <div>
      <div class="drawer-section-label">Going?</div>
      <div id="rsvp-${ev.id}">${rsvpButtonsHTML(ev.id)}</div>
    </div>` : '';

  const shareText = `${ev.title} — ${ev.dateStr} @ ${ev.venue}`.replace(/'/g, "\\'");
  const shareBtn = `<button class="share-btn" onclick="navigator.clipboard.writeText('${shareText}');this.textContent='Copied!';setTimeout(()=>this.textContent='Share',1200);event.stopPropagation()">Share</button>`;

  return `
    <div class="event-card tier-${ev.tier}${ev.urgent?' urgent-ev':''}${rsvpClass}"
         style="animation-delay:${delay}s; cursor:pointer;"
         data-id="${ev.id}" data-category="${ev.category}"
         data-slots="${ev.slots.join(',')}" data-tier="${ev.tier}"
         data-free="${ev.free}" data-score="${ev.score}" data-date="${ev.date}"
         onclick="toggleDrawer(${ev.id})">

      ${imgHtml}

      <div class="ev-card-header">
        <div class="ev-top-row">
          <div class="ev-meta">
            <div class="ev-cat-date-row">
              <span class="ev-cat-badge cat-${ev.category}">${catEmoji} ${catLabel}</span>
              <span class="ev-date${ev.tier==='S'?' amber':''}">${ev.dateStr}${ev.time ? ' · '+ev.time : ''}</span>
            </div>
            <div class="ev-title">${ev.title}</div>
            ${ev.subtitle ? `<div class="ev-subtitle">${ev.subtitle}</div>` : ''}
            <div class="ev-venue">📍 ${ev.venue}</div>
          </div>
          <div class="tier-score-block">
            <div class="tier-badge ${ev.tier}">${ev.tier}</div>
            <div class="score-num-big">${ev.score}</div>
          </div>
        </div>
        <div class="ev-tags">${urgTag}${freeTag}${ageTag}${envTag}${genreTags}${distTag}${recTag}</div>
        <div class="ev-footer-row">
          <button class="expand-btn" aria-expanded="false" onclick="event.stopPropagation();toggleDrawer(${ev.id})">
            Details <span class="arrow">▾</span>
          </button>
          ${buyBtn}
        </div>
      </div>

      <div class="ev-drawer" id="drawer-${ev.id}">
        <div class="ev-drawer-inner">
          ${noteInDrawer}
          ${rsvpSection}
          ${ytSection}
          ${lineupSection}
          ${radarSection}
          ${linksSection}
          ${ev.recurringNote ? `<div class="recurring-note">↺ ${ev.recurringNote}</div>` : ''}
          <div class="drawer-footer">${shareBtn}</div>
        </div>
      </div>
    </div>`;
}

function renderGrid(events) {
  const grid = document.getElementById('events-grid');
  if (!events.length) {
    grid.innerHTML = '<div class="no-results">No events match the current filters.</div>';
    return;
  }
  grid.innerHTML = events.map((ev, i) => renderEventCard(ev, i)).join('');
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
  else filtered.sort((a, b) => a.date.localeCompare(b.date));

  renderGrid(filtered);

  if (wizard.when || wizard.who || wizard.vibe) {
    document.querySelectorAll('.event-card[data-id]').forEach(card => {
      const id = parseInt(card.dataset.id);
      const ev = EVENTS.find(e => e.id === id);
      card.classList.toggle('wizard-dim', ev && !wizardEventFilter(ev));
    });
  }
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

// ─── DRAWER TOGGLE ─────────────────────────────────────────────────────────
function toggleDrawer(id) {
  const card   = document.querySelector(`.event-card[data-id="${id}"]`);
  const drawer = document.getElementById(`drawer-${id}`);
  if (!card || !drawer) return;
  const isOpen = card.classList.contains('open');
  card.classList.toggle('open', !isOpen);
  const btn = card.querySelector('.expand-btn');
  if (btn) btn.setAttribute('aria-expanded', String(!isOpen));
  if (!isOpen && !renderedRadars.has(id)) {
    const ev = EVENTS.find(e => e.id === id);
    if (ev && ev.scoreReasoning) requestAnimationFrame(() => renderRadar(ev));
    renderedRadars.add(id);
  }
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
function initMap() {
  const map = L.map('atl-map', { center:[33.775,-84.39], zoom:12, zoomControl:true, attributionControl:false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { subdomains:'abcd', maxZoom:19 }).addTo(map);
  function makeIcon(color) {
    return L.divIcon({ className:'', html:`<div style="width:14px;height:14px;background:${color};border:2px solid rgba(255,255,255,0.6);border-radius:50%;box-shadow:0 0 8px ${color}55;"></div>`, iconSize:[14,14], iconAnchor:[7,7] });
  }
  const tc = { S:'#F59E0B', A:'#8B5CF6', B:'#14B8A6', C:'#4B5563' };
  EVENTS.filter(ev => new Date(ev.date) >= SITE_TODAY && ev.lat).forEach(ev => {
    const m = L.marker([ev.lat,ev.lng],{icon:makeIcon(tc[ev.tier]||'#8B5CF6')}).addTo(map);
    m.bindPopup(`<div class="popup-title">${ev.title}</div><div class="popup-sub">${ev.venue} · ${ev.dateStr}</div><span class="popup-tier ${ev.tier}">Tier ${ev.tier} · ${ev.score}</span>${ev.ticketUrl?`<a href="${ev.ticketUrl}" target="_blank" class="popup-link">Get Tickets →</a>`:''}`);
  });
  EVERGREEN.filter(eg => eg.lat).forEach(eg => {
    const m = L.marker([eg.lat,eg.lng],{icon:makeIcon('#10B981')}).addTo(map);
    m.bindPopup(`<div class="popup-title">${eg.emoji} ${eg.name}</div><div class="popup-sub">${eg.description.slice(0,80)}…</div><span class="popup-tier EG">${eg.membershipIncluded?`Member · ${eg.membershipVenue}`:eg.free?'Free':eg.cost||''}</span>${eg.url?`<a href="${eg.url}" target="_blank" class="popup-link">Learn more →</a>`:''}`);
  });
  const legend = L.control({position:'bottomright'});
  legend.onAdd = () => {
    const div = L.DomUtil.create('div');
    div.innerHTML = `<div style="background:rgba(13,13,25,0.92);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:10px 14px;font-size:11px;color:#94A3B8;line-height:1.9"><div style="color:#E2E8F0;font-weight:700;margin-bottom:4px;font-size:10px;letter-spacing:.08em">MAP LEGEND</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#F59E0B;margin-right:6px"></span>S-Tier</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#8B5CF6;margin-right:6px"></span>A-Tier</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#14B8A6;margin-right:6px"></span>B-Tier</div><div><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#10B981;margin-right:6px"></span>Evergreen</div></div>`;
    return div;
  };
  legend.addTo(map);
}

// ─── EVERGREEN SECTION ─────────────────────────────────────────────────────
let activeEgCat  = 'all';
let activeEgTime = 'any';
let activeEgDay  = 'any';
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

    return `
      <div class="eg-card" data-id="${eg.id}" data-category="${eg.category}"
           data-effort="${eg.effort}" data-distance="${eg.distance}"
           data-timeofday="${eg.timeOfDay}" data-bestdays="${eg.bestDays||'any'}"
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
        <div class="eg-meta">${memTag}${freeTag}${costTag}${effortTag}${distTag}${timeTag}</div>
        <div class="eg-expand-indicator">▾ More info</div>
        <div class="eg-drawer">
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
  const ind = card.querySelector('.eg-expand-indicator');
  if (ind) ind.textContent = isOpen ? '▾ More info' : '▴ Less';
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

    const tierBg = { S:'rgba(245,158,11,0.22);color:var(--amber)', A:'rgba(139,92,246,0.22);color:var(--purple)', B:'rgba(20,184,166,0.15);color:var(--teal)', C:'rgba(75,85,99,0.15);color:var(--text-dim)' };
    let html = '';
    if (evMatches.length) {
      html += `<div class="search-section-label">Upcoming Events</div>`;
      evMatches.forEach((ev, i) => {
        const bg = tierBg[ev.tier]||tierBg.C;
        const img = ev.imageUrl
          ? `<img class="search-result-img" src="${ev.imageUrl}" alt="" loading="lazy">`
          : ev.youtubeId
          ? `<img class="search-result-img" src="https://img.youtube.com/vi/${ev.youtubeId}/mqdefault.jpg" alt="" loading="lazy">`
          : `<div class="search-result-fallback cat-${ev.category}">${CAT_EMOJI[ev.category]||'📍'}</div>`;
        html += `<div class="search-result-item" data-idx="${i}" onclick="selectSearchResult(${i})">${img}<div class="search-result-info"><div class="search-result-title">${ev.title}</div><div class="search-result-sub">${ev.venue} · ${ev.dateStr}</div></div><span class="search-result-badge" style="background:${bg.split(';')[0]};${bg.split(';')[1]}">${ev.tier} ${ev.score}</span></div>`;
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
          activeEgCat = 'all'; activeEgTime = 'any'; activeEgDay = 'any';
          document.querySelectorAll('.eg-chip').forEach(b => b.classList.toggle('active', b.dataset.cat==='all'));
          document.querySelectorAll('.eg-chip-time').forEach(b => b.classList.toggle('active', b.dataset.time==='any'));
          document.querySelectorAll('.eg-chip-day').forEach(b => b.classList.toggle('active', b.dataset.day==='any'));
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
          <span class="wiz-mini-tier tier-${ev.tier}">${ev.tier}</span>
          <span class="wiz-mini-date">${ev.dateStr}</span>
        </div>
      </div>
    </div>`;
  }).join('');
}

// ─── BACK TO TOP ────────────────────────────────────────────────────────────
const bttBtn = document.getElementById('back-to-top');
if (bttBtn) bttBtn.addEventListener('click', () => window.scrollTo({top:0,behavior:'smooth'}));

// ─── SCROLL: PROGRESS + NAV + BACK-TO-TOP ──────────────────────────────────
window.addEventListener('scroll', () => {
  const pct = (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
  document.getElementById('progress').style.width = pct + '%';
  if (bttBtn) bttBtn.classList.toggle('visible', window.scrollY > window.innerHeight * 0.5);
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
  if (elSA) elSA.textContent = upcoming.filter(e => e.tier==='S'||e.tier==='A').length;

  // RSVP count (internal only)
  if (INTERNAL) {
    const rsvpIn = upcoming.filter(e => getRSVP(e.id) === 'in').length;
    const elRsvp = document.getElementById('stat-rsvp-count');
    const elRsvpSub = document.getElementById('stat-rsvp-sub');
    if (elRsvp) elRsvp.textContent = rsvpIn;
    if (elRsvpSub) {
      const maybe = upcoming.filter(e => getRSVP(e.id) === 'maybe').length;
      elRsvpSub.textContent = maybe ? `${maybe} maybe` : 'Mark events below';
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
});
