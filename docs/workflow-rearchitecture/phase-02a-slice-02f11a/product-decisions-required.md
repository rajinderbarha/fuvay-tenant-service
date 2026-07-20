# Product Decisions Required — Slice 2F-11A

1. **Future technician participation in real-estate leads** — if the
   business ever wants technicians (or a new persona) involved in
   real-estate lead execution or reads, both the mutation guard
   (Slice 2F-11) and the new read guard (this slice) would need explicit,
   evidence-backed re-authorization — not decided or anticipated here.

2. **Future lead-conversion downstream behavior** — whether `convert_lead`
   should ever create a downstream customer/booking record remains
   unaddressed (carried over from Slice 2F-11, unchanged).

3. **Future note-visibility permission granularity** — whether
   `is_customer_visible` note creation should itself be permission-gated
   remains unaddressed (carried over from Slice 2F-11).

4. **Future frontend CRM implementation** — no UI exists for either
   `execution.real_estate_router` or (as far as this slice determined)
   the overlapping parts of `real_estate_lead`; building one is a
   distinct product/design decision, not addressed here.

5. **`real_estate_lead`'s own distinct architecture and authorization
   pattern** (inline `get_current_user(r)` calls instead of `Depends()`)
   — flagged as a candidate for a future dedicated slice, not evaluated
   or judged as correct/incorrect this slice (no capability overlap
   means no security conclusion about it is required here).
