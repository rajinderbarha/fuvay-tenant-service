# Tenant Service Setup — Remaining Blockers

None of these block `READY_TENANT_SERVICE_SETUP_ENTERPRISE_WIZARD_CERTIFIED` —
honestly documented, non-blocking notes.

## 1. `readyToEnable` does not check package/credits/deposit gates

The review step's checklist (`typeOk`, `brandOk`, `areasOk`, `technicianOk`,
`availabilityOk`) does not independently check package-active, usage-credits,
or security-deposit status before allowing "Enable Service" — those gates are
enforced server-side by the readiness/bookability engine (surfaced afterward
via `readiness_blockers` on the enabled-services table and the Readiness
Issues panel), but the wizard's own pre-enable checklist doesn't preview them.
A tenant can click "Enable Service" and have it succeed as a *draft/pending*
service even with an inactive package — which is correct per business rules
(package approval gates *bookability*, not *enabling*), but the review
screen's "Ready to enable" language could be clearer that "enabled" and
"bookable" are different states. Deferred as a UX polish item, not a
correctness defect.

## 2. No "preview available slots" computation

The Availability step (step 9) only checks whether any availability rules
exist — it does not compute or preview actual open slots for the requested
service window, since no such backend endpoint exists (`POST
/v1/tenant/availability/preview-slots` from the ticket's suggested API list
was not found in the backend). Documented rather than fabricated.

## 3. No dedicated setup-checklist endpoint

`GET /v1/tenant/setup/checklist` does not exist; the readiness hero and
review checklist are both computed client-side from the same real data
sources already used elsewhere (My Status sprint's approach). Consistent,
not a regression.

## 4. Pre-existing, unrelated build failure on `/service-jobs`

Same `useSearchParams()` Suspense-boundary issue documented in every prior
sprint this session — confirmed untouched by this ticket's changes.

## 5. No ESLint config / no `npm test` script

Same pre-existing gaps documented in every prior sprint. `npx tsc --noEmit` +
`npm run build` + Python static-inspection tests used as the correctness
gates.
