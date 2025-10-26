# EchoDent UI Optimizer — living doc (temporary)

This short, evolving note tracks UI/UX improvements for Agenda and friends. It focuses on practical fixes, DevTools-first validation, and repeatable checks that keep us fast.

## Why this doc exists

- EchoDent is server-first HTMX + scoped CSS. Visual regressions are best caught in the browser.
- For UI/JS work, prefer Chrome DevTools and CSS analysis over pytest (see `AGENTS.MD §16`).
- MCP agents help us validate quickly:
  - Chrome DevTools MCP: drive the app, resize, drag, take snapshots/screenshots.
  - CSS MCP: analyze CSS for complexity/specificity and spot hot spots.

## Ground rules (EchoDent)

- No inline CSS/JS in templates; scope styles within `.agenda-card`.
- Offline-first; simple, robust layouts; avoid brittle selectors.
- Components styled via tokens (see `global.css`).

## Work items and status

1) Mini calendar header title placement and format
- Goal: Title harmonically to the right of prev/next; format “mês/ano” (e.g., outubro/2025); centered and consistent with the main title.
- What shipped:
  - Mini toolbar unhidden and centered; titleFormat returns “mês/ano”.
  - Height calculation accounts for toolbar, preserving perfect square cells.
  - Verified visually via MCP full-page screenshot and a11y snapshot: heading “setembro/2025” present next to prev/next.
- Status: Done.

2) Narrow viewport robustness (DevTools open / unconventional widths)
- Goal: Agenda remains readable when the viewport narrows; avoid layout breakage.
- What shipped:
  - Compact rendering heuristic in JS, with a debug override in Settings to force Auto/Normal/Compact/Ultra for quick QA.
  - Policy:
    - ultra: time-only for timed events; compact: title-only for timed events; normal: default.
  - ResizeObserver throttled to rerender events on container width changes (e.g., when DevTools opens).
  - Mini calendar layout stabilized; toolbar height considered; content-visibility hints for widgets.
- Validation (MCP-driven):
  - Programmatically reduced body width to 640px; observed week view event labels change to single-time format (“00:00”, “02:00”), confirming compact policy.
  - Note: Automated viewport resize API has a protocol constraint in this sandbox; we used a style-based width reduction to simulate narrow layout.
- Status: Done (first pass). Keep an eye on extremely small widths; consider container queries if we need finer thresholds.

3) All‑day creation via mouse vs 24h timed blocks
- Goal: Selecting on the all‑day row should yield true all‑day events (date-only, exclusive end), not 24h timed blocks.
- What shipped:
  - Guard for full-day selection in timeGrid: if the selection is exactly 00:00 → 00:00 next day (24h), treat it as all-day on the client.
  - When selection is treated as all-day, date-only fields are shown in the popover and the payload uses exclusive end (start: YYYY-MM-DD, end: YYYY-MM-DD of next day).
- Validation (MCP-driven):
  - Direct API creation: POSTed an all‑day event (start: 2025‑10‑22, end: 2025‑10‑23, allDay: true). Server returned `status:201` with `allDay: true` and UTC date midnights — correct storage semantics.
  - UI note: New events without `dentista_id` may be filtered out when only “Dev Dentista” is selected; check the “Todos (sem dentista)” filter to see them.
  - Selection by dragging the all‑day row was attempted; the a11y tree doesn’t expose those cells cleanly in this environment, so automated E2E confirmation of the drag path isn’t deterministic here. Manual local verification recommended (see checklist below).
- Manual check (local, quick):
  - Switch to Semana view; drag across the all‑day row for a single day; ensure the create popover shows date-only fields; save; verify the event renders in the all‑day lane and not as a 24h block.
- Status: Server semantics validated; client safeguard in place; manual drag path to be re‑checked locally.

4) Truncation on tight slots (prefer “10:00” over “10:00 – 13:00”)
- Goal: In constrained widths or short slots, don’t render an ellipsis range; show only the start time.
- What shipped:
  - `eventContent` checks a compact mode predicate; in compact mode it renders only the start time, keeping the line legible.
- Validation (MCP-driven):
  - After narrowing, observed week events display a single time (“00:00”, “02:00”).
- Status: Done (first pass). If we spot specific overflows, we can tune thresholds per view.

## Practical validation scripts (repeatable)

- Narrow mode smoke: In the browser console
  - `document.body.style.width = '640px'; window.dispatchEvent(new Event('resize'));`
  - Expect week view times to condense to single start times.
- All‑day API smoke:
  - POST `{ title, start: 'YYYY-MM-DD', end: 'YYYY-MM-DD', allDay: true }` to `/api/agenda/events`.
  - Reload; ensure “Todos (sem dentista)” is checked to see events with `dentista_id = null`.
- Mini header glance:
  - In the sidebar widget, confirm prev/next + “mês/ano” centered title, with square day cells.

## Debug/ops tips we discovered

- Filters matter: If only “Dev Dentista” is checked, events without `dentista_id` won’t render; toggle “Todos (sem dentista)”.
- Use cache busting when iterating on static assets: set `ASSET_VERSION` before starting the server to avoid stale CSS/JS.
- For E2E UI checks, the all‑day row may not expose clean nodes to the a11y snapshot; prefer manual drag locally to validate the UX.

## CSS hot‑spots (from analyzer)

- File: `app/static/agenda/calendar-theme.css` (~400 LOC, 114 rules, 148 selectors). Scoped to `.agenda-card` with moderate specificity.
- Observations:
  - Many overrides target FullCalendar internals; keep them within `.agenda-card` to avoid global bleed.
  - content-visibility and intrinsic-size hints are used for widget performance — keep these, they help in slow hardware.
  - Consider container queries for future fine-grained compact switches if we need per-region thresholds.

## Next small wins

- Add a tiny “compact mode” visual hint in settings to toggle/preview single-time labels for debugging. (Done)
- Month view: consider hiding end time earlier than week view to reduce clutter in dense weeks.
- Add a non-disruptive log line in dev for selection shape (`allDay`, start/end) to speed up future debugging.

## Compact levels (impl. details)

- Levels: normal | compact | ultra
- Detection:
  - Prefer measuring the width of a timeGrid column; fallback to calendar container width.
  - ultra: <= 105px; compact: <= 180px (column width guidance); normal otherwise.
- Rendering policy:
  - timeGridWeek:
    - ultra: show only start time for timed events (no title), avoiding ellipsis in extreme widths.
    - compact: show title only for timed events (omit time and ranges) to keep context without truncation.
    - normal: default logic (range or start + title per duration).
  - timeGridDay: ultra shows only start time for timed events; otherwise unchanged.
- CSS hardening:
  - Container queries on `.agenda-calendar` shrink toolbar/title sizes and ensure harness can compress without overflow.

## Appendix — Checklist for manual local verification

- Mini header: Title shows as “mês/ano” next to prev/next; cells remain square when navigating months.
- Narrow layout: Open DevTools, shrink viewport; week events render start-only time labels; no broken layout.
- All‑day creation by drag: In week view, drag in the all‑day row for a single day → popover shows date-only; after save, event appears in the all‑day lane.
- Truncation: On tight slots, verify no ellipses in time labels; titles remain readable.

