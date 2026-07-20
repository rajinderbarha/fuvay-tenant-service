# Product Decisions Required — Slice 2F-11

1. **Should technician be excluded from the 3 read routes
   (`agent_timeline`/`provider_timeline`/`provider_notes`), matching its
   exclusion from all 11 mutations?** This slice chose the broader
   `require_staff_or_above` (includes technician) for reads specifically
   because reads are lower-risk and no evidence proves technician must be
   excluded from real-estate lead visibility the way it was excluded from
   lead mutation (no caller evidence either way). Not decided as a hard
   rule — flagged for future product input if real-estate technician
   involvement is ever intended.

2. **Should lead conversion create a downstream customer/booking
   record?** No such linkage exists in this codebase today. Not built
   (out of scope: "do not merge property inquiries with service
   bookings").

3. **Should `is_customer_visible` note-creation be independently
   permission-gated** (e.g., a stricter check before allowing a note to
   be marked customer-visible)? No evidence found either way — not
   changed.

4. **Whether this module's lead-execution capability should ever expand
   into full property/listing/media/offer management** — explicitly out
   of scope for this slice and not a security question; a genuine future
   product-roadmap decision, not addressed here.
