# CUSTOMER-L5-10 — Failure Matrix

| Failure | Detection point | Customer impact | Screen state | Message | Retry | Draft reconciliation | Analytics | Log level | Severity |
|---|---|---|---|---|---|---|---|---|---|
| Draft missing/expired/no address/not serviceable/no provider matched | `evaluatePricingPreflight` (reused from CUSTOMER-L5-09) | Cannot reach the tier picker | preflight_failed state | `pricing.preflight.*` (reused keys) | Navigate to AddressSelection | N/A | N/A | N/A | P2 |
| Estimate fetch fails (`HOME_BOOKING_NO_PROVIDER_AVAILABLE`/`PRICE_OPTIONS_UNAVAILABLE`/network) | `useCalculatePriceEstimate` mutation error | Cannot see any tier to choose | estimate_unavailable state | `bargain.unavailableTitle`/`unavailableDescription` | Yes ("Try again") | Draft unaffected | Reused `pricing_calculation_error` (from L5-09's own mutation) | warn | P1 |
| `confirm-price-choice` fails (network/validation) | `useConfirmPriceChoice` mutation error | Chosen tier not confirmed; the customer's tap had no lasting effect | confirm_failed state | `bargain.confirmFailedTitle`/`confirmFailedDescription` | Yes (choose again — safely re-callable) | Draft's `booking_summary` unchanged (backend never partially wrote it — the merge only happens on a fully successful response) | `bargain_offer_submit_error` | warn | P1 |
| `confirm-price-choice` response fails schema validation | `parseConfirmPriceChoiceResult` returns `null` | Same as above — fails closed | confirm_failed state | Same generic copy | Yes | Draft cache untouched | `bargain_offer_submit_failed` (reason: validation) | warn | P1 |
| Duplicate rapid tap on a tier | UI-level `disabled={isConfirming}` guard | No effect — second tap is a no-op while the first is in flight | confirming state (unchanged) | N/A | N/A | Backend's own overwrite-safe semantics mean even a slipped-through duplicate call is harmless (contract-matrix.md) | N/A | N/A | P3 |
| Customer changes their mind after confirming | `changeSelection()` (real, always-available action) | Returns to the tier picker using already-fetched numbers, no new network call | choosing state | N/A (not a failure) | N/A | Next successful `confirm-price-choice` call overwrites the prior tier choice server-side | N/A | info | NOT_APPLICABLE (correct, honest behavior) |
| Draft not owned by the calling customer (theoretical, unreachable via real UI) | Backend draft-ownership check | N/A — no real UI path constructs this | N/A | N/A | N/A | N/A | N/A | N/A | NOT_APPLICABLE |
| Logout/account switch mid-flow | `queryClient.clear()` (CUSTOMER-L5-02 pattern, reused) | Redirected away, no foreign state persists | Redirected to Authentication/BaselineLanding | Existing auth flow copy | N/A | Cache discarded, local `selectedTier` state unmounted | N/A | N/A | NOT_APPLICABLE (correct behavior) |

## Explicitly Not Applicable (per the real backend's confirmed absence)

Rate limiting, attempt exhaustion, cooldown, session expiry, counteroffer
expiry, and estimate-revision-conflict rows from the spec's requested
failure list (§74) are omitted from this matrix — none of them correspond
to any real, reachable backend behavior in this flow (see
`attempt-and-rate-limit-policy.md`/`counteroffer-contract.md`). Including
placeholder rows for them would misrepresent untested, non-existent
behavior as a real, covered failure mode.
