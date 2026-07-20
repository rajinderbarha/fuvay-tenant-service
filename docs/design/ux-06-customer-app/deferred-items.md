# Deferred Items — UX-06 (updated after Round 3)

Following UX-05's disposition vocabulary (KEEP_AND_REDESIGN / API_CONTRACT_REQUIRED /
MOCK_DESIGN_ONLY / NOT_APPLICABLE):

| Item | Disposition | Reasoning |
|---|---|---|
| ~~DeepSeek chat UI navigation wiring~~ | **DONE (Round 3)** | `DeepSeekChatScreen` now the real "AI Assistant" tab |
| ~~Real canonical booking journey~~ | **DONE (Round 3), 9/13 steps proven live** | See round3-runtime-proof-report.md — steps 10-13 blocked by a confirmed test-data gap (no seeded service areas), not code |
| ~~Typed chat booking-state model~~ | **DONE (Round 3)** | `chatBookingState.ts`, reducer-driven, real-payload-only transitions |
| ~~Canonical-ID-not-label enforcement~~ | **DONE (Round 3)** | `canonicalSlugsFor()` + a real test asserting the sent value is never the display name |
| ~~Idempotent booking submission~~ | **DONE (Round 3)** | Real `Idempotency-Key` header, confirmed via `final_records/confirm_router.py` + `idempotency.py` |
| ~~Formal typecheck classification~~ | **DONE (Round 3)** | typecheck-error-classification.md — all 123 errors classified by file:line + root-cause pattern |
| Consolidate 4 overlapping AI/chat screens | KEEP_AND_REDESIGN | `AIChatScreen`/`AIAssistantScreen`/`SmartBotScreen` are now redundant with `DeepSeekChatScreen` — delete or rewire (Pattern B in typecheck-error-classification.md) |
| Fix remaining 123 typecheck errors | KEEP_AND_REDESIGN | See typecheck-error-classification.md's prioritized "next round" list (navigation param-list typing fixes ~26 errors at once; mechanical field-rewiring for the rest) |
| Wire `match-and-price`/`confirm-price-choice` (server-side provider selection + price-tier choice) into the booking flow | KEEP_AND_REDESIGN | Real, confirmed endpoints, deliberately skipped this round in favor of the simpler catalog-default price path to keep the flow provable end-to-end in the time available |
| Use saved addresses (`/v1/customers/me/addresses`) in the booking flow instead of one-off text entry | KEEP_AND_REDESIGN | Real endpoint already wired in `addressApi` since Round 1, just not connected to `DeepSeekChatScreen` yet |
| Typed pipeline-aware view-model/adapter layer | KEEP_AND_REDESIGN | High-value, cheap once remaining screens are stable; not started |
| Customer IA/navigation restructure (5-tab decision) | KEEP_AND_REDESIGN | Audited in Round 2 (see customer-information-architecture.md) — decision on final tab set not yet implemented |
| Light/dark theme, accessibility pass | Not evaluated | `src/styles/theme.ts` exists in the scaffold, not audited |
| Component/screen-level RNTL tests | Not started | 19 lib/context/state-model-level tests exist; no per-screen RNTL tests yet |
| Full booking journey against seeded serviceable test data | Blocked, not started | Needs a dev/staging DB with real `TenantServiceArea` rows — see round3-runtime-proof-report.md |
| Showcase screen inventory | Not started | No showcase screens exist yet in this app |
| Switch AI chat to Sprint 29 engine (`/v1/customer/ai/sessions`) | Not started | A real seeded customer account is now confirmed available (`customer@serviceos.local`) — no longer blocked on credentials, just not done |
| Confirm DeepSeek reply-language compliance live | Not started | Blocked on a real (non-placeholder) `DEEPSEEK_API_KEY` in a test environment — explicitly separate blocker from the booking-journey work, per coordinator instruction |
