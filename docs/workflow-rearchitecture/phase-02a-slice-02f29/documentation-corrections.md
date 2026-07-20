# Documentation Corrections - Slice 2F-29

1. **2F-28 product question resolved.** 2F-28 recorded an open question about
   whether impersonation admits `admin_security`. The code already answers it:
   `AuthService.impersonate` admits `super_admin` only. Recorded in
   `product-decisions-required.md`; 2F-28's document is left as the historical
   record.

2. **2F-28 queue artifact is now point-in-time.** Its 45-route queue was
   correct when written. After this slice the live unprotected set is 33; the
   queue reconciles as `live_unprotected + 12 closed M01 routes == 45`. 2F-28's
   own artifacts were not rewritten; only its live-comparing test assertions
   were reframed.

3. No prior numeric coverage claim is corrected. 214/259 was re-verified at
   slice start and is now 226/259 by this slice's 12 closures.
