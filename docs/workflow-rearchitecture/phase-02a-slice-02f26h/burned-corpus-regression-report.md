# Burned-Corpus Regression Report — Slice 2F-26H

Development evidence only; approves nothing.

| Corpus | Persona | Direction | Family | Side effect |
|---|---|---|---|---|
| 26D (24) | 24/24 | 24/24 | — | — |
| 26E (24) | 24/24 | 24/24 | — | 23/24 (known manual error: mutating GET recorded PURE_READ) |
| 26F (24) | 24/24 | 24/24 | 24/24 | 24/24 |
| 26G (24) | 24/24 | 24/24 | 24/24 | 24/24 |

**Capability action diverges** from the four pre-repair manual sheets because
those sheets used the old POST→create convention that D-09 removed
(logout→revoke, plan/downgrade→update, unknown POST→abstain). This is the
intended semantic change, not a regression; the stable authority fields above
are unchanged.
