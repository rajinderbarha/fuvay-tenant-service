# Admin provider detail verification

## Scope

Home Services provider detail: Overview, Business & Verification, Services & Coverage,
Team & Capacity, Operations, Finance, Quality & Complaints, Documents & Activity.

## Findings and fixes

- Setup completion now reads the same canonical setup overview as the tenant portal.
  A fully configured profile shows 100%; this is not an approval or live-bookability score.
- Bookability uses the actual eligibility checks and requires active enrollment, rather
  than treating discoverability as permission to book. Approval/activation remain separate.
- Documents show current version, upload/review dates, review notes and clear attachment
  names. PDF/image previews open inside an authenticated modal with retry and full-size view.
  Unsupported active file types are refused. Closing the preview cancels pending requests
  and releases the object URL. Review decisions remain in the Onboarding Queue.
- Service configuration warnings count only active, offered services and use tenant setup
  validation. Unoffered drafts no longer appear as missing-price blockers.
- Coverage displays saved business hours, breaks, daily limits and upcoming exceptions.
- The team tab reads the provider-owned roster, including members without login accounts,
  and shows login/assignment status without inventing pending admin staff verification.
- Finance uses live purchased/used/available seats and lists recent technician plan orders
  separately from legacy top-ups and job charges.
- Lifecycle buttons are restricted to applicable enrollment states. Invalid tab URLs fall
  back to Overview. Provider-dependent reads refresh when the provider ID changes.

## Verification

- Inspected all eight tabs on the supplied public provider page before implementing fixes.
  Did not approve, reject, suspend, alter documents or change public provider data.
- All 42 super-admin Vitest tests passed, including 13 focused provider-detail/media tests.
- Four backend mapping/directory tests passed with `RUN_LOCAL_PROVIDER_DETAIL_TEST=1`.
  The integration check calls each detail-tab read service against local PostgreSQL,
  compares completion with tenant setup, checks roster/seat mapping and rolls back.
- Super-admin TypeScript checking passed after the final provider-dependency/label cleanup.

## Release boundary

Changes are local and require deployment of both API and super-admin to affect the public
URL. Updated live browser rendering and real document attachments still require a
post-deployment check. Automated preview tests cover PDF, image, missing attachment,
HTTP error/retry and unsafe MIME rejection. No schema migration is required.
