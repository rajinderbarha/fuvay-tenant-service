# Product Decisions Required

## 1. Office first-use into provider-internal-turned-customer-visible threads
This slice's rule uses `thread.customer_id is not None` as the gate for
requiring uploader-match. **Question for product**: are there legitimate
provider-internal threads (no `customer_id`) that later become
customer-visible (e.g., a customer is later added as a participant)? If
so, an asset shared into that thread WHILE it was internal-only would
have skipped the uploader-match check, and later customer visibility
could expose it. Current schema has no mechanism to change a thread's
`customer_id` after creation (confirmed absent), so this is currently a
theoretical, not live, concern — flagged for awareness only.

## 2. Granular per-asset replace permission
`_assert_chat_attachment_replace_authority` reuses role + access-scope
(the same `require_owner_or_office_staff_mutation` check used throughout
this series) rather than a dedicated, granular "media:replace" permission
string (no such permission exists in the codebase's `P` class — confirmed
absent). **Question for product/security**: should a dedicated permission
be added in a future slice (not this one — OUT OF SCOPE forbids adding
permissions here) to allow finer-grained control (e.g., only SOME staff
members, not all, can replace chat attachments)?

## 3. Same-tenant unrelated staff without a specific customer relationship
The "Same-tenant unrelated staff without permission denied" requirement
is currently satisfied only via the coarse role+access-scope check — any
non-readonly `staff`/`tenant_owner` in the tenant CAN replace ANY
same-tenant chat attachment, not just ones for customers they have a
specific relationship with. **Question for product**: is this consistent
with the SAME tenant-wide office oversight policy already ratified for
viewing/messaging (2F-18B onward), or should replacement specifically be
narrower?

## 4. Live concurrency verification
No live Postgres instance exists in this environment to run a true
two-session concurrent-claim integration test. **Question for
product/engineering**: should a dedicated live-environment test (following
this codebase's `*Live*` test class convention, matching
`TestChatNotifyLive`/`TestStaffChatLive`/`TestChatTwoWayLive`) be written
in a future slice, to be run in a CI/staging environment WITH a real
database, closing the residual "not independently provable without a
live DB" gap this slice's `concurrent-claim-proof.md` documents?
