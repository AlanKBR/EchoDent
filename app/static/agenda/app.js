document.addEventListener('DOMContentLoaded', function () {
    // Mitigação adicional: alguns navegadores podem restaurar foco
    // no campo de busca global (header) ao entrar na página Agenda.
    // Garantimos blur explícito nos primeiros ~300ms pós-load.
    try {
        const headerSearch = document.querySelector('.global-search-input');
        if (headerSearch) {
            // Se já está focado logo no DOMContentLoaded, desfocar e limpar.
            if (document.activeElement === headerSearch) {
                headerSearch.blur();
                headerSearch.value = '';
            }
            // Segundo tick (restauração tardia ou bfcache):
            setTimeout(() => {
                if (document.activeElement === headerSearch) {
                    headerSearch.blur();
                    headerSearch.value = '';
                }
            }, 150);
            // Terceiro tick para navegadores mais lentos:
            setTimeout(() => {
                if (document.activeElement === headerSearch) {
                    headerSearch.blur();
                }
            }, 300);
        }
    } catch (e) { /* noop */ }
    // Helper to append a cache-busting version to static asset URLs
    function assetUrl(path) {
        try {
            const v = window.__ASSET_VERSION || window.ASSET_VERSION || document.documentElement.getAttribute('data-asset-version') || localStorage.getItem('ASSET_VERSION');
            const ver = v && String(v).trim() ? String(v).trim() : String(Date.now());
            const sep = path.includes('?') ? '&' : '?';
            return path + sep + 'v=' + encodeURIComponent(ver);
        } catch (e) {
            const sep = path.includes('?') ? '&' : '?';
            return path + sep + 'v=' + Date.now();
        }
    }
    // ===== UTC Conversion Helper (AGENTS.MD §9.1 Compliance) =====
    /**
     * Converte uma Date local (do navegador) para string ISO UTC.
     * Compatível com a expectativa do backend (AGENTS.MD §9.1).
     *
     * @param {Date|null} date - Data local do navegador
     * @param {boolean} allDay - Se true, retorna 'YYYY-MM-DD' (sem horário)
     * @returns {string|null} - String ISO UTC (ex: "2025-11-07T18:00:00Z") ou null
     */
    function toUTC(date, allDay = false) {
        if (!date) return null;
        if (allDay) {
            // Para eventos de dia inteiro, retornar apenas YYYY-MM-DD
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, '0');
            const d = String(date.getDate()).padStart(2, '0');
            return `${y}-${m}-${d}`;
        }
        // Para eventos com hora, usar toISOString() que retorna UTC com 'Z'
        return date.toISOString(); // Ex: "2025-11-07T18:00:00.000Z"
    }

    Promise.all([
        fetch(assetUrl('/static/agenda/event-popover.html')).then(res => res.text()),
        fetch(assetUrl('/static/agenda/event-contextmenu.html')).then(res => res.text()),
        fetch(assetUrl('/static/agenda/event-detail-popover.html')).then(res => res.text()),
        fetch(assetUrl('/static/agenda/settings-menu.html')).then(res => res.text()),
        fetch(assetUrl('/static/agenda/search-menu.html')).then(res => res.text())
    ]).then(([popoverHtml, contextHtml, detailPopoverHtml, settingsMenuHtml, searchMenuHtml]) => {
        const agendaHost = document.querySelector('.agenda-card') || document.body;
        document.getElementById('popover-container').innerHTML = popoverHtml + detailPopoverHtml;
        document.getElementById('contextmenu-container').innerHTML = contextHtml;
        document.getElementById('settingsmenu-container').innerHTML = settingsMenuHtml;
        // inserir menu de busca dentro do card da agenda
        let searchContainer = document.getElementById('searchmenu-container');
        if (!searchContainer) {
            searchContainer = document.createElement('div');
            searchContainer.id = 'searchmenu-container';
            agendaHost.appendChild(searchContainer);
        }
        searchContainer.innerHTML = searchMenuHtml;

        // Inicialização global dos pickers para garantir formato BR mesmo antes da seleção
        try {
            const s1 = document.getElementById('popoverEventStart');
            const e1 = document.getElementById('popoverEventEnd');
            const sD = document.getElementById('popoverEventStartDate');
            const eD = document.getElementById('popoverEventEndDate');
            if (window.flatpickr && s1 && e1 && sD && eD) {
                const ptLocale = (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) || null;
                const fpDateOpts = {
                    enableTime: false,
                    allowInput: true,
                    dateFormat: 'Y-m-d',
                    altInput: true,
                    altFormat: 'd/m/Y'
                };
                if (ptLocale) fpDateOpts.locale = ptLocale;
                const fpDateTimeOpts = {
                    enableTime: true,
                    time_24hr: true,
                    allowInput: true,
                    minuteIncrement: 5,
                    dateFormat: 'Y-m-d\\TH:i',
                    altInput: true,
                    altFormat: 'd/m/Y H:i'
                };
                if (ptLocale) fpDateTimeOpts.locale = ptLocale;
                // Pickers são destruídos/recriados quando o modo muda (allDay vs time)
                flatpickr(s1, fpDateTimeOpts);
                flatpickr(e1, fpDateTimeOpts);
                flatpickr(sD, fpDateOpts);
                flatpickr(eD, fpDateOpts);
            }
        } catch (e) {
            /* noop */
        }

        // Aplicar tema salvo (se houver)
        const savedTheme = localStorage.getItem('calendarTheme') || 'default';
        applyTheme(savedTheme, false);

        // Global build auto-registers plugins via script tags; no need to pass plugins array
    const calendarEl = document.getElementById('calendar');
        // Heurística de responsividade: níveis de compacidade em função da largura útil da coluna de horários
        // Retorna 'normal' | 'compact' | 'ultra'
        function __computeCompactLevel() {
            try {
                // 1) Tentar medir uma coluna da grade de horários (timeGrid)
                const col = calendarEl && calendarEl.querySelector('.fc-timegrid-col-frame, .fc-timegrid-col');
                const colW = col ? Math.round(col.getBoundingClientRect().width) : 0;
                // 2) Fallback: usar a largura do container do calendário
                const containerW = (agendaHost && agendaHost.clientWidth) || (calendarEl && calendarEl.clientWidth) || window.innerWidth || 0;
                // Thresholds empíricos (ajustados): <=105px: ultra (apenas hora); <=180px: compacto (título); caso contrário normal
                const basis = colW || containerW;
                if (basis <= 105) return 'ultra';
                if (basis <= 180) return 'compact';
                return 'normal';
            } catch (e) { return 'normal'; }
        }
        function loadCompactOverride() {
            try { return localStorage.getItem('calendarCompactOverride') || 'auto'; } catch (e) { return 'auto'; }
        }
        function __getCompactLevel() {
            // If a debug override is set, respect it
            const ov = loadCompactOverride();
            if (ov && ov !== 'auto') return ov;
            return (calendarEl && calendarEl.dataset && calendarEl.dataset.compactLevel) || 'normal';
        }
        function __applyCompactLevel(level) {
            try {
                if (!calendarEl) return;
                const prev = calendarEl.dataset.compactLevel || '';
                if (prev === level) return;
                calendarEl.dataset.compactLevel = level;
                calendarEl.classList.remove('is-compact', 'is-ultra');
                if (level === 'compact') calendarEl.classList.add('is-compact');
                if (level === 'ultra') calendarEl.classList.add('is-ultra');
            } catch (e) { /* noop */ }
        }
        // Utils: debounce and rAF-throttle
        function debounce(fn, wait = 200) {
            let t;
            return function (...args) {
                clearTimeout(t);
                t = setTimeout(() => fn.apply(this, args), wait);
            };
        }
        function rafThrottle(fn) {
            let scheduled = false;
            let lastArgs = null;
            return function (...args) {
                lastArgs = args;
                if (scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => {
                    scheduled = false;
                    fn.apply(this, lastArgs);
                });
            };
        }
    // Toast helper (Bootstrap 5)
        function showToast(message, variant = 'success', delay = 2500) {
            try {
                let cont = document.getElementById('toastContainer');
                if (!cont) {
                    cont = document.createElement('div');
                    cont.id = 'toastContainer';
                    cont.style.position = 'fixed';
                    cont.style.bottom = '16px';
                    cont.style.right = '16px';
                    cont.style.zIndex = '5000';
                    cont.style.display = 'flex';
                    cont.style.flexDirection = 'column';
                    cont.style.gap = '8px';
                    document.body.appendChild(cont);
                }
                const toastEl = document.createElement('div');
                toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
                toastEl.setAttribute('role', 'alert');
                toastEl.setAttribute('aria-live', 'assertive');
                toastEl.setAttribute('aria-atomic', 'true');
                toastEl.innerHTML = `
          <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>`;
                cont.appendChild(toastEl);
                if (window.bootstrap && window.bootstrap.Toast) {
                    const t = new bootstrap.Toast(toastEl, { delay, autohide: true });
                    t.show();
                    toastEl.addEventListener('hidden.bs.toast', () => { try { toastEl.remove(); } catch (e) { } });
                } else {
                    // Fallback: simple timed removal
                    toastEl.style.display = 'block';
                    setTimeout(() => { try { toastEl.remove(); } catch (e) { } }, delay);
                }
            } catch (e) { /* noop */ }
        }

        // Helper: attach a one-shot outside-click listener on the next frame
        function onNextFrameOutsideClick(containerEl, handler) {
            try {
                requestAnimationFrame(() => {
                    const listener = (e) => {
                        try {
                            if (!containerEl || !containerEl.contains || !containerEl.contains(e.target)) {
                                handler();
                            }
                        } catch (err) { /* noop */ }
                    };
                    document.addEventListener('mousedown', listener, { once: true });
                });
            } catch (e) { /* noop */ }
        }
        // Aviso quando nenhum dentista selecionado
        let emptyNoticeTimer = null;
    function updateEmptyFilterNotice() {
            try {
        const el = document.getElementById('filterNoticeSidebar') || document.getElementById('filterNotice');
                if (!el) return;
                const ids = loadSelectedDentists();
        const includeUn = loadIncludeUnassigned();
                // Mostrar aviso somente quando nada está marcado:
                // nem dentistas específicos nem "Todos (sem dentista)"
                const show = (!ids || ids.length === 0) && !includeUn;
                // clear any pending
                if (emptyNoticeTimer) { clearTimeout(emptyNoticeTimer); emptyNoticeTimer = null; }
                if (show) {
                    // small delay to avoid flashing before initial state settles
                    emptyNoticeTimer = setTimeout(() => {
                        try {
                            el.style.display = 'block';
                        } catch (e) { }
                    }, 350);
                } else {
                    el.style.display = 'none';
                }
            } catch (e) { }
        }
        const updateEmptyFilterNoticeDeb = debounce(updateEmptyFilterNotice, 200);

        // ===== Shared events cache (main + mini) =====
        const sharedEventsCache = {
            key: null,     // string key for filters: dentists|includeUn|q
            start: null,   // Date coverage start (inclusive)
            end: null,     // Date coverage end (exclusive)
            events: []     // array of event objects as returned by server
        };
        // In-flight de-duplication for events fetches: key -> Promise
        const pendingEventsFetches = new Map();
        function buildCacheKey() {
            const ids = loadSelectedDentists() || [];
            const includeUn = loadIncludeUnassigned() ? '1' : '';
            const q = loadSearchQuery() || '';
            return `${ids.sort((a, b) => a - b).join(',')}|${includeUn}|${q}`;
        }
        function ymdhmss(d) {
            // format YYYY-MM-DDTHH:MM:SS without timezone
            const pad = n => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        }
        function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
        function endOfDayExclusive(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); x.setDate(x.getDate() + 1); return x; }
        function unionRanges(a1, a2, b1, b2) {
            const s = a1 && b1 ? new Date(Math.min(a1.getTime(), b1.getTime())) : (a1 || b1);
            const e = a2 && b2 ? new Date(Math.max(a2.getTime(), b2.getTime())) : (a2 || b2);
            return { start: s, end: e };
        }
        function storeEventsToCache(list, covStart, covEnd, key) {
            const sameKey = sharedEventsCache.key === key;
            if (!sameKey || !sharedEventsCache.start || !sharedEventsCache.end) {
                sharedEventsCache.key = key;
                sharedEventsCache.start = covStart;
                sharedEventsCache.end = covEnd;
                sharedEventsCache.events = Array.isArray(list) ? list.slice() : [];
                return;
            }
            // merge events by id and expand coverage
            const byId = new Map(sharedEventsCache.events.map(e => [String(e.id), e]));
            (list || []).forEach(e => byId.set(String(e.id), e));
            sharedEventsCache.events = Array.from(byId.values());
            if (covStart && covStart < sharedEventsCache.start) sharedEventsCache.start = covStart;
            if (covEnd && covEnd > sharedEventsCache.end) sharedEventsCache.end = covEnd;
        }
        function cacheCoversRange(rangeStart, rangeEnd, key) {
            if (sharedEventsCache.key !== key) return false;
            if (!sharedEventsCache.start || !sharedEventsCache.end) return false;
            return sharedEventsCache.start <= rangeStart && sharedEventsCache.end >= rangeEnd;
        }
        function eventsFromCache(rangeStart, rangeEnd, key) {
            if (sharedEventsCache.key !== key) return [];
            const rs = rangeStart.getTime();
            const re = rangeEnd.getTime();
            return (sharedEventsCache.events || []).filter(ev => {
                try {
                    const s = ev.start ? new Date(ev.start.replace(' ', 'T')) : null;
                    const e = ev.end ? new Date(ev.end.replace(' ', 'T')) : null;
                    if (s && e) return e.getTime() >= rs && s.getTime() < re;
                    if (s && !e) return s.getTime() < re; // open-ended
                    return false;
                } catch (e) { return false; }
            });
        }
        // Mutate a cached event by id (keeps coverage and key); returns updated obj or null
        function updateEventInCacheById(id, changes) {
            try {
                const list = sharedEventsCache.events || [];
                const idx = list.findIndex(e => String(e.id) === String(id));
                if (idx === -1) return null;
                const old = list[idx] || {};
                const updated = { ...old, ...changes };
                // merge extended props if provided nested (not used now, but safe)
                if (old.extendedProps || changes?.extendedProps) {
                    updated.extendedProps = { ...(old.extendedProps || {}), ...(changes.extendedProps || {}) };
                }
                list[idx] = updated;
                sharedEventsCache.events = list;
                return updated;
            } catch (e) { return null; }
        }
        function removeEventFromCacheById(id) {
            try {
                if (!sharedEventsCache.events) return;
                sharedEventsCache.events = sharedEventsCache.events.filter(e => String(e.id) !== String(id));
            } catch (e) { /* noop */ }
        }
        function addEventToCache(ev) {
            try {
                if (!sharedEventsCache.events) sharedEventsCache.events = [];
                // avoid duplicates by id
                const id = ev && ev.id != null ? String(ev.id) : null;
                if (id) {
                    const exists = sharedEventsCache.events.some(e => String(e.id) === id);
                    if (exists) return;
                }
                sharedEventsCache.events.push(ev);
            } catch (e) { /* noop */ }
        }
        // Helper: detect a Brazilian phone number within free text (first match)
        function extractPhoneFromText(text) {
            if (!text) return null;
            try {
                // Supports formats like: +55 11 91234-5678, (11) 91234-5678, 112345-6789, 1234-5678, 9 1234-5678
                const re = /(?:\+?55[\s\-.]?)?(?:\(?\d{2}\)?[\s\-.]?)?(?:9\d{4}|\d{4})[\s\-.]?\d{4}\b/;
                const m = String(text).match(re);
                return m ? m[0].trim() : null;
            } catch (e) {
                return null;
            }
        }
        // Helper: format Date to local 'YYYY-MM-DDTHH:MM' string
        function formatLocalYmdHm(d) {
            const pad = (n) => String(n).padStart(2, '0');
            const y = d.getFullYear();
            const m = pad(d.getMonth() + 1);
            const day = pad(d.getDate());
            const h = pad(d.getHours());
            const min = pad(d.getMinutes());
            return `${y}-${m}-${day}T${h}:${min}`;
        }

        // Weekends setting (for week view)
        function getWeekendsSetting() {
            const v = localStorage.getItem('timeGridWeek_weekends');
            return v === null ? true : v === 'true';
        }

        function setWeekendsSetting(val) {
            try {
                localStorage.setItem('timeGridWeek_weekends', String(!!val));
            } catch (e) { }
        }

        // Client-side holiday cache
        let holidayDates = new Set(); // visible set 'YYYY-MM-DD'
        let holidayMeta = {}; // visible map date -> meta
        const dayCellEls = {}; // date -> [elements]
        // Session in-memory cache by year to avoid repeated GETs
        const holidaysYearCache = {}; // { [year]: { dates:Set, meta:{[date]:meta} } }
        const holidaysYearPending = {}; // { [year]: Promise }

        function toLocalISO(date) {
            const pad = (n) => String(n).padStart(2, '0');
            return [
                date.getFullYear(),
                pad(date.getMonth() + 1),
                pad(date.getDate())
            ].join('-');
        }

        function syncHolidayHighlight() {
            Object.keys(dayCellEls).forEach(d => {
                (dayCellEls[d] || []).forEach(el => {
                    if (!el || !el.classList) return;
                    if (holidayDates.has(d)) {
                        el.classList.add('fc-day-holiday');
                        const meta = holidayMeta[d];
                        if (meta && el.setAttribute) {
                            el.setAttribute('title', meta.name);
                        }
                    } else {
                        el.classList.remove('fc-day-holiday');
                        if (el.getAttribute && el.getAttribute('title')) {
                            el.removeAttribute('title');
                        }
                    }
                });
            });
        }

        function ymdFromDate(d) {
            const pad = n => String(n).padStart(2, '0');
            return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
        }

        function yearsInRangeInclusive(startDate, endDateInclusive) {
            const ys = [];
            const y1 = startDate.getFullYear();
            const y2 = endDateInclusive.getFullYear();
            for (let y = y1; y <= y2; y++) ys.push(y);
            return ys;
        }

        function ensureYearCached(year) {
            if (holidaysYearCache[year]) return Promise.resolve();
            if (holidaysYearPending[year]) return holidaysYearPending[year];
            const p = fetch(`/api/agenda/holidays/year?year=${year}`)
                .then(r => r.json())
                .then(list => {
                    const dates = new Set(list.map(h => h.date));
                    const meta = {};
                    list.forEach(h => {
                        meta[h.date] = {
                            name: h.name,
                            type: h.type,
                            level: h.level
                        };
                    });
                    holidaysYearCache[year] = {
                        dates,
                        meta
                    };
                })
                .catch(() => {
                    /* swallow; leave uncached to retry later */
                })
                .finally(() => {
                    delete holidaysYearPending[year];
                });
            holidaysYearPending[year] = p;
            return p;
        }

        function ensureRangeCached(startDate, endDateInclusive) {
            const years = yearsInRangeInclusive(startDate, endDateInclusive);
            return Promise.all(years.map(y => ensureYearCached(y)));
        }

        function buildVisibleFromCache(startDate, endDateInclusive) {
            const resDates = new Set();
            const resMeta = {};
            let d = new Date(startDate);
            while (d <= endDateInclusive) {
                const y = d.getFullYear();
                const yc = holidaysYearCache[y];
                const key = ymdFromDate(d);
                if (yc && yc.dates.has(key)) {
                    resDates.add(key);
                    if (yc.meta[key]) resMeta[key] = yc.meta[key];
                }
                d.setDate(d.getDate() + 1);
            }
            return {
                dates: resDates,
                meta: resMeta
            };
        }

        function updateHolidaysForCurrentView() {
            const view = calendar.view;
            if (!(view && view.currentStart && view.currentEnd)) return;
            const start = new Date(view.currentStart);
            const endInc = new Date(view.currentEnd);
            endInc.setDate(endInc.getDate() - 1); // end is exclusive
            return ensureRangeCached(start, endInc).then(() => {
                const built = buildVisibleFromCache(start, endInc);
                holidayDates = built.dates;
                holidayMeta = built.meta;
                syncHolidayHighlight();
            });
        }

        // Estado de filtro de dentistas (persistido no navegador)
        const storageKey = 'selectedDentists';
        const storageKeyUnassigned = 'includeUnassigned';

        function saveSelectedDentists(ids) {
            try {
                localStorage.setItem(storageKey, JSON.stringify(ids));
            } catch (e) { }
        }

        function loadSelectedDentists() {
            try {
                const v = localStorage.getItem(storageKey);
                if (!v) return [];
                const arr = JSON.parse(v);
                return Array.isArray(arr) ? arr : [];
            } catch (e) {
                return [];
            }
        }

        function saveIncludeUnassigned(val) {
            try {
                localStorage.setItem(storageKeyUnassigned, String(!!val));
            } catch (e) { }
        }

        function loadIncludeUnassigned() {
            try {
                return localStorage.getItem(storageKeyUnassigned) === 'true';
            } catch (e) {
                return false;
            }
        }

        function colorForDentist(d) {
            // fallback padrão se não houver cor: paleta baseada em id
            if (d && d.color) return d.color;
            const palette = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c', '#0891b2', '#4f46e5', '#059669'];
            const id = d && d.id ? Number(d.id) : 0;
            return palette[Math.abs(id) % palette.length];
        }
        // Renderizar lista lateral de dentistas
        const dentistsCache = {
            list: [],
            map: {}
        };

        // Client-side dentists loader with memoization + TTL cache in localStorage
        const DENTISTS_CACHE_KEY = 'dentistsCacheV1';
        const DENTISTS_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
        let dentistsPending = null; // Promise in-flight

        function loadDentistsFromStorage() {
            try {
                const raw = localStorage.getItem(DENTISTS_CACHE_KEY);
                if (!raw) return null;
                const obj = JSON.parse(raw);
                if (!obj || !Array.isArray(obj.list) || !obj.at) return null;
                if ((Date.now() - obj.at) > DENTISTS_CACHE_TTL_MS) return null;
                return obj.list;
            } catch (e) { return null; }
        }

        function saveDentistsToStorage(list) {
            try {
                localStorage.setItem(DENTISTS_CACHE_KEY, JSON.stringify({ list, at: Date.now() }));
            } catch (e) { }
        }

        // Force repaint of dentist color bars for all rendered instances of a given event id
        function repaintDentistBarsForEvent(eventId, pid) {
            try {
                const els = document.querySelectorAll(`[data-eid="${eventId}"]`);
                let col = null;
                if (pid != null && dentistsCache && dentistsCache.map && dentistsCache.map[pid]) {
                    const d = dentistsCache.map[pid];
                    col = colorForDentist(d);
                }
                els.forEach(el => {
                    // Ensure classes exist for styling consistency
                    if (col) {
                        el.classList.add('dentist-rightbar');
                        el.classList.add('dentist-leftbar');
                        el.style.borderRight = `6px solid ${col}`;
                        el.style.borderLeft = `2px solid ${col}`;
                        try { el.style.boxShadow = `inset -6px 0 0 0 ${col}`; } catch (e) { }
                    } else {
                        // No dentist: remove custom bars
                        el.style.borderRight = '';
                        el.style.borderLeft = '';
                        try { el.style.boxShadow = ''; } catch (e) { }
                        el.classList.remove('dentist-rightbar');
                        el.classList.remove('dentist-leftbar');
                    }
                });
            } catch (e) { }
        }

        function fetchDentistsOnce() {
            // If already in memory, resolve immediately
            if (dentistsCache.list && dentistsCache.list.length) {
                return Promise.resolve(dentistsCache.list);
            }
            // Try storage cache
            const fromStorage = loadDentistsFromStorage();
            if (fromStorage) {
                dentistsCache.list = fromStorage.map(d => ({ id: Number(d.id), nome: d.nome, color: d.color || null }));
                dentistsCache.map = Object.fromEntries(dentistsCache.list.map(d => [d.id, d]));
                return Promise.resolve(dentistsCache.list);
            }
            if (dentistsPending) return dentistsPending;
            dentistsPending = fetch('/api/agenda/dentists')
                .then(r => r.json())
                .then(list => {
                    const norm = Array.isArray(list) ? list.map(d => ({
                        id: Number(d.id),
                        nome: d.nome || String(d.id),
                        color: d.color || null
                    })) : [];
                    dentistsCache.list = norm;
                    dentistsCache.map = Object.fromEntries(norm.map(d => [d.id, d]));
                    saveDentistsToStorage(norm);
                    // If no saved selection, default to all dentists to avoid empty results on first load
                    try {
                        const saved = loadSelectedDentists();
                        if (!saved || saved.length === 0) {
                            saveSelectedDentists(norm.map(d => d.id));
                        }
                    } catch (e) { }
                    return norm;
                })
                .finally(() => { dentistsPending = null; });
            return dentistsPending;
        }

        function renderDentistsSidebar(list) {
            // Always render into in-card container; global sidebar widgets removed
            let cont = document.getElementById('dentistsContainer');
            if (!cont) return;
            // restore 'Todos (sem dentista)' checkbox in card
            try {
                const cbAll = document.getElementById('dent_all');
                if (cbAll) {
                    cbAll.checked = loadIncludeUnassigned();
                    cbAll.onchange = () => {
                        saveIncludeUnassigned(cbAll.checked);
                        try { calendar.refetchEvents(); } catch (e) { }
                        updateEmptyFilterNoticeDeb();
                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                        try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                    };
                }
            } catch (e) { }
            const selected = new Set(loadSelectedDentists());
            const ul = document.createElement('ul');
            ul.className = 'dentist-list';
            list.forEach(d => {
                const li = document.createElement('li');
                li.className = 'dentist-item d-flex align-items-center gap-2 py-1 border-bottom';
                const color = colorForDentist(d);
                li.innerHTML = `
                            <input type="checkbox" class="form-check-input" id="dent_${d.id}" ${selected.has(d.id) ? 'checked' : ''} />
                            <span class="dentist-color" style="background:${color}"></span>
                            <label class="form-check-label" for="dent_${d.id}">${d.nome || ('Dentista ' + d.id)}</label>
                        `;
                ul.appendChild(li);
            });
            ul.lastElementChild && ul.lastElementChild.classList.remove('border-bottom');
            cont.innerHTML = '';
            cont.appendChild(ul);
            cont.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', () => {
                    const ids = Array.from(cont.querySelectorAll('input[type="checkbox"]'))
                        .filter(x => x.checked)
                        .map(x => parseInt(x.id.replace('dent_', ''), 10))
                        .filter(n => Number.isFinite(n));
                    saveSelectedDentists(ids);
                    try { calendar.refetchEvents(); } catch (e) { }
                    updateEmptyFilterNotice();
                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                    try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                    try {
                        const sel = document.getElementById('popoverDentist');
                        if (sel) {
                            if (ids.length === 1) sel.value = String(ids[0]);
                            else if (ids.length === 0) sel.value = '';
                        }
                    } catch (e) { }
                });
            });
            // No mirroring into global sidebar; no need for observers here
            // No search/bulk controls by design
        }

        const calendar = new FullCalendar.Calendar(calendarEl, {
            themeSystem: 'bootstrap5',
            locale: 'pt-br',
            // Fit the calendar to its container which is sized by CSS to the viewport
            height: '100%',
            initialView: 'timeGridWeek',
            // Desabilitar renderização automática de horário (usamos eventContent customizado)
            displayEventTime: false,
            // Garantir 24h em toda a UI do FullCalendar
            eventTimeFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            },
            slotLabelFormat: {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            },
            // Não depender de ícones externos: sobrescrever botões com texto
            customButtons: {
                prev: {
                    text: '‹',
                    click: () => calendar.prev()
                },
                next: {
                    text: '›',
                    click: () => calendar.next()
                },
                prevYear: {
                    text: '≪',
                    click: () => {
                        const d = calendar.getDate();
                        calendar.gotoDate(new Date(
                            d.getFullYear(), d.getMonth() - 1, d.getDate()
                        ));
                    }
                },
                nextYear: {
                    text: '≫',
                    click: () => {
                        const d = calendar.getDate();
                        calendar.gotoDate(new Date(
                            d.getFullYear(), d.getMonth() + 1, d.getDate()
                        ));
                    }
                },
                settings: {
                    text: 'Configurações',
                    click: function () {
                        const btn = calendarEl.querySelector('.fc-settings-button');
                        if (!btn) return;
                        const wrap = document.getElementById('settingsmenu-container');
                        if (wrap && wrap.childElementCount === 0) {
                            fetch(assetUrl('/static/agenda/settings-menu.html'))
                                .then(r => r.text())
                                .then(html => { wrap.innerHTML = html; toggleSettingsMenu(btn); })
                                .catch(() => toggleSettingsMenu(btn));
                            return;
                        }
                        toggleSettingsMenu(btn);
                    }
                },
                search: {
                    text: 'Buscar',
                    click: function () {
                        const btn = calendarEl.querySelector('.fc-search-button');
                        if (!btn) return;
                        let wrap = document.getElementById('searchmenu-container');
                        if (!wrap) {
                            wrap = document.createElement('div');
                            wrap.id = 'searchmenu-container';
                            const agendaHost = document.querySelector('.agenda-card') || document.body;
                            agendaHost.appendChild(wrap);
                        }
                        if (wrap.childElementCount === 0) {
                            fetch(assetUrl('/static/agenda/search-menu.html'))
                                .then(r => r.text())
                                .then(html => { wrap.innerHTML = html; toggleSearchMenu(btn); })
                                .catch(() => toggleSearchMenu(btn));
                            return;
                        }
                        toggleSearchMenu(btn);
                    }
                }
            },
            headerToolbar: {
                left: 'prev,next today settings search',
                center: 'title',
                right: 'prevYear,nextYear dayGridMonth,timeGridWeek,timeGridDay,listWeek,multiMonthYear'
            },
            buttonText: {
                today: 'Hoje',
                month: 'Mês',
                week: 'Semana',
                day: 'Dia',
                list: 'Lista',
                listWeek: 'Lista',
                listMonth: 'Lista mês',
                listYear: 'Lista ano',
                dayGridMonth: 'Mês',
                timeGridWeek: 'Semana',
                timeGridDay: 'Dia',
                multiMonthYear: 'Ano'
            },
            moreLinkText: function (n) {
                return `+${n} mais`;
            },
            views: {
                dayGridMonth: {
                    eventDisplay: 'block'
                },
                multiMonthYear: {
                    type: 'multiMonth',
                    duration: {
                        years: 1
                    },
                    // boas colunas para layout 12 meses (3 col x 4 linhas)
                    multiMonthMaxColumns: 3,
                    eventDisplay: 'block',
                    buttonText: 'Ano'
                }
            },
            // plugins auto-registered by global build; omit explicit array
            dayCellClassNames: function (arg) {
                const iso = toLocalISO(arg.date);
                return holidayDates.has(iso) ? ['fc-day-holiday'] : [];
            },
            dayCellDidMount: function (arg) {
                const iso = toLocalISO(arg.date);
                if (!dayCellEls[iso]) dayCellEls[iso] = [];
                dayCellEls[iso].push(arg.el);
                // apply immediately if data already loaded
                if (holidayDates.has(iso)) {
                    arg.el.classList.add('fc-day-holiday');
                    const meta = holidayMeta[iso];
                    if (meta && arg.el && arg.el.setAttribute) {
                        arg.el.setAttribute('title', meta.name);
                    }
                }
            },
            selectable: true,
            editable: true,
            nowIndicator: true,
            navLinks: true,
            weekends: getWeekendsSetting(),
            eventContent: function (arg) {
                const level = __getCompactLevel();
                const compact = (level === 'compact' || level === 'ultra');
                function fmtHHMM(d) {
                    const hh = String(d.getHours()).padStart(2, '0');
                    const mm = String(d.getMinutes()).padStart(2, '0');
                    return `${hh}:${mm}`;
                }
                function buildTimeRange(ev) {
                    if (!ev || ev.allDay || !ev.start) return '';
                    const start = ev.start;
                    const startStr = fmtHHMM(start);
                    let endStr = '';
                    if (ev.end) {
                        endStr = fmtHHMM(ev.end);
                    }
                    // Em modo compacto, evitar intervalo para reduzir truncamento
                    if (compact) return startStr;
                    // Show range only when end exists; else just start
                    return endStr ? `${startStr} – ${endStr}` : startStr;
                }
                // Semana: estilo Google Calendar - nome em negrito, horário sem negrito, descrição com wrap
                if (arg.view.type === 'timeGridWeek') {
                    const isAllDay = arg.event.allDay;
                    const title = arg.event.title || '';

                    // Extrair todas as linhas de notes (para descrição com múltiplas linhas)
                    const notes = (arg.event.extendedProps && arg.event.extendedProps.notes) ? arg.event.extendedProps.notes : '';
                    const notesLines = notes.split('\n').filter(line => line.trim()).join('\n');

                    // calcular duração em minutos
                    let durationMin = 0;
                    if (!isAllDay && arg.event.start && arg.event.end) {
                        durationMin = Math.max(0, Math.round((arg.event.end.getTime() - arg.event.start.getTime()) / 60000));
                    } else if (!isAllDay && arg.event.start && !arg.event.end) {
                        durationMin = 60;
                    }

                    // Criar elementos DOM manualmente para sobrescrever completamente o conteúdo do FullCalendar
                    const container = document.createElement('div');
                    container.className = 'fc-event-main-custom';

                    // Eventos all-day: apenas título (e descrição se houver)
                    if (isAllDay) {
                        const titleEl = document.createElement('div');
                        titleEl.className = 'fc-event-title';
                        titleEl.textContent = title;
                        container.appendChild(titleEl);

                        if (notesLines) {
                            const descEl = document.createElement('div');
                            descEl.className = 'fc-event-description';
                            descEl.textContent = notesLines;
                            container.appendChild(descEl);
                        }
                    }
                    // Eventos muito curtos (≤30min): inline "Nome HH:MM" (sem vírgula!)
                    else if (durationMin <= 30) {
                        container.classList.add('short');

                        const titleEl = document.createElement('span');
                        titleEl.className = 'fc-event-title';
                        titleEl.textContent = title;
                        container.appendChild(titleEl);

                        const timeEl = document.createElement('span');
                        timeEl.className = 'fc-event-time';
                        const startTime = fmtHHMM(arg.event.start);
                        timeEl.textContent = `, ${startTime}`; // vírgula + espaço para separação visual
                        container.appendChild(timeEl);
                    }
                    // Eventos maiores (>30min): múltiplas linhas com range completo
                    else {
                        container.classList.add('multi-line');

                        const titleEl = document.createElement('div');
                        titleEl.className = 'fc-event-title';
                        titleEl.textContent = title;
                        container.appendChild(titleEl);

                        const timeEl = document.createElement('div');
                        timeEl.className = 'fc-event-time';
                        const startTime = fmtHHMM(arg.event.start);
                        const endTime = arg.event.end ? fmtHHMM(arg.event.end) : '';
                        timeEl.textContent = endTime ? `${startTime} – ${endTime}` : startTime;
                        container.appendChild(timeEl);

                        if (notesLines) {
                            const descEl = document.createElement('div');
                            descEl.className = 'fc-event-description';
                            descEl.textContent = notesLines;
                            container.appendChild(descEl);
                        }
                    }

                    return { domNodes: [container] };
                }
                // Dia: Nome (negrito) - descrição do evento (primeira linha de notes)
                if (arg.view.type === 'timeGridDay') {
                    const title = arg.event.title || '';
                    // Em ultra-compact, somente hora para eventos com hora
                    if (!arg.event.allDay && level === 'ultra') {
                        const t = buildTimeRange(arg.event);
                        const html = `<div class="fc-event-main-custom">${t || title}</div>`;
                        return { html };
                    }
                    const notes = (arg.event.extendedProps && arg.event.extendedProps.notes) ? arg.event.extendedProps.notes : '';
                    // Extrair primeira linha de notes (até \n ou até 60 caracteres)
                    let firstLineNotes = notes.split('\n')[0].trim();
                    if (firstLineNotes.length > 60) {
                        firstLineNotes = firstLineNotes.substring(0, 60) + '...';
                    }
                    // calcular duração em minutos (para escalar fonte)
                    let durationMin = 0;
                    if (!arg.event.allDay && arg.event.start) {
                        if (arg.event.end) {
                            durationMin = Math.max(0, Math.round((arg.event.end.getTime() - arg.event.start.getTime()) / 60000));
                        } else {
                            durationMin = 60; // padrão quando sem fim explícito
                        }
                    }
                    let sizeClass = '';
                    if (durationMin >= 120) sizeClass = ' size-large';
                    else if (durationMin >= 60) sizeClass = ' size-medium';
                    // Renderizar: sempre mostrar título, mostrar descrição se houver espaço (duração >= 45min)
                    let descriptionPart = '';
                    if (firstLineNotes && durationMin >= 45) {
                        descriptionPart = ` <span class="fc-event-notes" style="color: rgba(255,255,255,0.85); font-weight: 400;">- ${firstLineNotes}</span>`;
                    }
                    const html = `<div class="fc-event-main-custom${sizeClass}"><span class="fc-event-title" style="font-weight: 700;">${title}</span>${descriptionPart}</div>`;
                    return {
                        html
                    };
                }
                // Lista: Nome (negrito) - descrição (primeira linha de notes)
                if (arg.view.type && arg.view.type.startsWith('list')) {
                    const title = arg.event.title || '';
                    const notes = (arg.event.extendedProps && arg.event.extendedProps.notes) ? arg.event.extendedProps.notes : '';
                    // Extrair primeira linha
                    let firstLineNotes = notes.split('\n')[0].trim();
                    if (firstLineNotes.length > 80) {
                        firstLineNotes = firstLineNotes.substring(0, 80) + '...';
                    }
                    const sep = firstLineNotes ? ' - ' : '';
                    const html = `<span class="fc-event-title" style="font-weight: 700;">${title}</span>${sep}<span class="fc-event-notes" style="color: var(--color-text-secondary);">${firstLineNotes}</span>`;
                    return {
                        html
                    };
                }
                // Mês: título primeiro e horário (intervalo) em seguida numa única linha (mantém fundo colorido padrão)
                if (arg.view.type === 'dayGridMonth') {
                    const timeStr = buildTimeRange(arg.event);
                    const title = arg.event.title || '';
                    const timeInline = timeStr ? `<span class=\"fc-event-time-start\"> ${timeStr}</span>` : '';
                    const html = `<div class=\"fc-event-main-custom fc-month-line\"><span class=\"fc-event-title\">${title}</span>${timeInline}</div>`;
                    return {
                        html
                    };
                }
                // Visualização Anual (multiMonth): mesmo layout do mês
                if (arg.view.type && arg.view.type.startsWith('multiMonth')) {
                    const timeStr = buildTimeRange(arg.event);
                    const title = arg.event.title || '';
                    const timeInline = timeStr ? `<span class=\"fc-event-time-start\"> ${timeStr}</span>` : '';
                    const html = `<div class=\"fc-event-main-custom fc-month-line\"><span class=\"fc-event-title\">${title}</span>${timeInline}</div>`;
                    return {
                        html
                    };
                }
                // Outras visões: padrão
                return undefined;
            },
            events: function (fetchInfo, success, failure) {
                try {
                    const key = buildCacheKey();
                    // Always fetch a month (±7 days). If mini set an override, use its month; else use fetchInfo.start
                    const override = (typeof window !== 'undefined') ? window.__fetchMonthOverride : null;
                    const focus = (override && override.start) ? new Date(override.start) : new Date(fetchInfo.start);
                    const monthStart = new Date(focus.getFullYear(), focus.getMonth(), 1);
                    const monthEnd = (override && override.end)
                        ? new Date(override.end)
                        : new Date(focus.getFullYear(), focus.getMonth() + 1, 1);
                    const padStart = new Date(monthStart);
                    padStart.setDate(padStart.getDate() - 7);
                    const padEnd = new Date(monthEnd);
                    padEnd.setDate(padEnd.getDate() + 7);
                    const covStart = startOfDay(padStart);
                    const covEnd = startOfDay(padEnd);
                    const dedupKey = `${key}|${covStart.toISOString()}|${covEnd.toISOString()}`;
                    // If cache covers this padded month, just serve the requested subrange
                    if (cacheCoversRange(padStart, padEnd, key)) {
                        const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                        success(result);
                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                        try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                        return;
                    }
                    // If an identical fetch is in-flight, wait for it and then serve from cache
                    if (pendingEventsFetches.has(dedupKey)) {
                        pendingEventsFetches.get(dedupKey)
                            .then(() => {
                                const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                                success(result);
                                try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                            })
                            .catch(err => {
                                if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
                                else success([]);
                            });
                        return;
                    }
                    // Build query params for padded month
                    const ids = loadSelectedDentists();
                    const includeUn = loadIncludeUnassigned();
                    const q = loadSearchQuery();
                    const params = new URLSearchParams({
                        dentists: (ids && ids.length ? ids.join(',') : ''),
                        include_unassigned: includeUn ? '1' : '',
                        q: q || '',
                        start: ymdhmss(covStart),
                        end: ymdhmss(covEnd)
                    });
                    const p = fetch(`/api/agenda/events?${params.toString()}`)
                        .then(r => {
                            if (!r.ok) throw new Error(`HTTP ${r.status}`);
                            return r.json();
                        })
                        .then(list => {
                            storeEventsToCache(Array.isArray(list) ? list : [], covStart, covEnd, key);
                            const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
                            success(result);
                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                            try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
                        })
                        .catch(err => {
                            if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
                            else success([]);
                        })
                        .finally(() => { try { pendingEventsFetches.delete(dedupKey); } catch (e) { } });
                    pendingEventsFetches.set(dedupKey, p);
                } catch (e) {
                    if (typeof failure === 'function') failure(e instanceof Error ? e : new Error('Unexpected error'));
                    else success([]);
                }
            },
            select: function (info) {
                // Guard: if selection spans exactly a full day (00:00 -> 00:00 next day), treat as all-day
                function isFullDaySelection(i) {
                    try {
                        if (!i || !i.startStr || !i.endStr) return false;
                        const s = new Date(i.startStr);
                        const e = new Date(i.endStr);
                        const ms = e.getTime() - s.getTime();
                        const isStartMidnight = s.getHours() === 0 && s.getMinutes() === 0;
                        const isEndMidnight = e.getHours() === 0 && e.getMinutes() === 0;
                        return isStartMidnight && isEndMidnight && ms === 24 * 60 * 60 * 1000;
                    } catch (e) { return false; }
                }
                const selIsAllDay = info.allDay || isFullDaySelection(info);
                const popover = document.getElementById('eventPopover');
                popover.classList.remove('hidden');
                popover.classList.add('is-open');
                // garantir que fica acima do popover do dia/ano
                try {
                    popover.style.zIndex = '4000';
                } catch (e) { }
                let x = 0,
                    y = 0;
                if (info.jsEvent) {
                    x = info.jsEvent.clientX;
                    y = info.jsEvent.clientY;
                } else {
                    const rect = calendarEl.getBoundingClientRect();
                    x = rect.left + rect.width / 2;
                    y = rect.top + rect.height / 2;
                }
                requestAnimationFrame(() => {
                    const hostRect = agendaHost.getBoundingClientRect();
                    const popRect = popover.getBoundingClientRect();
                    let left = x - hostRect.left;
                    let top = y - hostRect.top;
                    const maxLeft = hostRect.width - popRect.width - 10;
                    const maxTop = hostRect.height - popRect.height - 10;
                    if (left > maxLeft) left = Math.max(10, maxLeft);
                    if (left < 10) left = 10;
                    if (top > maxTop) top = Math.max(10, maxTop);
                    if (top < 10) top = 10;
                    popover.style.position = 'absolute';
                    popover.style.left = left + 'px';
                    popover.style.top = top + 'px';
                });
                // Preencher campos do popover
                document.getElementById('popoverEventTitle').value = '';
                // Pré-selecionar dentista se exatamente um estiver marcado na sidebar
                try {
                    const sel = document.getElementById('popoverDentist');
                    if (sel) {
                        const ids = loadSelectedDentists();
                        if (ids && ids.length === 1) sel.value = String(ids[0]);
                        else sel.value = '';
                    }
                } catch (e) { }
                // Alterna inputs conforme allDay
                const startInput = document.getElementById('popoverEventStart');
                const endInput = document.getElementById('popoverEventEnd');
                const startDateInput = document.getElementById('popoverEventStartDate');
                const endDateInput = document.getElementById('popoverEventEndDate');
                if (selIsAllDay) {
                    startInput.classList.add('hidden');
                    endInput.classList.add('hidden');
                    startDateInput.classList.remove('hidden');
                    endDateInput.classList.remove('hidden');
                    // Acessibilidade: ajustar labels para o campo visível (date)
                    try {
                        const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]');
                        if (startLbl) startLbl.setAttribute('for', 'popoverEventStartDate');
                        const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]');
                        if (endLbl) endLbl.setAttribute('for', 'popoverEventEndDate');
                    } catch (e) { }
                    startDateInput.value = info.startStr;
                    if (info.endStr) {
                        const endDate = new Date(info.endStr);
                        endDate.setDate(endDate.getDate() - 1);
                        endDateInput.value = endDate.toISOString().slice(0, 10);
                    } else {
                        endDateInput.value = '';
                    }
                    // Se for dia inteiro, não usar datetime picker
                    try {
                        if (startInput._flatpickr) startInput._flatpickr.destroy();
                        if (endInput._flatpickr) endInput._flatpickr.destroy();
                    } catch (e) { }
                    // Aplicar flatpickr nos campos de data (dd/mm/yyyy)
                    const ptLocale2 = (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) || null;
                    const fpDateOpts = {
                        enableTime: false,
                        allowInput: true,
                        dateFormat: 'Y-m-d', // valor real do input
                        altInput: true,
                        altFormat: 'd/m/Y' // exibição para o usuário
                    };
                    if (ptLocale2) fpDateOpts.locale = ptLocale2;
                    if (window.flatpickr) {
                        flatpickr(startDateInput, fpDateOpts);
                        flatpickr(endDateInput, fpDateOpts);
                    }
                } else {
                    startInput.classList.remove('hidden');
                    endInput.classList.remove('hidden');
                    startDateInput.classList.add('hidden');
                    endDateInput.classList.add('hidden');
                    // Acessibilidade: ajustar labels para o campo visível (datetime)
                    try {
                        const startLbl = document.querySelector('#eventPopoverForm label[for="popoverEventStart"], #eventPopoverForm label[for="popoverEventStartDate"]');
                        if (startLbl) startLbl.setAttribute('for', 'popoverEventStart');
                        const endLbl = document.querySelector('#eventPopoverForm label[for="popoverEventEnd"], #eventPopoverForm label[for="popoverEventEndDate"]');
                        if (endLbl) endLbl.setAttribute('for', 'popoverEventEnd');
                    } catch (e) { }
                    startInput.value = info.startStr.slice(0, 16);
                    // Se a seleção não tiver fim, sugerir fim = início + duração padrão
                    (function () {
                        const saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                        const dur = isFinite(saved) && saved > 0 ? saved : 60;
                        try {
                            const startISO = info.startStr;
                            const startDate = new Date(startISO);
                            // valor sugerido pelo FullCalendar (geralmente 30min)
                            const selectionEndISO = info.endStr || '';
                            let useDefault = false;
                            if (selectionEndISO) {
                                const selEndDate = new Date(selectionEndISO);
                                const diffMin = Math.max(0, Math.round((selEndDate.getTime() - startDate.getTime()) / 60000));
                                // Se seleção for o slot padrão (30min) e default != 30, usar default
                                // Se usuário arrastou mais que o default, respeitar o arrasto
                                if (diffMin === 30 && dur !== 30) {
                                    useDefault = true;
                                } else if (diffMin === 0) {
                                    useDefault = true;
                                }
                            } else {
                                useDefault = true;
                            }
                            if (useDefault) {
                                const endDate = new Date(startDate);
                                endDate.setMinutes(endDate.getMinutes() + dur);
                                endInput.value = formatLocalYmdHm(endDate);
                            } else {
                                // selectionEndISO pode conter timezone; converter para local string HH:MM
                                const sel = new Date(selectionEndISO);
                                endInput.value = isNaN(sel.getTime()) ? selectionEndISO.slice(0, 16) : formatLocalYmdHm(sel);
                            }
                        } catch (e) {
                            endInput.value = '';
                        }
                    })();
                    // Inicializar/atualizar flatpickr 24h com valores ISO (mantém value no formato ISO; mostra formato BR ao usuário)
                    try {
                        if (startInput._flatpickr) startInput._flatpickr.destroy();
                        if (endInput._flatpickr) endInput._flatpickr.destroy();
                    } catch (e) { }
                    const ptLocale3 = (window.flatpickr && window.flatpickr.l10ns && window.flatpickr.l10ns.pt) || null;
                    const fpOpts = {
                        enableTime: true,
                        time_24hr: true,
                        allowInput: true,
                        minuteIncrement: 5,
                        dateFormat: "Y-m-d\\TH:i", // value real enviado
                        altInput: true,
                        altFormat: "d/m/Y H:i" // o que o usuário vê
                    };
                    if (ptLocale3) fpOpts.locale = ptLocale3;
                    if (window.flatpickr) {
                        flatpickr(startInput, fpOpts);
                        flatpickr(endInput, fpOpts);
                    }
                }
                document.getElementById('popoverEventDesc').value = '';
                setTimeout(() => {
                    document.getElementById('popoverEventTitle').focus();
                    // Configurar autocompletar
                    setupAutocomplete();
                }, 50);

                function closePopover() {
                    popover.classList.add('hidden');
                    popover.classList.remove('is-open');
                }
                onNextFrameOutsideClick(popover, closePopover);
                document.getElementById('closePopoverBtn').onclick = closePopover;
                const form = document.getElementById('eventPopoverForm');
                form.onsubmit = function (e) {
                    e.preventDefault();
                    const title = document.getElementById('popoverEventTitle').value;
                    let start, end;
                    if (selIsAllDay) {
                        // §9.1 Compliance: Eventos de dia inteiro já são YYYY-MM-DD (correto)
                        start = document.getElementById('popoverEventStartDate').value;
                        end = document.getElementById('popoverEventEndDate').value;
                        // UI mostra fim inclusivo; para o backend/FullCalendar precisamos enviar fim exclusivo
                        // Se usuário não preencher, usar start + 1 dia
                    } else {
                        // §9.1 Compliance: Converter datetime local para UTC
                        const startInput = document.getElementById('popoverEventStart').value;
                        const endInput = document.getElementById('popoverEventEnd').value;

                        start = toUTC(new Date(startInput), false);

                        if (endInput) {
                            end = toUTC(new Date(endInput), false);
                        } else if (startInput) {
                            // Aplicar duração padrão se end não fornecido
                            const saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                            const dur = isFinite(saved) && saved > 0 ? saved : 60;
                            const dt = new Date(startInput);
                            dt.setMinutes(dt.getMinutes() + dur);
                            end = toUTC(dt, false);
                        }
                    }
                    const selDent = (function () {
                        const el = document.getElementById('popoverDentist');
                        if (!el) return null;
                        const v = (el.value || '').trim();
                        return v && /^\d+$/.test(v) ? parseInt(v, 10) : null;
                    })();
                    if (title && start) {
                        // Preparar end a ser enviado respeitando regras de all-day (fim exclusivo)
                        let endToSend = end;
                        if (selIsAllDay) {
                            try {
                                const base = new Date(start + 'T00:00:00');
                                let endDate = end ? new Date(end + 'T00:00:00') : new Date(base);
                                endDate.setDate(endDate.getDate() + 1); // tornar exclusivo
                                endToSend = endDate.toISOString().slice(0, 10);
                            } catch (e) {
                                // fallback: se algo falhar, garantir pelo menos +1 dia
                                try {
                                    const d = new Date(start + 'T00:00:00');
                                    d.setDate(d.getDate() + 1);
                                    endToSend = d.toISOString().slice(0, 10);
                                } catch (e2) {
                                    endToSend = end || start;
                                }
                            }
                        }

                        // QOL 1: Loading state
                        const submitBtn = document.getElementById('eventPopoverForm')?.querySelector('button[type="submit"]');
                        if (submitBtn) {
                            submitBtn.disabled = true;
                            const originalText = submitBtn.innerHTML;
                            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando...';

                            fetch('/api/agenda/events', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    title: title,
                                    start: start,
                                    end: selIsAllDay ? endToSend : end,
                                    notes: document.getElementById('popoverEventDesc').value || '',
                                    dentista_id: selDent
                                })
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status === 'success' && data.event) {
                                        try {
                                            // Adiciona imediatamente no calendário e no cache compartilhado
                                            if (selIsAllDay) {
                                                const ev = { ...data.event, allDay: true };
                                                calendar.addEvent(ev);
                                                addEventToCache(ev);
                                            } else {
                                                calendar.addEvent(data.event);
                                                addEventToCache(data.event);
                                            }
                                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                            try { showToast('Evento criado.', 'success', 1600); } catch (e) { }
                                        } catch (e) {
                                            // Fallback: força recarregar eventos
                                            try { calendar.refetchEvents(); } catch (_) { }
                                        }
                                        closePopover();
                                    } else {
                                        alert('Erro ao adicionar evento!');
                                    }
                                })
                                .catch(() => {
                                    alert('Erro ao adicionar evento!');
                                })
                                .finally(() => {
                                    if (submitBtn) {
                                        submitBtn.disabled = false;
                                        submitBtn.innerHTML = originalText;
                                    }
                                });
                        }
                    }
                };
                calendar.unselect();
            },
            eventClick: function (info) {
                document.getElementById('eventContextMenu').style.display = 'none';
                const popover = document.getElementById('eventDetailPopover');
                // mover para o container do card para manter escopo e z-index previsível
                try {
                    const agendaHost = document.querySelector('.agenda-card') || document.body;
                    if (popover && popover.parentElement !== agendaHost) {
                        agendaHost.appendChild(popover);
                    }
                } catch (e) { }
                // Formatação correta do horário (pt-BR)
                const fmtDate = new Intl.DateTimeFormat('pt-BR', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
                const fmtTime = new Intl.DateTimeFormat('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                });

                function buildTimeText(ev) {
                    const start = ev.start;
                    const end = ev.end;
                    if (ev.allDay) {
                        if (!end) return `${fmtDate.format(start)} (dia inteiro)`;
                        const last = new Date(end.getTime() - 24 * 60 * 60 * 1000);
                        const same = start.getFullYear() === last.getFullYear() &&
                            start.getMonth() === last.getMonth() &&
                            start.getDate() === last.getDate();
                        return same ?
                            `${fmtDate.format(start)} (dia inteiro)` :
                            `${fmtDate.format(start)} – ${fmtDate.format(last)} (dia inteiro)`;
                    } else {
                        if (end) {
                            const sameDay = start.toDateString() === end.toDateString();
                            return sameDay ?
                                `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtTime.format(end)}` :
                                `${fmtDate.format(start)} ${fmtTime.format(start)} – ${fmtDate.format(end)} ${fmtTime.format(end)}`;
                        } else {
                            return `${fmtDate.format(start)} ${fmtTime.format(start)}`;
                        }
                    }
                }
                // Preencher apenas título e horário
                document.getElementById('detailEventTitle').textContent = info.event.title;
                document.getElementById('detailEventTime').textContent = buildTimeText(info.event);
                // Preencher notas (descrição)
                const notesArea = document.getElementById('detailEventNotes');
                const saveNotesBtn = document.getElementById('saveDetailNotesBtn');
                if (notesArea) {
                    notesArea.value = info.event.extendedProps && info.event.extendedProps.notes ? info.event.extendedProps.notes : '';
                }
                if (saveNotesBtn) {
                    saveNotesBtn.onclick = function () {
                        const newNotes = notesArea ? notesArea.value : '';
                        fetch(`/api/agenda/events/${info.event.id}`, {
                            method: 'PATCH',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                notes: newNotes
                            })
                        })
                            .then(r => r.json())
                            .then(data => {
                                if (data.status === 'success') {
                                    try { info.event.setExtendedProp('notes', newNotes); } catch (e) { }
                                    updateEventInCacheById(info.event.id, { notes: newNotes });
                                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                } else {
                                    alert('Erro ao salvar descrição.');
                                }
                            })
                            .catch(() => alert('Erro ao salvar descrição.'));
                    };
                }
                // Dentista: preencher opções e valor atual
                try {
                    const sel = document.getElementById('detailEventDentist');
                    const btn = document.getElementById('saveDetailDentistBtn');
                    if (sel) {
                        // Limpar e repopular mantendo 'Sem dentista'
                        const keep = sel.querySelector('option[value=""]');
                        sel.innerHTML = '';
                        if (keep) sel.appendChild(keep);
                        (dentistsCache.list || []).forEach(d => {
                            const opt = document.createElement('option');
                            opt.value = String(d.id);
                            opt.textContent = d.nome;
                            sel.appendChild(opt);
                        });
                        const pid = info.event.extendedProps && (info.event.extendedProps.dentista_id ?? info.event.extendedProps.profissional_id);
                        sel.value = (pid != null) ? String(pid) : '';
                    }
                    if (btn) {
                        btn.onclick = function () {
                            const v = (sel && sel.value || '').trim();
                            const pid = v && /^\d+$/.test(v) ? parseInt(v, 10) : null;
                            fetch(`/api/agenda/events/${info.event.id}`, {
                                method: 'PATCH',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    dentista_id: pid
                                })
                            })
                                .then(r => r.json())
                                .then(j => {
                                    if (j && j.status === 'success') {
                                        try { info.event.setExtendedProp('profissional_id', pid); } catch (e) { }
                                        updateEventInCacheById(info.event.id, { profissional_id: pid });
                                        // Re-render events to re-run eventDidMount and apply new dentist colors
                                        try { calendar.rerenderEvents(); } catch (e) { }
                                        // Also directly repaint current DOM nodes for immediate feedback
                                        try { repaintDentistBarsForEvent(info.event.id, pid); } catch (e) { }
                                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                    } else {
                                        alert('Erro ao salvar dentista.');
                                    }
                                })
                                .catch(() => alert('Erro ao salvar dentista.'));
                        };
                    }
                } catch (e) { }
                // Buscar telefone do paciente e habilitar clique para copiar
                const phoneSection = document.getElementById('detailEventPhoneSection');
                const phoneDiv = document.getElementById('detailEventPhone');
                const waLink = document.getElementById('detailEventWhatsApp');

                function normalizePhoneForWhatsApp(raw) {
                    if (!raw) return null;
                    const digits = String(raw).replace(/\D+/g, '');
                    if (!digits) return null;
                    // Se já tem DDI e parece E.164 brasileiro (55 + 11 dígitos para celular ou 10 para fixo)
                    if (digits.startsWith('55') && (digits.length === 12 || digits.length === 13)) {
                        return digits;
                    }
                    // Se parece internacional (mais que 11 dígitos e não começa com 55), manter
                    if (!digits.startsWith('55') && digits.length > 11) {
                        return digits;
                    }
                    const DEFAULT_DDI = '55';
                    const DEFAULT_DDD = '33'; // conforme solicitado
                    if (digits.length === 11) {
                        // DDD + celular (9 dígitos)
                        return DEFAULT_DDI + digits;
                    }
                    if (digits.length === 10) {
                        // DDD + fixo
                        return DEFAULT_DDI + digits;
                    }
                    if (digits.length === 9 || digits.length === 8) {
                        // sem DDD, usar padrão
                        return DEFAULT_DDI + DEFAULT_DDD + digits;
                    }
                    // fallback: se muito curto, retornar null
                    return null;
                }

                function applyWhatsAppLink(num) {
                    if (!waLink) return;
                    const normalized = normalizePhoneForWhatsApp(num);
                    if (normalized) {
                        waLink.href = `https://wa.me/${normalized}`;
                        waLink.classList.remove('visually-hidden');
                    } else {
                        waLink.classList.add('visually-hidden');
                    }
                }
                if (phoneSection && phoneDiv) {
                    phoneSection.classList.add('hidden');
                    phoneDiv.textContent = '';
                    fetch(`/api/agenda/buscar_telefone?nome=${encodeURIComponent(info.event.title)}`)
                        .then(response => response.json())
                        .then(data => {
                            const tel = (data && data.telefone) ? String(data.telefone).trim() : '';
                            const fromNotes = (!tel && info.event.extendedProps) ?
                                extractPhoneFromText(info.event.extendedProps.notes) :
                                null;
                            const finalTel = tel || (fromNotes || '');
                            if (finalTel) {
                                phoneDiv.textContent = finalTel;
                                phoneDiv.classList.remove('copied');
                                phoneSection.classList.remove('hidden');
                                applyWhatsAppLink(finalTel);
                                phoneDiv.onclick = async () => {
                                    try {
                                        await navigator.clipboard.writeText(finalTel);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    } catch (e) {
                                        const ta = document.createElement('textarea');
                                        ta.value = finalTel;
                                        (document.querySelector('.agenda-card') || document.body).appendChild(ta);
                                        ta.select();
                                        document.execCommand('copy');
                                        document.body.removeChild(ta);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    }
                                };
                            }
                        })
                        .catch(() => {
                            // Fallback silencioso: tentar extrair do texto das notas
                            const notes = (info.event.extendedProps && info.event.extendedProps.notes) ? String(info.event.extendedProps.notes) : '';
                            const extracted = extractPhoneFromText(notes);
                            if (extracted) {
                                phoneDiv.textContent = extracted;
                                phoneDiv.classList.remove('copied');
                                phoneSection.classList.remove('hidden');
                                applyWhatsAppLink(extracted);
                                phoneDiv.onclick = async () => {
                                    try {
                                        await navigator.clipboard.writeText(extracted);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    } catch (e) {
                                        const ta = document.createElement('textarea');
                                        ta.value = extracted;
                                        (document.querySelector('.agenda-card') || document.body).appendChild(ta);
                                        ta.select();
                                        document.execCommand('copy');
                                        document.body.removeChild(ta);
                                        phoneDiv.classList.add('copied');
                                        setTimeout(() => phoneDiv.classList.remove('copied'), 1200);
                                    }
                                };
                            }
                        });
                }

                // Exibir popover próximo ao clique
                let x = 0,
                    y = 0;
                if (info.jsEvent) {
                    x = info.jsEvent.clientX;
                    y = info.jsEvent.clientY;
                } else {
                    const rect = calendarEl.getBoundingClientRect();
                    x = rect.left + rect.width / 2;
                    y = rect.top + rect.height / 2;
                }
                popover.classList.remove('hidden');
                popover.classList.add('is-open');
                try {
                    popover.style.zIndex = '10000';
                } catch (e) { }
                requestAnimationFrame(() => {
                    const hostRect = agendaHost.getBoundingClientRect();
                    const popRect = popover.getBoundingClientRect();
                    let left = x - hostRect.left;
                    let top = y - hostRect.top;
                    const maxLeft = hostRect.width - popRect.width - 10;
                    const maxTop = hostRect.height - popRect.height - 10;
                    if (left > maxLeft) left = Math.max(10, maxLeft);
                    if (left < 10) left = 10;
                    if (top > maxTop) top = Math.max(10, maxTop);
                    if (top < 10) top = 10;
                    popover.style.position = 'absolute';
                    popover.style.left = left + 'px';
                    popover.style.top = top + 'px';
                });
                // Fechar ao clicar fora ou no botão
                function closePopover() {
                    popover.classList.add('hidden');
                    popover.classList.remove('is-open');
                }
                onNextFrameOutsideClick(popover, closePopover);
                document.getElementById('closeDetailPopoverBtn').onclick = closePopover;
            },
            eventDidMount: function (info) {
                // QOL 2: Tooltips enriquecidos (§QOL)
                try {
                    const title = info.event.title || '';
                    const notes = (info.event.extendedProps && info.event.extendedProps.notes) || '';
                    const start = info.event.start;
                    const end = info.event.end;

                    // Formatar data/hora para pt-BR
                    const fmtDate = new Intl.DateTimeFormat('pt-BR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: info.event.allDay ? undefined : '2-digit',
                        minute: info.event.allDay ? undefined : '2-digit',
                        hour12: false
                    });

                    const startStr = start ? fmtDate.format(start) : '';
                    const endStr = end ? fmtDate.format(end) : '';

                    // Montar tooltip rico
                    let tooltipText = title;
                    if (startStr) {
                        tooltipText += `\n${startStr}`;
                        if (endStr && endStr !== startStr) {
                            tooltipText += ` - ${endStr}`;
                        }
                    }
                    if (notes) {
                        tooltipText += `\n${notes}`;
                    }

                    info.el.setAttribute('title', tooltipText);
                } catch (e) { /* noop */ }

                // marcar elemento com id para filtros de busca
                try {
                    if (info && info.el && info.event && info.event.id != null) {
                        info.el.setAttribute('data-eid', String(info.event.id));
                    }
                } catch (e) { }
                info.el.addEventListener('contextmenu', function (e) {
                    e.preventDefault();
                    const menu = document.getElementById('eventContextMenu');
                    let x = e.clientX,
                        y = e.clientY;
                    menu.classList.remove('hidden');
                    menu.classList.add('is-open');
                    requestAnimationFrame(() => {
                        const hostRect = agendaHost.getBoundingClientRect();
                        const menuRect = menu.getBoundingClientRect();
                        let left = x - hostRect.left;
                        let top = y - hostRect.top;
                        const maxLeft = hostRect.width - menuRect.width - 10;
                        const maxTop = hostRect.height - menuRect.height - 10;
                        if (left > maxLeft) left = Math.max(10, maxLeft);
                        if (left < 10) left = 10;
                        if (top > maxTop) top = Math.max(10, maxTop);
                        if (top < 10) top = 10;
                        menu.style.left = left + 'px';
                        menu.style.top = top + 'px';
                    });

                    function closeMenu() {
                        menu.classList.add('hidden');
                        menu.classList.remove('is-open');
                    }
                    onNextFrameOutsideClick(menu, closeMenu);
                    // Duplicação rápida (+1 semana, +2 semanas, +1 mês)
                    const ORANGE = '#f59e42';

                    function pad(n) {
                        return String(n).padStart(2, '0');
                    }

                    function fmtDate(d) {
                        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
                    }

                    function fmtDateTime(d) {
                        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
                    }

                    function addDays(d, n) {
                        const nd = new Date(d);
                        nd.setDate(nd.getDate() + n);
                        return nd;
                    }

                    function addMonths(d, n) {
                        const nd = new Date(d);
                        nd.setMonth(nd.getMonth() + n);
                        return nd;
                    }

                    function duplicateWith(offset) {
                        try {
                            const ev = info.event;
                            const isAllDay = !!ev.allDay;
                            const start = new Date(ev.start);
                            const end = ev.end ? new Date(ev.end) : (isAllDay ? addDays(start, 1) : addDays(start, 1));
                            const pid = ev.extendedProps && (ev.extendedProps.dentista_id ?? ev.extendedProps.profissional_id) != null ? Number(ev.extendedProps.dentista_id ?? ev.extendedProps.profissional_id) : null;
                            let newStart, newEnd;
                            if (offset.type === 'd') {
                                newStart = addDays(start, offset.value);
                                newEnd = addDays(end, offset.value);
                            } else if (offset.type === 'm') {
                                newStart = addMonths(start, offset.value);
                                newEnd = addMonths(end, offset.value);
                            }
                            const body = {
                                title: ev.title || '',
                                start: isAllDay ? fmtDate(newStart) : fmtDateTime(newStart),
                                end: isAllDay ? fmtDate(newEnd) : fmtDateTime(newEnd),
                                notes: '',
                                color: ORANGE,
                                profissional_id: pid
                            };
                            fetch('/api/agenda/events', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(body)
                            })
                                .then(r => r.json()).then(j => {
                                    if (j && j.status === 'success' && j.event) {
                                        try {
                                            calendar.addEvent(j.event);
                                            addEventToCache(j.event);
                                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                            closeMenu();
                                        } catch (e) {
                                            calendar.refetchEvents();
                                        }
                                    } else {
                                        alert('Erro ao duplicar evento.');
                                    }
                                }).catch(() => alert('Erro ao duplicar evento.'));
                        } catch (e) {
                            /* noop */
                        }
                    }
                    const dup1w = document.getElementById('dup1wBtn');
                    const dup2w = document.getElementById('dup2wBtn');
                    const dup3w = document.getElementById('dup3wBtn');
                    const dup4w = document.getElementById('dup4wBtn');
                    const dup1m = document.getElementById('dup1mBtn');
                    if (dup1w) dup1w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 7
                    });
                    if (dup2w) dup2w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 14
                    });
                    if (dup3w) dup3w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 21
                    });
                    if (dup4w) dup4w.onclick = () => duplicateWith({
                        type: 'd',
                        value: 28
                    });
                    if (dup1m) dup1m.onclick = () => duplicateWith({
                        type: 'm',
                        value: 1
                    });

                    document.getElementById('deleteEventBtn').onclick = function () {
                        fetch(`/api/agenda/events/${info.event.id}`, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: undefined
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.status === 'success') {
                                    try { info.event.remove(); } catch (e) { }
                                    removeEventFromCacheById(info.event.id);
                                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                    closeMenu();
                                } else {
                                    alert('Erro ao deletar evento!');
                                }
                            });
                    };
                    document.querySelectorAll('#colorOptions .color-circle').forEach(function (circle) {
                        circle.onclick = function () {
                            const color = this.getAttribute('data-color');
                            fetch(`/api/agenda/events/${info.event.id}`, {
                                method: 'PATCH',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    color: color
                                })
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status === 'success') {
                                        try {
                                            info.event.setProp('backgroundColor', color);
                                            info.event.setProp('borderColor', color);
                                        } catch (e) { }
                                        updateEventInCacheById(info.event.id, { color });
                                        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                                        closeMenu();
                                    } else {
                                        alert('Erro ao atualizar cor!');
                                    }
                                });
                        };
                    });
                });

                // Aplicar borda direita espessa + esquerda fina por dentista
                try {
                    const pid = info.event.extendedProps && (info.event.extendedProps.dentista_id ?? info.event.extendedProps.profissional_id);
                    if (pid != null && dentistsCache && dentistsCache.map && dentistsCache.map[pid]) {
                        const d = dentistsCache.map[pid];
                        const col = colorForDentist(d);
                        info.el.classList.add('dentist-rightbar');
                        info.el.style.borderRight = `6px solid ${col}`;
                        info.el.classList.add('dentist-leftbar');
                        info.el.style.borderLeft = `2px solid ${col}`;
                        // Reforço visual em views baseadas em tabela (list) e em elementos sem borda visível
                        try {
                            info.el.style.boxShadow = `inset -6px 0 0 0 ${col}`;
                        } catch (e) { }
                    }
                } catch (e) { }

                // Enriquecer eventos no popover "+ mais" (multiMonth/dayGrid): título, horário e descrição
                // Executa após render para garantir que o elemento esteja dentro do popover
                setTimeout(() => {
                    const pop = info.el.closest('.fc-more-popover');
                    if (!pop) return; // apenas dentro do popover
                    try {
                        const isAllDay = info.event.allDay;
                        let timeStr = '';
                        if (!isAllDay && info.event.start) {
                            try {
                                timeStr = new Intl.DateTimeFormat('pt-BR', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    hour12: false
                                }).format(info.event.start);
                            } catch (e) {
                                const d = info.event.start;
                                const hh = String(d.getHours()).padStart(2, '0');
                                const mm = String(d.getMinutes()).padStart(2, '0');
                                timeStr = `${hh}:${mm}`;
                            }
                        }
                        const title = info.event.title || '';
                        const notes = (info.event.extendedProps && info.event.extendedProps.notes) ? info.event.extendedProps.notes : '';
                        const sep = timeStr ? '<span class="fc-event-time-start"> ' + timeStr + '</span>' : '';
                        const notesLine = notes ? `<div class="fc-event-notes">${notes}</div>` : '';
                        const html = `<div class="fc-event-main-custom fc-popover-rich">
                                    <div class="line1"><span class="fc-event-title">${title}</span>${sep}</div>
                                    ${notesLine}
                                </div>`;
                        const main = info.el.querySelector('.fc-event-main') || info.el.querySelector('.fc-event-main-frame') || info.el;
                        if (main) main.innerHTML = html;
                    } catch (e) {
                        /* noop */
                    }
                }, 0);
                // aplicar filtro de busca para novos elementos
                try {
                    if (typeof applyClientSearchFilter === 'function') applyClientSearchFilter();
                } catch (e) { }
            },
            eventDrop: function (info) {
                // §9.1 Compliance: Converter para UTC antes de enviar
                const allDay = info.event.allDay;
                const start = toUTC(info.event.start, allDay);
                const end = toUTC(info.event.end, allDay);

                fetch(`/api/agenda/events/${info.event.id}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        start: start,
                        end: end
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'success') {
                            alert('Erro ao atualizar evento!');
                            info.revert();
                        }
                    })
                    .catch(() => {
                        alert('Erro ao atualizar evento!');
                        info.revert();
                    });
            },
            eventResize: function (info) {
                // §9.1 Compliance: Converter para UTC antes de enviar
                const allDay = info.event.allDay;
                const start = toUTC(info.event.start, allDay);
                const end = toUTC(info.event.end, allDay);

                fetch(`/api/agenda/events/${info.event.id}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        start: start,
                        end: end
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'success') {
                            alert('Erro ao atualizar evento!');
                            info.revert();
                        }
                    })
                    .catch(() => {
                        alert('Erro ao atualizar evento!');
                        info.revert();
                    });
            }
        });
        calendar.render();
        // Re-render events quando o container muda de largura (para aplicar modo compacto)
        try {
            const measureAndApply = () => {
                const ov = loadCompactOverride();
                if (ov && ov !== 'auto') {
                    __applyCompactLevel(ov);
                } else {
                    __applyCompactLevel(__computeCompactLevel());
                }
            };
            const rerender = rafThrottle(() => { try { measureAndApply(); calendar.rerenderEvents(); } catch (e) { } });
            // Inicializar nível de compacidade logo após o render
            setTimeout(measureAndApply, 0);
            if (window.ResizeObserver && agendaHost) {
                const roCal = new ResizeObserver(() => rerender());
                roCal.observe(agendaHost);
                try { window.__calendarRO = roCal; } catch (_) { }
            } else {
                window.addEventListener('resize', rerender);
            }
            // Também observar a área interna do timeGrid para captar mudanças de coluna
            try {
                const tg = calendarEl && calendarEl.querySelector('.fc-timegrid-body, .fc-timegrid-slots, .fc-scroller-harness');
                if (window.ResizeObserver && tg) {
                    const roTg = new ResizeObserver(() => rerender());
                    roTg.observe(tg);
                    try { window.__calendarLaneRO = roTg; } catch (_) { }
                }
            } catch (e) { /* noop */ }
            // Atualizar nível ao mudar de datas/visão
            try { calendar.on('datesSet', () => { measureAndApply(); }); } catch (e) { }
        } catch (e) { }
        // After main events are loaded/rendered, refresh the mini to consume the cache and rebuild indicators
        try {
            // Simplified: avoid touching the mini from main events to prevent unnecessary re-renders
            calendar.on('eventsSet', () => { /* no-op */ });
        } catch (e) { }

        // ===== Mini calendário (in-card sidebar) =====
    (function initMiniCalendar() {
            try {
                const el = document.getElementById('miniCalendarFallback');
                if (!el || !window.FullCalendar) return;
                // Build a minimal, stable mini month view without dynamic resize logic
                const mini = new FullCalendar.Calendar(el, {
                    locale: 'pt-br',
                    initialDate: calendar.getDate(),
                    initialView: 'dayGridMonth',
                    // Title placed to the right of prev/next within the same chunk; chunk centered via CSS
                    headerToolbar: { left: 'prev,next title', center: '', right: '' },
                    titleFormat: (arg) => {
                        try {
                            // mês/ano em pt-BR e com barra (ex: outubro/2025)
                            const s = arg.date.marker.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
                            return s.replace(' de ', '/');
                        } catch (e) {
                            const d = arg.date.marker; return `${d.getMonth() + 1}/${d.getFullYear()}`;
                        }
                    },
                    height: 'auto', // natural height, no scrollbars
                    fixedWeekCount: true, // always 6 weeks for consistent layout
                    navLinks: false,
                    selectable: false,
                    editable: false,
                    handleWindowResize: false, // avoid auto resize thrash
                    dayHeaderFormat: { weekday: 'narrow' },
                    eventDisplay: 'none', // mini does not render events; keeps rows compact
                    dateClick: (info) => { try { calendar.gotoDate(info.date); } catch (e) { } },
                    // Keep holidays highlight (optional lightweight)
                    dayCellClassNames: function (arg) {
                        try {
                            const key = ymdFromDate(arg.date);
                            const yc = holidaysYearCache[arg.date.getFullYear()];
                            return yc && yc.dates && yc.dates.has(key) ? ['fc-day-holiday'] : [];
                        } catch (e) { return []; }
                    },
                    // When navigating months in mini, navigate main too (one-way)
                    datesSet: function () {
                        try { calendar.gotoDate(mini.getDate()); } catch (e) { }
                    }
                });
                mini.render();
                // Layout helper to keep mini calendar day cells square (6 rows x 7 columns)
                let __miniApplying = false;
                let __miniLast = { w: 0, cell: 0, totalH: 0 };
                const layoutMiniCalendarSquares = rafThrottle(() => {
                    try {
                        if (__miniApplying) return;
                        const host = el;
                        // If widget is hidden (media query or manual), skip layout to avoid thrash
                        const widget = host.closest('.widget-mini-calendar') || host.parentElement;
                        // Auto-hide when the widget becomes too narrow to render squares meaningfully
                        try {
                            const widgetW = widget ? widget.clientWidth : host.clientWidth;
                            if (widgetW > 0 && widgetW < 240) {
                                if (widget && widget.classList) widget.classList.add('auto-hidden');
                                return;
                            } else {
                                if (widget && widget.classList) widget.classList.remove('auto-hidden');
                            }
                        } catch (e) { /* noop */ }
                        if (widget) {
                            const cs = window.getComputedStyle(widget);
                            if (cs && (cs.display === 'none' || cs.visibility === 'hidden')) return;
                            // If not in DOM flow (e.g., offsetParent null), skip
                            if (widget.offsetParent === null) return;
                        }
                        // In mini, FullCalendar often attaches 'fc' class to the host itself
                        const fc = host.classList && host.classList.contains('fc')
                            ? host
                            : host.querySelector('.fc');
                        const harness = host.querySelector('.fc-view-harness');
                        const toolbar = host.querySelector('.fc-toolbar');
                        const header = host.querySelector('.fc-col-header');
                        const body = host.querySelector('.fc-daygrid-body');
                        if (!fc || !harness || !body) return;
                        // Constrain to the mini host width to avoid bleed from the main calendar
                        const availW = Math.max(0, host.clientWidth);
                        if (!availW) return; // hidden or no space
                        // Skip if width/cell/height are already applied to avoid flicker
                        const headerH = header ? Math.ceil(header.getBoundingClientRect().height) : 0;
                        const toolbarH = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;
                        // Derive exact square size from the actual first cell width
                        let cellSize = Math.floor(availW / 7);
                        try {
                            const firstCell = body.querySelector('.fc-daygrid-day');
                            if (firstCell) {
                                const cw = Math.round(firstCell.getBoundingClientRect().width);
                                if (cw > 0) cellSize = cw;
                            }
                        } catch (e) { /* noop */ }
                        const totalH = toolbarH + headerH + (cellSize * 6);
                        // Bail early if nothing relevant changed
                        if (Math.abs(__miniLast.w - availW) <= 1 &&
                            Math.abs(__miniLast.cell - cellSize) <= 1 &&
                            Math.abs(__miniLast.totalH - totalH) <= 1) {
                            return;
                        }
                        __miniApplying = true;
                        // Constrain fc width only if changed
                        try {
                            const currW = Math.round((fc.getBoundingClientRect().width || 0));
                            if (Math.abs(currW - availW) > 1) fc.style.width = availW + 'px';
                        } catch (e) { }
                        // Force exact row heights for 6 weeks and set frame heights to match (visual squares)
                        const rows = body.querySelectorAll('tr');
                        rows.forEach(r => { try { r.style.setProperty('height', cellSize + 'px', 'important'); } catch (e) {} });
                        const frames = body.querySelectorAll('.fc-daygrid-day-frame');
                        frames.forEach(fr => { try { fr.style.setProperty('height', cellSize + 'px', 'important'); } catch (e) {} });
                        // Lock the view height to header + 6 rows of squares (avoid setOption to reduce thrash)
                        harness.style.height = totalH + 'px';
                        harness.style.minHeight = totalH + 'px';
                        __miniLast = { w: availW, cell: cellSize, totalH };
                        __miniApplying = false;
                    } catch (e) { /* noop */ }
                });
                // Expose for debugging/inspection if needed
                try { window.__layoutMiniCalendarSquares = layoutMiniCalendarSquares; } catch (e) { }
                // Initial layout after first render frame
                setTimeout(layoutMiniCalendarSquares, 0);
                // Prefer ResizeObserver over window resize to avoid global thrash
                try {
                    const widget = el.closest('.widget-mini-calendar') || el.parentElement || el;
                    if (window.ResizeObserver && widget) {
                        const ro = new ResizeObserver(() => layoutMiniCalendarSquares());
                        ro.observe(widget);
                        // keep a weak ref for potential future cleanup
                        try { window.__miniRO = ro; } catch (_) { }
                    } else {
                        window.addEventListener('resize', layoutMiniCalendarSquares);
                    }
                } catch (_) {
                    window.addEventListener('resize', layoutMiniCalendarSquares);
                }
                // Re-layout when mini changes month (prev/next)
                mini.on('datesSet', layoutMiniCalendarSquares);
                // Also re-layout when main calendar view dates change (keep in sync visually)
                try { calendar.on('datesSet', layoutMiniCalendarSquares); } catch (e) { }
                // expose for potential future hooks without forcing reflows
                try { Object.defineProperty(window, '__miniCalendar', { configurable: true, get: () => mini }); } catch (e) { }
                // Debug helper: capture mini metrics for E2E and manual diagnostics
                try {
                    window.__getMiniMetrics = function () {
                        try {
                            const host = el;
                            const fc = host.querySelector('.fc');
                            const harness = host.querySelector('.fc-view-harness');
                            const header = host.querySelector('.fc-col-header');
                            const body = host.querySelector('.fc-daygrid-body');
                            const firstFrames = Array.from(host.querySelectorAll('.fc-daygrid-day-frame')).slice(0, 7);
                            const frames = firstFrames.map(fr => {
                                const r = fr.getBoundingClientRect();
                                return { w: Math.round(r.width), h: Math.round(r.height) };
                            });
                            const hr = harness ? harness.getBoundingClientRect() : { width: 0, height: 0 };
                            const br = body ? body.getBoundingClientRect() : { width: 0, height: 0 };
                            const he = header ? header.getBoundingClientRect() : { width: 0, height: 0 };
                            return {
                                exists: !!fc,
                                widgetWidth: (host.closest('.widget-mini-calendar') || host).clientWidth,
                                harness: { w: Math.round(hr.width), h: Math.round(hr.height) },
                                body: { w: Math.round(br.width), h: Math.round(br.height) },
                                header: { w: Math.round(he.width), h: Math.round(he.height) },
                                firstRowFrames: frames
                            };
                        } catch (e) {
                            return { error: String(e && e.message || e) };
                        }
                    };
                } catch (e) { /* noop */ }
            } catch (e) { /* noop */ }
        })();

        // Carregar dentistas e montar sidebar (dedup + TTL cache) antes de qualquer refetch
        fetchDentistsOnce()
            .then(list => {
                // normalizar ids para number
                const norm = Array.isArray(list)
                    ? list.map(d => ({ id: Number(d.id), nome: d.nome, color: d.color || null }))
                    : [];
                dentistsCache.list = norm; // ensure structures are set (no-op if already)
                dentistsCache.map = Object.fromEntries(norm.map(d => [d.id, d]));
                // Preencher o select do popover
                try {
                    const sel = document.getElementById('popoverDentist');
                    if (sel) {
                        // mantém 'Sem dentista'
                        norm.forEach(d => {
                            const opt = document.createElement('option');
                            opt.value = String(d.id);
                            opt.textContent = d.nome;
                            sel.appendChild(opt);
                        });
                        const checkedIds = loadSelectedDentists();
                        if (checkedIds && checkedIds.length === 1) sel.value = String(checkedIds[0]);
                    }
                } catch (e) { }
                // Se não houver seleção salva, selecionar todos por padrão (e só então refazer fetch)
                const saved = loadSelectedDentists();
                let selectionChanged = false;
                if (!saved || saved.length === 0) {
                    try {
                        const newSel = norm.map(d => d.id);
                        saveSelectedDentists(newSel);
                        selectionChanged = true;
                    } catch (e) { }
                }
                renderDentistsSidebar(norm);
                // Refazer fetch apenas se a seleção inicial foi alterada (ex.: primeira execução)
                if (selectionChanged) {
                    try { calendar.refetchEvents(); } catch (e) { }
                }
                updateEmptyFilterNoticeDeb();
                // sincronizar mini calendário após carregar dentistas
                if (selectionChanged) {
                    try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                }
                try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) { }
            })
            .catch(() => {
                const cont = document.getElementById('dentistsContainer');
                if (cont) cont.innerHTML = '<div class="text-danger">Falha ao carregar dentistas.</div>';
            });

        // ===== Configurações / Temas =====
        const settingsMenu = document.getElementById('settingsMenu');
        const searchMenu = document.getElementById('searchMenu');

        function toggleSettingsMenu(anchorEl) {
            if (!settingsMenu) return;
            const isVisible = settingsMenu.classList.contains('is-open');
            if (isVisible) {
                settingsMenu.classList.add('hidden');
                settingsMenu.classList.remove('is-open');
                return;
            }
            // Posicionar próximo ao botão
            const rect = anchorEl.getBoundingClientRect();
            const hostRect = agendaHost.getBoundingClientRect();
            const top = (rect.bottom - hostRect.top) + 6;
            const left = rect.left - hostRect.left;
            settingsMenu.classList.remove('hidden');
            settingsMenu.classList.add('is-open');
            settingsMenu.style.position = 'absolute';
            settingsMenu.style.top = top + 'px';
            settingsMenu.style.left = left + 'px';
            // Inicializar UI de feriados somente ao abrir o menu (lazy)
            try {
                if (typeof initHolidaysUIOnce === 'function') initHolidaysUIOnce();
            } catch (e) { }
            setActiveThemeButton(localStorage.getItem('calendarTheme') || 'default');
            (function () {
                let saved = parseInt(localStorage.getItem('defaultEventDurationMin') || '60', 10);
                if (!isFinite(saved) || saved <= 0 || saved === 15) {
                    saved = 60;
                    try {
                        localStorage.setItem('defaultEventDurationMin', String(saved));
                    } catch (e) { }
                }
                setActiveDurationButton(saved);
            })();
            // compact override active state
            (function () {
                const ov = loadCompactOverride();
                setActiveCompactButton(ov);
            })();
            // weekends active state
            (function () {
                const wk = getWeekendsSetting();
                document.querySelectorAll('#settingsMenu [data-weekends]').forEach(btn => {
                    btn.classList.toggle('active', String(wk) === btn.getAttribute('data-weekends'));
                });
            })();
            // Atualizar status do token somente agora
            try {
                if (window.__fetchAndUpdateTokenBadge) window.__fetchAndUpdateTokenBadge();
            } catch (e) { }
            onNextFrameOutsideClick(settingsMenu, () => {
                settingsMenu.classList.add('hidden');
                settingsMenu.classList.remove('is-open');
            });
        }


        // ===== Busca =====
        const searchStateKey = 'calendarSearchQuery';

        function saveSearchQuery(q) {
            try {
                localStorage.setItem(searchStateKey, q || '');
            } catch (e) { }
        }

        function loadSearchQuery() {
            try {
                return localStorage.getItem(searchStateKey) || '';
            } catch (e) {
                return '';
            }
        }

        function toggleSearchMenu(anchorEl) {
            if (!searchMenu) return;
            const isVisible = searchMenu.classList.contains('is-open');
            if (isVisible) {
                searchMenu.classList.add('hidden');
                searchMenu.classList.remove('is-open');
                return;
            }
            const rect = anchorEl.getBoundingClientRect();
            const hostRect = agendaHost.getBoundingClientRect();
            const top = (rect.bottom - hostRect.top) + 6;
            const left = rect.left - hostRect.left;
            searchMenu.classList.remove('hidden');
            searchMenu.classList.add('is-open');
            searchMenu.style.position = 'absolute';
            searchMenu.style.top = top + 'px';
            searchMenu.style.left = left + 'px';
            // Prefill
            try {
                const inp = document.getElementById('searchQueryInput');
                if (inp) {
                    inp.value = loadSearchQuery();
                    inp.focus();
                    inp.select();
                }
            } catch (e) { }
            onNextFrameOutsideClick(searchMenu, () => {
                searchMenu.classList.add('hidden');
                searchMenu.classList.remove('is-open');
            });
        }

        // Busca server-side: alterna para List e ajusta range para cobrir todos resultados
        function gotoListCoveringResults(qstr) {
            const ids = loadSelectedDentists();
            const includeUn = loadIncludeUnassigned();
            const params = new URLSearchParams({
                q: qstr || '',
                dentists: (ids && ids.length ? ids.join(',') : ''),
                include_unassigned: includeUn ? '1' : ''
            });
            fetch(`/api/agenda/events/search_range?${params.toString()}`)
                .then(r => r.json())
                .then(j => {
                    const countEl = document.getElementById('searchResultsSummary');
                    if (countEl) {
                        const c = j && typeof j.count === 'number' ? j.count : 0;
                        countEl.textContent = qstr ? `${c} resultado(s)` : '';
                    }
                    if (!j || !j.min || !j.max) {
                        // sem resultados: vai para lista da semana atual e refetch com q
                        calendar.changeView('listWeek');
                        calendar.refetchEvents();
                        return;
                    }
                    try {
                        const start = new Date(j.min);
                        const end = new Date(j.max);
                        // Expandir 1 dia para garantir inclusão do fim (end é exclusivo)
                        end.setDate(end.getDate() + 1);
                        // Goto min e trocar para listMonth ou listWeek baseado no span
                        const diffDays = Math.max(1, Math.round((end - start) / 86400000));
                        if (diffDays > 35) {
                            calendar.changeView('listYear');
                        } else if (diffDays > 28) {
                            calendar.changeView('listMonth');
                        } else {
                            calendar.changeView('listWeek');
                        }
                        // O FullCalendar não permite setar range arbitrário em list sem customização,
                        // então navegamos para a data inicial; o refetch com q garantirá somente resultados.
                        calendar.gotoDate(start);
                        calendar.refetchEvents();
                    } catch (e) {
                        calendar.changeView('listWeek');
                        calendar.refetchEvents();
                    }
                })
                .catch(() => {
                    calendar.changeView('listWeek');
                    calendar.refetchEvents();
                });
        }

        function wireSearchMenu() {
            const inp = document.getElementById('searchQueryInput');
            const btn = document.getElementById('btnApplySearch');
            const clr = document.getElementById('btnClearSearch');
            if (inp) {
                inp.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        const qv = inp.value.trim();
                        saveSearchQuery(qv);
                        gotoListCoveringResults(qv);
                    }
                });
            }
            if (btn) btn.addEventListener('click', () => {
                const v = (inp && inp.value || '').trim();
                saveSearchQuery(v);
                gotoListCoveringResults(v);
            });
            if (clr) clr.addEventListener('click', () => {
                saveSearchQuery('');
                if (inp) inp.value = '';
                calendar.refetchEvents();
            });
        }
        wireSearchMenu();
        // Removido: injeção de extraParams em eventSources/events.
        // Motivo: nossa função events() já inclui a query (q) ao montar a URL,
        // e mutar opções em runtime pode causar erros em algumas versões do FullCalendar.

        function setActiveThemeButton(theme) {
            document.querySelectorAll('#settingsMenu [data-theme]').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
            });
        }

        function setActiveDurationButton(mins) {
            document.querySelectorAll('#settingsMenu [data-duration]').forEach(btn => {
                const v = parseInt(btn.getAttribute('data-duration') || '0', 10);
                btn.classList.toggle('active', v === mins);
            });
        }

        function setActiveCompactButton(state) {
            const st = state || 'auto';
            document.querySelectorAll('#settingsMenu [data-compact]').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-compact') === st);
            });
        }

        function applyTheme(theme, persist = true) {
            try {
                const link = document.getElementById('theme-override');
                if (theme === 'default') {
                    link.removeAttribute('href');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { }
                } else if (theme === 'dark') {
                    link.setAttribute('href', '/static/agenda/themes/theme-dark.css');
                    try { document.body.classList.add('theme-dark'); } catch (e) { }
                } else if (theme === 'contrast') {
                    link.setAttribute('href', '/static/agenda/themes/theme-contrast.css');
                    try { document.body.classList.remove('theme-dark'); } catch (e) { }
                }
                if (persist) localStorage.setItem('calendarTheme', theme);
            } catch (e) {
                /* noop */
            }
        }
        // Listeners dos botões do menu de configurações
        document.querySelectorAll('#settingsMenu [data-theme]').forEach(btn => {
            btn.addEventListener('click', () => {
                const t = btn.getAttribute('data-theme');
                applyTheme(t);
                setActiveThemeButton(t);
            });
        });
        // Compact override (debug/testing)
        document.querySelectorAll('#settingsMenu [data-compact]').forEach(btn => {
            btn.addEventListener('click', () => {
                const v = btn.getAttribute('data-compact') || 'auto';
                try { localStorage.setItem('calendarCompactOverride', v); } catch (e) { }
                setActiveCompactButton(v);
                // Apply immediately and rerender
                try {
                    if (v !== 'auto') {
                        __applyCompactLevel(v);
                    } else {
                        __applyCompactLevel(__computeCompactLevel());
                    }
                    calendar.rerenderEvents();
                } catch (e) { }
            });
        });
        // Duração padrão do novo evento (em minutos)
        document.querySelectorAll('#settingsMenu [data-duration]').forEach(btn => {
            btn.addEventListener('click', () => {
                let mins = parseInt(btn.getAttribute('data-duration') || '60', 10);
                if (!isFinite(mins) || mins <= 0 || mins === 15) mins = 60;
                try {
                    localStorage.setItem('defaultEventDurationMin', String(mins));
                } catch (e) { }
                setActiveDurationButton(mins);
            });
        });
        // Weekends toggle (timeGridWeek)
        document.querySelectorAll('#settingsMenu [data-weekends]').forEach(btn => {
            btn.addEventListener('click', () => {
                const val = btn.getAttribute('data-weekends') === 'true';
                setWeekendsSetting(val);
                document.querySelectorAll('#settingsMenu [data-weekends]').forEach(b => {
                    b.classList.toggle('active', b === btn);
                });
                const viewType = calendar.view && calendar.view.type;
                if (viewType && viewType.startsWith('timeGrid')) {
                    calendar.setOption('weekends', val);
                }
            });
        });

        // Re-apply weekends per view dates change
        calendar.on('datesSet', function () {
            const val = getWeekendsSetting();
            calendar.setOption('weekends', val);
            updateHolidaysForCurrentView();
        });
        // prime holidays on initial render
        setTimeout(() => {
            updateHolidaysForCurrentView();
        }, 50);
        // aviso inicial de filtros vazios
        setTimeout(() => {
            updateEmptyFilterNoticeDeb();
        }, 10);
        // ==== Invertexto token and refresh (lazy init) ====
        let __holidaysUIInitialized = false;

        function initHolidaysUIOnce() {
            if (__holidaysUIInitialized) return;
            __holidaysUIInitialized = true;
            const tokenInput = document.getElementById('invertextoToken');
            const yearInput = document.getElementById('holidaysYear');
            const ufInput = document.getElementById('holidaysState');
            const btn = document.getElementById('btnRefreshHolidays');
            const statusEl = document.getElementById('holidaysStatus');
            const clearBtn = document.getElementById('btnClearToken');
            const hardRefreshBtn = document.getElementById('btnHardRefresh');
            const tokenBadge = document.getElementById('tokenStatusBadge');
            if (!tokenInput || !yearInput || !btn) return;
            // Prefill year
            try {
                yearInput.value = String(new Date().getFullYear());
            } catch (e) { }
            // Check if token configured
            function updateTokenBadge(has) {
                if (!tokenBadge) return;
                tokenBadge.textContent = has ? 'Token configurado' : 'Token não configurado';
                tokenBadge.className = has ? 'badge bg-success' : 'badge bg-secondary';
            }

            function fetchAndUpdateTokenBadge() {
                return fetch('/api/agenda/settings/invertexto_token')
                    .then(r => r.json())
                    .then(j => {
                        const has = !!(j && j.hasToken);
                        if (!has) statusEl.textContent = 'Token não configurado.';
                        updateTokenBadge(has);
                    })
                    .catch(() => { });
            }
            // Expor para chamada quando abrir o menu
            window.__fetchAndUpdateTokenBadge = fetchAndUpdateTokenBadge;
            // Save token on blur
            function saveToken(value) {
                const v = (value || '').trim();
                if (!v) return Promise.resolve();
                statusEl.textContent = 'Salvando token...';
                return fetch('/api/agenda/settings/invertexto_token', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        token: v
                    })
                }).then(r => r.json()).then(j => {
                    if (j && j.status === 'success') {
                        statusEl.textContent = 'Token salvo.';
                        tokenInput.value = '';
                        updateTokenBadge(true);
                    } else {
                        statusEl.textContent = 'Falha ao salvar token.';
                    }
                }).catch(() => {
                    statusEl.textContent = 'Erro ao salvar token.';
                });
            }
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    fetch('/api/agenda/settings/invertexto_token', {
                        method: 'DELETE'
                    })
                        .then(r => r.json())
                        .then(j => {
                            if (j && j.status === 'success') {
                                statusEl.textContent = 'Token removido.';
                                updateTokenBadge(false);
                            } else {
                                statusEl.textContent = 'Falha ao remover token.';
                            }
                        })
                        .catch(() => {
                            statusEl.textContent = 'Erro ao remover token.';
                        });
                });
            }
            if (hardRefreshBtn) {
                hardRefreshBtn.addEventListener('click', () => {
                    try { hardRefreshBtn.disabled = true; } catch (e) { }
                    showToast('Limpando cache...', 'warning', 1200);
                    // 1) Clear client caches
                    try {
                        // events cache (in-memory)
                        if (sharedEventsCache) {
                            sharedEventsCache.key = null;
                            sharedEventsCache.start = null;
                            sharedEventsCache.end = null;
                            sharedEventsCache.events = [];
                        }
                    } catch (e) { }
                    try {
                        // dentists cache (localStorage + memory)
                        localStorage.removeItem('dentistsCacheV1');
                        if (typeof dentistsCache === 'object') {
                            dentistsCache.list = [];
                            dentistsCache.map = {};
                        }
                    } catch (e) { }
                    try {
                        // holidays year cache (client)
                        for (const y in holidaysYearCache) delete holidaysYearCache[y];
                        for (const y in holidaysYearPending) delete holidaysYearPending[y];
                    } catch (e) { }
                    // 2) Clear server caches
                    let serverCleared = false;
                    fetch('/api/agenda/cache/clear', { method: 'POST' })
                        .then(r => { if (!r.ok) throw new Error('server'); serverCleared = true; })
                        .catch(() => { /* keep serverCleared=false */ })
                        .finally(() => {
                            // 3) Rebuild UI data
                            try { fetchDentistsOnce().then(list => renderDentistsSidebar(list)); } catch (e) { }
                            try { calendar.refetchEvents(); } catch (e) { }
                            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) { }
                            try { if (typeof updateHolidaysForCurrentView === 'function') updateHolidaysForCurrentView(); } catch (e) { }
                            showToast(serverCleared ? 'Cache limpo e recarregado.' : 'Cache local limpo. Falha ao limpar no servidor.', serverCleared ? 'success' : 'danger', 2500);
                            try { hardRefreshBtn.disabled = false; } catch (e) { }
                        });
                });
            }
            tokenInput.addEventListener('change', () => {
                saveToken(tokenInput.value);
            });
            // Refresh action
            btn.addEventListener('click', () => {
                const year = parseInt(yearInput.value || '0', 10);
                const uf = (ufInput && ufInput.value || '').toUpperCase().trim();
                if (!year || year < 1900) {
                    statusEl.textContent = 'Ano inválido.';
                    return;
                }
                statusEl.textContent = 'Atualizando feriados...';
                const maybeToken = (tokenInput.value || '').trim();
                const doRefresh = () => fetch('/api/agenda/holidays/refresh', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        year: year,
                        state: uf || undefined
                    })
                }).then(r => r.json()).then(j => {
                    if (j && j.status === 'success') {
                        statusEl.textContent = `Atualizado. ${j.count || 0} registros.`;
                        // Invalidate year cache and rebuild for current view
                        for (const y in holidaysYearCache) delete holidaysYearCache[y];
                        for (const y in holidaysYearPending) delete holidaysYearPending[y];
                        try {
                            updateHolidaysForCurrentView();
                        } catch (e) { }
                    } else {
                        const msg = (j && j.message) ? j.message : 'Falha ao atualizar.';
                        statusEl.textContent = msg + (msg.includes('Não autorizado') ? ' Verifique o token e tente novamente.' : '');
                    }
                }).catch(() => {
                    statusEl.textContent = 'Erro ao atualizar.';
                });
                if (maybeToken) {
                    saveToken(maybeToken).then(doRefresh);
                } else {
                    doRefresh();
                }
            });
        }

        // Função para configurar autocompletar nativo
        function setupAutocomplete() {
            const titleInput = document.getElementById('popoverEventTitle');
            const datalist = document.getElementById('namesList');
            let currentTimeout = null;
            let suggestions = [];
            let currentIndex = -1;

            titleInput.addEventListener('input', function () {
                const query = this.value.trim();
                // Limpar timeout anterior
                if (currentTimeout) {
                    clearTimeout(currentTimeout);
                }
                if (query.length >= 1) {
                    // Aguardar 300ms antes de fazer a busca
                    currentTimeout = setTimeout(() => {
                        fetch(`/api/agenda/buscar_nomes?q=${encodeURIComponent(query)}`)
                            .then(response => response.json())
                            .then(nomes => {
                                suggestions = nomes;
                                currentIndex = -1;
                                updateDatalist(nomes);
                            })
                            .catch(error => {
                                console.error('Erro ao buscar nomes:', error);
                                datalist.innerHTML = '';
                                suggestions = [];
                            });
                    }, 300);
                } else {
                    datalist.innerHTML = '';
                    suggestions = [];
                    currentIndex = -1;
                }
            });

            titleInput.addEventListener('keydown', function (e) {
                if (e.key === 'Tab' && suggestions.length > 0) {
                    e.preventDefault();
                    currentIndex = (currentIndex + 1) % suggestions.length;
                    this.value = suggestions[currentIndex];
                }
            });

            function updateDatalist(nomes) {
                datalist.innerHTML = '';
                nomes.forEach(nome => {
                    const option = document.createElement('option');
                    option.value = nome;
                    datalist.appendChild(option);
                });
            }
        }
    });
});
