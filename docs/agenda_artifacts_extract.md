# Agenda: Artefatos extraídos para migração (EchoDent)

Data: 2025-10-24

Repositório de origem: https://github.com/AlanKBR/agenda (arquivos lidos via raw)

Fontes diretas utilizadas:
- app.js: https://raw.githubusercontent.com/AlanKBR/agenda/master/agenda/static/app.js
- routes.py: https://raw.githubusercontent.com/AlanKBR/agenda/master/agenda/routes.py
- Árvore de assets:
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static/fullcalendar
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static/fullcalendar/plugins
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static/vendor/flatpickr
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static/vendor/flatpickr/l10n
  - https://github.com/AlanKBR/agenda/tree/master/agenda/static/themes


## Modelos SQLAlchemy (Agenda)

Fonte: routes.py

```python
# Models colocados aqui para manter o módulo autocontido
class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start = db.Column(db.String(30), nullable=False)
    end = db.Column(db.String(30), nullable=False)
    color = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.String(500), nullable=True)
    profissional_id = db.Column(db.Integer, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        from dateutil.parser import parse

        try:
            start_dt = parse(self.start)
            end_dt = parse(self.end)
            if len(self.start) == 10 and len(self.end) == 10:
                all_day = True
            elif (
                start_dt.hour == 0
                and start_dt.minute == 0
                and start_dt.second == 0
                and end_dt.hour == 0
                and end_dt.minute == 0
                and end_dt.second == 0
                and (end_dt - start_dt).total_seconds() % 86400 == 0
            ):
                all_day = True
            else:
                all_day = False
        except Exception:
            all_day = False
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "notes": self.notes,
            "allDay": all_day,
            "profissional_id": self.profissional_id,
        }


class AppSetting(db.Model):
    __tablename__ = "app_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(1000), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class Holiday(db.Model):
    __tablename__ = "holidays"
    date = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    level = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(5), nullable=True)
    year = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="invertexto")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "name": self.name,
            "type": self.type,
            "level": self.level,
            "state": self.state,
            "year": self.year,
            "source": self.source,
        }
```

Nota: Não há modelo Usuario no projeto Agenda; o sistema lê “users.db” diretamente via sqlite (sem ORM) quando necessário (e.g., lista de dentistas e validações).


## FullCalendar: inicialização (plugins, handlers, endpoints)

Fonte: app.js

