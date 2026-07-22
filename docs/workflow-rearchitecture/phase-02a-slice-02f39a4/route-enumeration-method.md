# Route Enumeration Method — Slice 2F-39A4

This slice did not re-enumerate mounted routes (the 261-route census
closed in Slice 2F-39A3, unchanged here). Instead, it took the 21 rows
already classified `PRODUCT_DECISION_REQUIRED` in
`../phase-02a-slice-02f39a3/final-route-classification.csv` as its fixed
input list and individually traced each one's router guard, service
method, and (where present) sibling patterns in the same file — full
manual source reads, not the bulk-scanned guard-pattern extraction used
for the original 149-route classification pass.
