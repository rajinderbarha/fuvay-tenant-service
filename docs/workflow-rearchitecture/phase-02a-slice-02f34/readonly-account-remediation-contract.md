# readonly@demo-ac-services.local Remediation Contract

## Status through this slice

**Untouched.** No inspection, no role change, no session action was
taken on this account during Slice 2F-34 (or any prior slice in this
program). This is deliberate, per explicit repeated instruction across
Slices 2F-32 through 2F-34.

## What Slice 2F-38 must record when it acts

1. Original account role and status (read as-is, not assumed).
2. Active sessions at the time of remediation.
3. The chosen canonical remediation (which of the 10 canonical roles it
   maps to, and why).
4. The authorization effect of the change (what the account could do
   before vs. after).
5. The session-revocation effect (were existing sessions invalidated,
   and how).
6. Audit evidence (a durable record of who/what changed this account and
   when).
7. Rollback evidence (proof the change can be reversed if the demo
   account's expected behavior turns out to depend on its current
   state).

## What this slice (2F-34) does

Nothing beyond restating this contract for Slice 2F-38 to execute. No
file, table row, or session related to this account was read, queried,
or modified this slice.