```javascript
// Build plugins dynamically from the global FullCalendar bundle
const plugins = [];
if (window.FullCalendar) {
  if (FullCalendar.dayGridPlugin) plugins.push(FullCalendar.dayGridPlugin);
  if (FullCalendar.timeGridPlugin) plugins.push(FullCalendar.timeGridPlugin);
  if (FullCalendar.listPlugin) plugins.push(FullCalendar.listPlugin);
  if (FullCalendar.interactionPlugin) plugins.push(FullCalendar.interactionPlugin);
  if (FullCalendar.multiMonthPlugin) plugins.push(FullCalendar.multiMonthPlugin);
  if (FullCalendar.scrollGridPlugin) plugins.push(FullCalendar.scrollGridPlugin);
  if (FullCalendar.adaptivePlugin) plugins.push(FullCalendar.adaptivePlugin);
}

const calendarEl = document.getElementById('calendar');

const calendar = new FullCalendar.Calendar(calendarEl, {
  themeSystem: 'bootstrap5',
  locale: 'pt-br',
  initialView: 'timeGridWeek',
  eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
  slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },

  customButtons: {
    prev: { text: '‹', click: () => calendar.prev() },
    next: { text: '›', click: () => calendar.next() },
    prevYear: {
      text: '≪',
      click: () => {
        const d = calendar.getDate();
        calendar.gotoDate(new Date(d.getFullYear(), d.getMonth() - 1, d.getDate()));
      }
    },
    nextYear: {
      text: '≫',
      click: () => {
        const d = calendar.getDate();
        calendar.gotoDate(new Date(d.getFullYear(), d.getMonth() + 1, d.getDate()));
      }
    },
    settings: {
      text: 'Configurações',
      click: function () {
        const btn = calendarEl.querySelector('.fc-settings-button');
        if (!btn) return;
        const wrap = document.getElementById('settingsmenu-container');
        if (wrap && wrap.childElementCount === 0) {
          fetch('/static/settings-menu.html')
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
          document.body.appendChild(wrap);
        }
        if (wrap.childElementCount === 0) {
          fetch('/static/search-menu.html')
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

  views: {
    dayGridMonth: { eventDisplay: 'block' },
    multiMonthYear: {
      type: 'multiMonth',
      duration: { years: 1 },
      multiMonthMaxColumns: 3,
      eventDisplay: 'block',
      buttonText: 'Ano'
    }
  },

  plugins: plugins,

  dayCellClassNames: function (arg) {
    const iso = toLocalISO(arg.date);
    return holidayDates.has(iso) ? ['fc-day-holiday'] : [];
  },

  dayCellDidMount: function (arg) {
    const iso = toLocalISO(arg.date);
    if (!dayCellEls[iso]) dayCellEls[iso] = [];
    dayCellEls[iso].push(arg.el);
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

  // Conteúdo de evento customizado por view (sem dependências externas)
  eventContent: function (arg) {
    // ... (lógica de renderização específica das views timeGridWeek/timeGridDay/list/dayGridMonth/multiMonth)
    // Nota: omiti aqui apenas o HTML gerado, sem endpoints, para caber neste trecho. Está idêntico no arquivo fonte.
  },

  // Carregamento de eventos do servidor (com cache cliente e filtros)
  events: function (fetchInfo, success, failure) {
    try {
      const key = buildCacheKey();
      const override = (typeof window !== 'undefined') ? window.__fetchMonthOverride : null;
      const focus = (override && override.start) ? new Date(override.start) : new Date(fetchInfo.start);
      const monthStart = new Date(focus.getFullYear(), focus.getMonth(), 1);
      const monthEnd = (override && override.end) ? new Date(override.end) : new Date(focus.getFullYear(), focus.getMonth() + 1, 1);
      const padStart = new Date(monthStart); padStart.setDate(padStart.getDate() - 7);
      const padEnd = new Date(monthEnd); padEnd.setDate(padEnd.getDate() + 7);
      const covStart = startOfDay(padStart);
      const covEnd = startOfDay(padEnd);
      const dedupKey = `${key}|${covStart.toISOString()}|${covEnd.toISOString()}`;

      if (cacheCoversRange(padStart, padEnd, key)) {
        const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
        success(result);
        try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) {}
        try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) {}
        return;
      }

      if (pendingEventsFetches.has(dedupKey)) {
        pendingEventsFetches.get(dedupKey)
          .then(() => {
            const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
            success(result);
            try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) {}
            try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) {}
          })
          .catch(err => {
            if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
            else success([]);
          });
        return;
      }

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

      const p = fetch(`/events?${params.toString()}`)
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(list => {
          storeEventsToCache(Array.isArray(list) ? list : [], covStart, covEnd, key);
          const result = eventsFromCache(new Date(fetchInfo.start), new Date(fetchInfo.end), key);
          success(result);
          try { if (window.__miniCalendar) window.__miniCalendar.refetchEvents(); } catch (e) {}
          try { if (window.__rebuildMiniIndicators) window.__rebuildMiniIndicators(); } catch (e) {}
        })
        .catch(err => {
          if (typeof failure === 'function') failure(err instanceof Error ? err : new Error('Failed to load events'));
          else success([]);
        })
        .finally(() => { try { pendingEventsFetches.delete(dedupKey); } catch (e) {} });

      pendingEventsFetches.set(dedupKey, p);
    } catch (e) {
      if (typeof failure === 'function') failure(e instanceof Error ? e : new Error('Unexpected error'));
      else success([]);
    }
  },

  // Criação rápida com popover; envia POST /add_event
  select: function (info) {
    // ... (UI e inputs)
    const form = document.getElementById('eventPopoverForm');
    form.onsubmit = function (e) {
      e.preventDefault();
      // ... coleta de campos + regras allDay/fim exclusivo
      fetch('/add_event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, start, end, notes, profissional_id: selDent })
      })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success' && data.event) {
          try {
            calendar.addEvent(data.event);
            addEventToCache(data.event);
            // ...
          } catch (e) { calendar.refetchEvents(); }
          // close popover
        } else {
          alert('Erro ao adicionar evento!');
        }
      });
    };
    calendar.unselect();
  },

  // Detalhe com ações: update color/notes/dentist e delete (endpoints POST abaixo)
  eventClick: function (info) {
    // Notas: POST /update_event_notes
    // Dentista: POST /update_event (profissional_id)
    // Deletar: POST /delete_event
    // Cor: POST /update_event_color
    // ... (UI, toasts, ajustes de cache)
  },

  // Drag & drop: POST /update_event
  eventDrop: function (info) {
    let start = info.event.startStr;
    let end = info.event.endStr;
    if (info.event.allDay) {
      if (start && start.length > 10) start = start.slice(0, 10);
      if (end && end.length > 10) end = end.slice(0, 10);
    }
    fetch('/update_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: info.event.id, start, end })
    })
    .then(r => r.json())
    .then(d => { if (d.status !== 'success') { alert('Erro ao atualizar evento!'); info.revert(); } })
    .catch(() => { alert('Erro ao atualizar evento!'); info.revert(); });
  },

  // Resize: POST /update_event
  eventResize: function (info) {
    let start = info.event.startStr;
    let end = info.event.endStr;
    if (info.event.allDay) {
      if (start && start.length > 10) start = start.slice(0, 10);
      if (end && end.length > 10) end = end.slice(0, 10);
    }
    fetch('/update_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: info.event.id, start, end })
    })
    .then(r => r.json())
    .then(d => { if (d.status !== 'success') { alert('Erro ao atualizar evento!'); info.revert(); } })
    .catch(() => { alert('Erro ao atualizar evento!'); info.revert(); });
  }
});

calendar.render();
```

