# Scenario Schema

Each scenario is a JSON object with:
- name: string
- description: string
- steps: array of step objects

## Step Types

- setViewport
  - width: number
  - height: number

- navigate
  - url: string (can contain ${baseUrl})

- waitForText
  - text: string
  - timeoutMs?: number (default 8000)

- clickByText
  - text: string (exact or contains)

- clickBySelector (fallback)
  - selector: string (CSS)

- fillByPlaceholder
  - placeholder: string
  - value: string

- fillByLabel
  - label: string (visible label text)
  - value: string

- assertVisible
  - text?: string (preferred) OR
  - selector?: string

- assertChecked / assertUnchecked
  - selector: string (input type=checkbox)

- assertNoBodyScroll
  - none (runner should evaluate document.body.scrollHeight <= window.innerHeight + 8)

- delay
  - ms: number

- switchView
  - view: string (e.g., 'listWeek', 'timeGridWeek', 'dayGridMonth')

- calendarGotoDate
  - iso: string (YYYY-MM-DD)

## MCP mapping hints

- setViewport -> mcp_chromedevtool_resize_page
- navigate -> mcp_chromedevtool_navigate_page
- waitForText -> mcp_chromedevtool_wait_for
- clickByText -> mcp_chromedevtool_take_snapshot + find uid by text + mcp_chromedevtool_click
- clickBySelector -> snapshot + resolve uid by role/name/attributes
- fillBy* -> snapshot + mcp_chromedevtool_fill
- assertVisible -> snapshot + check element presence & visibility; or wait_for text
- assertChecked/Unchecked -> evaluate_script with document.querySelector(...).checked
- assertNoBodyScroll -> evaluate_script for scrolling metrics
- switchView -> click button by text (e.g., 'Lista', 'Semana')
- calendarGotoDate -> optional: use mini calendar dateClick by locating the day cell, or use toolbar navigation
