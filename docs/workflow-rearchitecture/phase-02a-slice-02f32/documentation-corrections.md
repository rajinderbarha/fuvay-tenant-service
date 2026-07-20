# Documentation Corrections

## Test-count correction

An earlier compacted conversation summary stated "2289 passed" at one
intermediate checkpoint during Slice 2F-31A's work. This was a transient
in-progress figure (captured after the primary N01 closure edits but
before the WS10 test file and the full cross-slice rebaseline landed), not
a final baseline. This slice's authoritative arithmetic
([test-count-correction.md](test-count-correction.md)) uses the mission's
given 2290 baseline and reconciles forward to 2319 via real node-ID
evidence. No historical document was rewritten to fix this — the
correction is recorded forward, in this slice's own documentation, per the
same historical-immutability discipline established in Slice 2F-31A.

## Held-count correction

Slice 2F-30's documentation described the held registry with a "59"
figure that had not been reconciled against the N01 closures that
happened afterward (in Slice 2F-31). This slice reconciles it to 56
pending, from exact route-key evidence, without modifying the 2F-30 or
2F-27a historical documents themselves.

No other historical slice document required correction.
