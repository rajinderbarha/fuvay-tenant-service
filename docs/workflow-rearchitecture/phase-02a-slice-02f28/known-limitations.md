# Known Limitations - Slice 2F-28

1. Module boundaries are derived from router/service/model evidence in this
   repository; a future refactor could invalidate a grouping.
2. Risk scores are hand-assigned 0-3 with evidence, not measured. They order
   the queue; they are not absolute severities. M01 leads on raw risk and on
   priority, so the ordering does not hinge on the weighting choices.
3. The 59 held candidates remain unadjudicated; they are cross-referenced only.
4. The security-observation registry is a summarised carry-forward (9 explicit
   rows plus a carry-forward line covering the remainder), not 37 individually
   expanded rows.
5. This slice selects work only. No authorization behaviour was analysed for
   correctness beyond identifying the gap class.