Endpoints referenciados pelo app.js:
- GET /events
- GET /events/search_range
- POST /add_event
- POST /update_event
- POST /delete_event
- POST /update_event_color
- POST /update_event_notes
- GET /dentists
- GET /buscar_nomes
- GET /buscar_telefone
- GET /holidays/year
- POST /holidays/refresh
- GET /holidays/range
- POST /cache/clear (usado no “hard refresh” do cache lado servidor, se existir a rota)
- GET/POST/DELETE /settings/invertexto_token

Obs.: O app.js também busca parciais HTML locais:
- /static/event-popover.html
- /static/event-contextmenu.html
- /static/event-detail-popover.html
- /static/settings-menu.html
- /static/search-menu.html


## Rotas Flask consumidas pelo app.js

Fonte: routes.py

Assinaturas e função-alvo:

- GET / → index() → renderiza “calendar.html”
- GET /events → get_events() → filtros por dentistas, intervalo, include_unassigned e busca; retorna eventos via CalendarEvent.to_dict()
- GET /events/search_range → events_search_range() → com filtros (idem) e busca “q”; retorna min/max/count
- POST /add_event → add_event() → normaliza/valida datas (all-day vs horário), cria CalendarEvent e retorna o evento criado
- POST /delete_event → delete_event() → remove evento por id
- POST /update_event → update_event() → atualiza start/end e/ou profissional_id
- POST /update_event_color → update_event_color() → atualiza cor do evento
- POST /update_event_notes → update_event_notes() → atualiza notes do evento
- GET /dentists → listar_dentistas() → lê users.db via sqlite, retorna [{id, nome, color?}] com ETag/Cache-Control
- GET /pacientes → listar_pacientes() → lê pacientes.db via SQLAlchemy engine
- GET /buscar_nomes → buscar_nomes() → autocompletar de nomes (prefix/contains) em pacientes.db
- GET /buscar_telefone → buscar_telefone() → retorna celular por nome (exact/like)
- GET/POST/DELETE /settings/invertexto_token → invertexto_token() → gerencia token (GET não expõe token)
- POST /holidays/refresh → holidays_refresh() → consulta API Invertexto, substitui dados do ano e invalida cache
- GET /holidays/range → holidays_in_range() → feriados no intervalo (cache em memória + TTL)
- GET /holidays/year → holidays_by_year() → feriados por ano (cache em memória + TTL)

