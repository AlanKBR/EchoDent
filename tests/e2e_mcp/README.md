# EchoDent Agenda — Chrome DevTools MCP E2E Suite

This suite defines real-world scenarios and edge cases for the Agenda. It is designed to be executed by an MCP agent with Chrome DevTools capabilities. Each scenario is a JSON file with declarative steps that a runner maps to Chrome DevTools actions (navigate, wait, click, fill, assert).

Note: This repository doesn’t ship a local runner for MCP. Use GitHub Copilot (or your MCP-capable agent) to execute the steps with the built-in Chrome DevTools MCP tools.

## Prerequisites
- App running locally (default): http://localhost:5000
- Test data: run pytest first to ensure DB models and flows are healthy.
- Optional: set baseUrl in `env.local.json` (copy from `env.example.json`).

## How to run (with an MCP-capable assistant)
1. Ensure the Flask app is running.
2. Ask your assistant to execute a scenario file. Example prompts:
   - "Run the MCP E2E scenario tests/e2e_mcp/agenda_smoke.json"
   - "Run all scenarios in tests/e2e_mcp against http://localhost:5000"
3. The assistant should:
   - Read env.local.json or fallback to env.example.json for `baseUrl`.
   - For each step, translate to MCP operations:
     - navigate -> Navigate to URL
     - waitForText -> Wait for the text to appear
     - clickByText -> Take snapshot, find element by text, click
     - fillByPlaceholder/Label -> Take snapshot, find input by placeholder/label, fill
     - setViewport -> Resize page
     - assertNoBodyScroll -> Evaluate JS to compare scrollHeight vs innerHeight
     - assertVisible -> Ensure element found and visible
     - assertChecked/Unchecked -> Evaluate checked state

## Files
- env.example.json — base environment variables for scenarios
- schema.md — step format and mapping to MCP actions
- agenda_smoke.json — basic page rendering and main widgets
- agenda_filters.json — dentist filters, include_unassigned, empty notice
- agenda_events_crud.json — create/update/delete via popovers and context menu
- agenda_search.json — search flow, switch to list view, range coverage
- agenda_holidays.json — settings menu, token badge status, year fetch behavior
- agenda_responsive.json — responsiveness and no global page scroll

## Troubleshooting
- If selectors don’t match: many steps rely on visible labels or button texts used in the UI (pt-BR). Keep the UI language consistent.
- If base URL differs, set `baseUrl` in env.local.json.
- Ensure FullCalendar resources and CSS load locally; the app is offline-first.
