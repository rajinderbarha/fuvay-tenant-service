# Known Limitations — Slice 2F-39

1. **Mounted route census still incomplete** — 261/2320 routes remain
   unclassified, unchanged from 2F-38 (deliberately not this slice's
   priority; see `route-census-reproduction.md`).
2. **Both demo accounts remain unresolved** — no new evidence, no human
   decision received.
3. **Migration 144 remains unproven in PostgreSQL** — no environment
   available.
4. **~15 of the 45 original full-backend failures remain un-fixed**,
   individually dispositioned in `remaining-failure-disposition.csv`:
   most are pre-existing domain-logic fixture drift (service catalog,
   checklist templates, complaint eligibility, quote checklist) unrelated
   to authorization; 2 (`test_versions.py`) reflect frontend package
   version drift from concurrent, unrelated UX work on other branches;
   2 (`test_customer_frontend_02_hardening.py`,
   `test_p0_engine_management_enterprise.py`) are TypeScript-compile
   environment checks; 2 (`test_sprint27_notifications.py` chat-access
   tests) are flagged as *possibly* authorization-adjacent but not
   confirmed or fixed this slice — a genuine open item worth a follow-up
   slice's attention.
5. **Full-backend regression run only once** this slice (not twice),
   given its ~15-25 minute cost.
6. **No dedicated `verify_2f39.py`** with all mission-specified negative
   fixtures was built (see `slice-2f39-verifier-spec.md`).
7. **N01 domain integrity, payments financial integrity, read-path
   privacy gaps** — unchanged, not remediated (out of scope).