Observações:
- Múltiplos bancos via arquivos em instance_path: users.db e pacientes.db (sem FKs)
- Caches em memória: _HOLIDAYS_YEAR_CACHE, _HOLIDAYS_RANGE_CACHE (TTL = 1h)
- Parse/normalização de datas aceita BR/ISO; all-day com fim exclusivo (dia seguinte)


## Inventário de assets estáticos (Agenda)

Diretório base: agenda/static

Arquivos JS:
- agenda/static/app.js
- agenda/static/bootstrap.bundle.min.js
- agenda/static/fullcalendar/fullcalendar.global.min.js
- agenda/static/fullcalendar/plugins/adaptive.global.min.js
- agenda/static/fullcalendar/plugins/daygrid.global.min.js
- agenda/static/fullcalendar/plugins/interaction.global.min.js
- agenda/static/fullcalendar/plugins/list.global.min.js
- agenda/static/fullcalendar/plugins/multimonth.global.min.js
- agenda/static/fullcalendar/plugins/premium-common.global.min.js
- agenda/static/fullcalendar/plugins/resource.global.min.js
- agenda/static/fullcalendar/plugins/resource-timeline.global.min.js
- agenda/static/fullcalendar/plugins/scrollgrid.global.min.js
- agenda/static/fullcalendar/plugins/timegrid.global.min.js
- agenda/static/fullcalendar/plugins/timeline.global.min.js
- agenda/static/vendor/flatpickr/flatpickr.min.js
- agenda/static/vendor/flatpickr/l10n/pt.js
- agenda/static/vendor/flatpickr/l10n/pt.min.js

Arquivos CSS:
- agenda/static/bootstrap.min.css
- agenda/static/calendar-theme.css
- agenda/static/vendor/flatpickr/flatpickr.min.css
- agenda/static/themes/theme-dark.css
- agenda/static/themes/theme-contrast.css

Parciais HTML:
- agenda/static/event-popover.html
- agenda/static/event-contextmenu.html
- agenda/static/event-detail-popover.html
- agenda/static/settings-menu.html
- agenda/static/search-menu.html


## Notas de migração rápida para EchoDent

- Modelos: em EchoDent, padronizar DateTime(timezone=True) e UTC-aware; os modelos do Agenda usam strings e datetime.utcnow() em settings/holidays. Ao portar, adequar à Seção 6/9 do AGENTS.MD.
- Rotas/UI: manter hipermídia-first e fragmentos HTMX; app.js usa fetch JSON e HTML parciais locais, que podem ser servidos por EchoDent via `app/templates/...` e `app/static/...`.
- Fluxo financeiro: Agenda não toca no “Fluxo de Ouro”; integração é somente com agendamento (sem finanças).
- Multi-bind: já alinhado ao padrão EchoDent (users.db e pacientes.db como binds externos, sem FKs).

---

Este arquivo documenta os artefatos necessários para a junção (lift-and-shift) do módulo Agenda no EchoDent, preservando fidelidade às rotas, dados e UI do projeto de origem.
