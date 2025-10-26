# MCP-based visual checks for Agenda (no extra deps)

This project avoids heavyweight E2E test dependencies. For UI validation, we use a lightweight DevTools-driven check and small runtime helpers to assert layout properties (like the mini calendar cells being square).

## What this covers
- Mini calendar day cells are square within ±1px tolerance.
- Agenda page avoids page-level scroll; scrolling is contained within the card.

## How it works
At runtime, `app/static/agenda/app.js` exposes a debug helper:

- `window.__getMiniMetrics()` → returns a JSON snapshot with:
  - `widgetWidth` (mini widget container width)
  - `harness`, `body`, `header` sizes
  - `firstRowFrames` → array of width/height for the first 7 day frames

And a layout trigger (idempotent):

- `window.__layoutMiniCalendarSquares()` → recomputes the mini calendar layout (used by observers and safe to call manually).

## Manual check (Chrome DevTools)
1. Run the app and open `/agenda` in the browser.
2. Open DevTools Console and execute:

```js
// Optionally wait a bit for render
setTimeout(() => console.table((window.__getMiniMetrics && __getMiniMetrics().firstRowFrames) || []), 300);
```

3. Confirm the frames show equal width and height (±1px OK):
   - Example: `{ w: 34, h: 34 }` across the first seven cells.

4. To force a fresh layout (safe, idempotent):

```js
if (window.__layoutMiniCalendarSquares) __layoutMiniCalendarSquares();
```

5. Check page-level scroll containment:

```js
({
  bodyOverflow: getComputedStyle(document.body).overflow,
  body: { h: document.body.scrollHeight, ch: document.body.clientHeight },
  html: { h: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight }
});
```

Expect `bodyOverflow: "hidden"` and body/html heights equal (no page-level scrolling).

## Cache busting during development
Static assets can be cached aggressively by the browser. We inject `asset_v` in templates to allow query-string cache busting. You can set an environment variable before launching the app:

```powershell
$env:ASSET_VERSION = (Get-Date).ToString('yyyyMMddHHmmss'); python run.py
```

This will render static assets like `app.js?v=<ASSET_VERSION>`, ensuring the latest JS/CSS is loaded.

## Notes
- These helpers are dev-friendly and no-op in production flows.
- No inline CSS/JS was added to templates; helpers live in `app.js` and are idempotent.
- If you need more automation, an external agent (like an MCP client) can drive these checks without adding any test dependencies to the repo.
