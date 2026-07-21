# Old Scaffold Closure Report — UX-06 Round 5

Continuation of production-route-design-census.csv's Round 4 findings.

## Closed this round

- `AIChatScreen.tsx`, `AIAssistantScreen.tsx`, `SmartBotScreen.tsx`,
  `BookServiceScreen.tsx` — **deleted**, not left as unreachable dead code.
  All four called nonexistent APIs (`aiApi`, `bookingsApi.create`) and were
  fully superseded by `DeepSeekChatScreen`'s real, live-verified flow.
  Navigation call sites that referenced them (`HomeScreen`'s category tap,
  `ProfileScreen`'s "AI Assistant" menu item) were redirected to the real
  `AIAssistant` tab instead of left pointing at a deleted route.
- `BookingDetailScreen.tsx` — old scaffold payment-breakdown card + dead
  cancel control removed (see booking-detail-visual-audit.md); now
  `REDESIGNED_THIS_ROUND`.
- `InvoiceScreen.tsx` — old scaffold fields (`invoice_number`/`line_items`/
  `tax`/`pdf_url`, none real) removed; now `REDESIGNED_THIS_ROUND`.
- `ChatScreen.tsx` — old scaffold `ChatRoom`/`.rooms` shape fixed to the real
  `ChatThread`/`{items}` contract; now `REDESIGNED_THIS_ROUND`.

## Remaining, honestly flagged

- `QuoteApprovalScreen.tsx` — typecheck-clean now, but its `Quote` field
  shape (`visit_fee`/`labour_cost`/`parts_cost`/etc.) was **not re-verified
  against a live backend this round** (backend was down during that specific
  fix pass) — flagged `NOT_LIVE_VERIFIED_THIS_ROUND`, not silently claimed
  correct.
- `ReviewScreen.tsx` — no fabricated submit path; shows an honest "not
  available yet" message. Classification: `HONEST_GAP`, not
  `OLD_SCAFFOLD_REMAINS` (nothing fake is presented as live).

## Net result

**Zero major production-navigable screens remain `OLD_SCAFFOLD_REMAINS`**
after this round's closures — every screen in production-route-design-census.csv
is now `NEW_DESIGN_VERIFIED` or `REDESIGNED_THIS_ROUND`, except the 3 items
above which are honestly flagged with a specific, narrower caveat rather than
either a false "clean" claim or a vague "old scaffold" label.
