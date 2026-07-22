# Product Decisions Required — Slice 2F-3B

## 1. Should the dead `staff_accept_job`/`staff_reject_job` functions eventually be deleted?
Preserved this slice per the brief's explicit instruction. A future
cleanup slice, if separately approved, could remove them with a proper
justification (e.g. confirmed zero internal callers over a longer
observation window) — not decided or done here.

## 2. Should `reassign_job`/`cancel_assignment`/`schedule_job`'s ownership mechanisms receive a dedicated audit?
Not independently re-verified line-by-line this slice (only the
access-scope guard was added). If a future incident or review raises
concerns, this is the next place to look — flagged, not resolved.

## 3. Should `provider_install_parts_request`'s exact provider-only mechanism be re-documented?
Confirmed unchanged, not re-traced end-to-end. If a future slice touches
Parts installation, this is worth clarifying precisely (role check?
permission? assignment-derived identity?) rather than continuing to treat
it as an unexamined black box.

## 4. Should staff/technician be granted a formal permission (vs. role-only access) for execution actions?
This slice deliberately used a role-based composed guard
(`require_staff_or_above_mutation`), not a new granular permission, per the
brief's "do not grant broad permissions merely to make actions accessible."
If finer-grained delegation (e.g. a specific staff member allowed only
some execution actions, not others) is ever wanted, that would require a
new permission scheme — not decided or built here.
