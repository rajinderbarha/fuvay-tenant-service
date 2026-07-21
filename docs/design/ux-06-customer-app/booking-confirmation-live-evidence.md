# Booking Confirmation Live Evidence — UX-06 Round 4

**Not reached this round.** The real confirm endpoint was called (see
booking-submission-live-evidence.md) and returned a real, honest failure
(`FINAL_DRAFT_NOT_READY`) rather than a fabricated success. Per Workstream 4's
explicit instruction ("Do NOT display confirmation before backend success"),
`DeepSeekChatScreen.tsx` correctly does not show a confirmation screen in this
state — the real error is surfaced via `flowError` instead (visible in
`r4-12-after-confirm-attempt.png`). No confirmation UI content can be honestly
evidenced until the blocker in booking-submission-live-evidence.md is resolved.
