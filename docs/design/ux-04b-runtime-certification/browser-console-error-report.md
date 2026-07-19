# Browser Console Error Report

`browser-tests/smoke.spec.ts` attaches `page.on("console", ...)` and
`page.on("pageerror", ...)` listeners on every one of the 18 showcase
routes, across all 3 Playwright projects (54 route-loads total). **Zero
console errors and zero page errors were recorded on any route in any
project.** This is a real, executed check (not a static assumption) — the
assertion literally fails the test if any error is captured, and none
were.
