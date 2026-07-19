# Responsive Runtime Report

Real browser evidence: the `mobile` Playwright project (Pixel 7 device
profile — 412x915 logical viewport, mobile UA, touch enabled) loaded all
18 showcase routes with zero console/page errors, same as desktop (see
`browser-smoke-test-report.csv`). `PartsRequestList`'s table and
`booking-list`'s table are NOT wrapped in an explicit horizontal-scroll
container (a real, known gap carried over from UX-04A's
`responsive-operational-behavior.md`) — this pass's browser check
confirms the pages still load and render without a JS error at the mobile
viewport, but does not confirm the table renders without horizontal
overflow/clipping (that would require a visual screenshot diff, not done
this pass). See `desktop-route-evidence.md` / `mobile-route-evidence.md`
for the per-viewport breakdown.
