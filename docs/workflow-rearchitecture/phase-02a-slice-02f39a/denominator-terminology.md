# Denominator Terminology — Authoritative Statement

Per review feedback on this slice, every future report in this program
must keep these five terms distinct rather than collapsing them into one
"coverage percentage":

- **Unique mounted paths** — distinct URL path templates, independent of
  HTTP method (not separately counted this slice).
- **Route-method records** — the actual unit this program counts:
  2,320, one per (method, path) combination the live app serves.
- **Confirmed mutations** — route-method records individually proven
  (not merely heuristically flagged) to cause a persistent side effect:
  321 canonical + 2 platform-admin + 9 public/callback + 13 self-service
  = 345 confirmed this slice's classification work, out of the 1,186
  auto-flagged candidates.
- **Canonical tenant/provider mutations** — the specific, narrower
  subset this program's certification denominator tracks: **321**,
  protected, 0 unprotected.
- **Unresolved route-method records** — records with no confirmed
  classification yet: **229**.

## Authoritative current statement

> 321 canonical tenant/provider mutations are protected; 229 additional
> mounted route-method records remain unclassified and are not
> automatically presumed insecure.

This sentence, or an equivalent one preserving the same distinctions,
should be the standard framing in every future slice's summary until the
229 reaches zero.
