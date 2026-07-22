# Customer Functional Baseline (UX-08 freeze)

Re-verified this pass via a genuinely fresh WSL install:
**76/76 tests passing, 0 typecheck errors** — matches the UX-07 closure
baseline exactly, confirming no regression at the UX-08 starting commit
(`50fe95b`).

## Preserved functional capabilities (VERIFIED)

- Authentication and session restoration
- Home service discovery (real catalog, no fixtures)
- SmartBot category context handoff from Home (no re-asking a category
  already selected)
- Three conversation languages (English/हिन्दी/ਪੰਜਾਬੀ) via `chatLanguages.ts`
- Real DeepSeek tool orchestration
- Real serviceability checks
- Real server-authoritative standard pricing
- Real bargain pricing path
- Real booking summary and idempotent booking submission
- Real booking list and detail
- Refresh persistence
- Real review submission via the canonical `POST /v1/customer/reviews`
- Theme system: System/Light/Dark modes, AsyncStorage-persisted, no
  startup flash, stability-tested (25/25 + 10/10 + 5/5 repeated runs
  across UX-07 Pass 3c)
- Critical/high accessibility fixes on Home, SmartBot, and bottom
  navigation (1 CRITICAL + 3 HIGH + 7 MEDIUM real findings fixed)

## Explicitly design-replacement pending (NOT a functional failure)

Per the user's explicit direction that the Customer visual design will be
replaced, the following are marked `DESIGN_REPLACEMENT_PENDING`, not
defective:

- Home final visual design
- SmartBot final visual layout
- One-question-at-a-time final presentation polish
- Final category-card appearance
- Final responsive layout (320/360/390/430/768/1024px)
- Final production screenshot matrix

These are functional-contract-preserving, visually-open items — see
`customer-redesign-handoff.md` for the full functional contract each
redesigned screen must honor.

## Known limitations carried forward (see `unsupported-capability-registry.csv`)

- No customer cancellation/rescheduling capability
- `POST /v1/customer/reviews` malformed-input raw 500 (backend-owned,
  frontend-guarded)
- Final authenticated Home/SmartBot Playwright sweep not completed
  (environment blocker: backend unreachable during UX-07 Pass 3f's
  verification window)
