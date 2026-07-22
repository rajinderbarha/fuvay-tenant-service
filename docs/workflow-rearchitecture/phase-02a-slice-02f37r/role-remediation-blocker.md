# Role Remediation Blocker (preserved, not remediated this slice)

Per Workstream 15, this slice does not remediate either account. Findings
carried forward unchanged from Slice 2C's original investigation
(`docs/workflow-rearchitecture/phase-02a-slice-02c/remediation-decision-register.md`,
`affected-account-investigation.md`, present on the recovered branch):

- `manager@demo-ac-services.local` (role `tenant_manager`, user id
  `72640932-ef3c-4ce5-92a1-6609bff35ee0`): zero logins, zero sessions, zero
  audit activity. Disposition `MANUAL_ROLE_CONFIRMATION_REQUIRED` — a
  plausible candidate mapping to `staff` exists but requires human
  confirmation this investigation cannot supply.
- `readonly@demo-ac-services.local` (role `tenant_readonly`, user id
  `05deaee8-03f2-40f9-8af6-2f21892c075f`): 7 real logins, 7 unrevoked
  sessions. Disposition `MANUAL_ROLE_CONFIRMATION_REQUIRED` — no canonical
  role represents "tenant-side read-only"; this is a genuine product gap,
  not an evidence gap. No later slice's documentation (through 2F-37)
  produced a different, evidence-backed mapping.

No mapping was invented, assumed from the account's email/name, or applied
to seed data, fixtures, or Migration 144 in this slice.
