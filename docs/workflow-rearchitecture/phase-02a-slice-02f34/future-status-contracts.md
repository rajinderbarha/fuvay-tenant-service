# Future Status Contracts

Each of Slices 2F-35, 2F-36, and 2F-37 must select exactly one status per
module from this set (unchanged from the N01/geo precedent):

- `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`
- `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`
- `SECURITY_CLOSED_PRIVACY_BLOCKED`
- `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`
- `IMPLEMENTATION_SCOPE_BLOCKED`
- `INCOMPLETE`

Every status must be scoped explicitly to the module it describes — never
implied application-wide, and never implied to cover a Set C or
unassigned-held route.

A batch slice's OWN overall approval-gate status is separate from its
per-module statuses: a batch containing 7 modules may report, for
example, "5 modules `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`, 1
module `SECURITY_CLOSED_PRIVACY_BLOCKED`, 1 module
`IMPLEMENTATION_SCOPE_BLOCKED`" and still reach its own batch-level
`NEXT_...` or completion status truthfully, provided every module's
status is reported honestly and not smoothed into one attractive
headline.

Slice 2F-38 defines its own certification-specific status vocabulary (see
[slice-2f38-certification-contract.md](slice-2f38-certification-contract.md))
since it certifies rather than closes modules.
