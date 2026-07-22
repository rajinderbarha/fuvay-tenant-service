# Migration 144 Readiness Contract

Migration 144 remains **unapplied** through Slices 2F-34, 2F-35, 2F-36,
and 2F-37. It is reserved exclusively for Slice 2F-38.

## Readiness conditions (all must hold before application)

1. Zero invalid canonical roles remain in any account.
2. Existing invalid sessions (sessions tied to a non-canonical role) are
   resolved.
3. Read-only mutation-enforcement is proven application-wide.
4. Rollback is tested (not merely written — actually executed against a
   non-production copy and confirmed to restore prior state).
5. All seed and fixture data use canonical roles only.
6. Full regression remains green at the moment of application.

## What this slice (2F-34) does

Nothing — Migration 144 is not touched, inspected for content, or
scheduled for application. This document exists only to freeze the
readiness bar for Slice 2F-38, per the mission's explicit instruction
that this slice must not apply or schedule migrations before readiness
proof.
