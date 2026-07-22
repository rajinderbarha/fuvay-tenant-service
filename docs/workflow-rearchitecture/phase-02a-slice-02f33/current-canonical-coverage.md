# Current Canonical Coverage

As of the end of Slice 2F-33:

- **Denominator:** 264 (262 + 2 Set B additions)
- **Protected:** 241 (238 + 1 Set A closure + 2 Set B closures)
- **Unprotected:** 23
- **Canonical hash:** `d4900ce03daa5437`
- **Matrix hash:** `abfa5d030b1cfeee`

This figure will move again as future slices close more routes; it is not
a claim that the whole application is secured — 23 canonical routes
remain unprotected. Scoped to `geo_zone_management` specifically: all 3
in-scope routes (1 Set A + 2 Set B) are now fully closed on
authorization, tenant/object ownership, and privacy grounds. No domain-
integrity or product-policy blocker was found for any of the 3 (see
[geography-hierarchy-integrity-audit.csv](geography-hierarchy-integrity-audit.csv)).
