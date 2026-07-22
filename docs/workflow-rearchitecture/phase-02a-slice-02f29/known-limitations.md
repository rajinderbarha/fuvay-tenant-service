# Known Limitations - Slice 2F-29

1. **Not live end-to-end.** Authorization proofs use deterministic in-process
   doubles plus live route/dependency/model introspection. No seeded
   two-tenant HTTP transaction or concurrency test was run. Stated plainly in
   `live-database-evidence.md`.

2. **`invite_staff` and cross-tenant email.** An email that exists in another
   tenant is not treated as a conflict; a second user row is created. `User.email`
   carries no unique constraint, so this does not error - but it also means the
   invite path does not disclose foreign-tenant membership. Whether the same
   email may exist in two tenants is a product question, recorded not decided.

3. **Deactivating an already-inactive staff member** succeeds as a no-op
   (`was_active` guards only the usage decrement). Existing behaviour,
   preserved; classified as a state-integrity observation, not a defect.

4. **The `*` registry entry passes key validation.** It cannot widen authority
   through an override (proven by test), but it is accepted as a stored key.

5. **Scope is M01 only.** 33 canonical unprotected routes remain across other
   modules, and 59 held candidates remain unadjudicated.
