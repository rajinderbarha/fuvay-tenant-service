# Known Limitations - Slice 2F-27

1. Single agent cannot establish genuine two-human reviewer independence.
2. Two automated streams share a low-level substrate (guard/AST/request-input
   helpers); a substrate defect would bias both.
3. Automated dual-review over-classifies: 59 add-candidates vs 2 hand-verified.
4. 21 PRODUCT_DECISION_REQUIRED routes need a product owner.
5. Security observations are static-reading only; none executed.
6. Same-population independent validation is exhausted (per 26H WS16).
