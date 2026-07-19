# SSR / Hydration Report

Two layers of real verification, one genuine limitation stated honestly:

1. **`next build` static prerender** — every UX-04/UX-04A route was
   rendered server-side to static HTML during `next build`
   ("Generating static pages") with zero prerender errors. A prerender
   error (as literally happened and was fixed for `/dev/ux-03/
   permission-editor` at UX-04 baseline — see
   `prerequisite-bug-fix-report.md`) would have failed the build outright,
   so a successful build is real evidence the server-render path works for
   every route.
2. **`next start` + curl smoke check** — all 14 route paths (see
   `showcase-route-smoke-report.csv`) returned HTTP 200 with zero
   occurrences of the string "application error" in the served HTML.

**Genuine limitation**: curl-based checks cannot catch a client-side
*hydration mismatch* (server HTML matching but React then throwing during
client hydration/re-render) — that requires a real browser DOM + JS
execution, which was not available in this environment (no headless
browser was installed or run this pass). This is stated honestly per the
task's own instruction rather than claimed as verified. What IS verified:
no server-side render error, and no build-time hydration-adjacent error
(Next.js does catch some class of Server/Client Component boundary issues
at build time, as it did for the `permission-editor` fix) surfaced across
either build run.
