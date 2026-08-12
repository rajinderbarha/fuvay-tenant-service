# ServiceOS tenant account creation and business setup audit

Date: 2026-08-11  
Scope: audit only; no application source files changed  
Environment: local tenant portal (`localhost:3001`), API (`localhost:8000`), PostgreSQL and Redis

## Verdict

The flow is not release-ready. A new tenant can be created through the API and can reach an authenticated workspace, but the browser flow is blocked at contact verification in the local environment, the completed signup redirects to the general dashboard instead of business setup, and signup business data is not carried into the setup profile.

## Release blockers

1. **OTP response contract is incompatible with the UI.** The API returns `dev_otp_mobile` and `dev_otp_email`; the UI expects a nested `dev_otps` object. With delivery disabled locally, no codes are delivered or displayed, so the user cannot proceed without test-only intervention. Evidence: [04-register-verify-contact.png](04-register-verify-contact.png).
2. **The post-signup handoff is wrong.** Workspace completion lands at `/dashboard`, where a seven-step product tour opens over an empty operations dashboard. The promised next action is vertical setup. Evidence: [12-post-signup-destination.png](12-post-signup-destination.png).
3. **Signup data is lost between flows.** Business name, city, state and description are entered during signup, but the setup profile only retains name/email/phone; business type and registered address are blank. The two flows read/write different database locations. Evidence: [07-register-business-identity-filled.png](07-register-business-identity-filled.png) and [14-setup-business-profile.png](14-setup-business-profile.png).
4. **Terms and privacy links are dead.** `/terms`, `/privacy`, `/legal/terms`, and `/legal/privacy` all return 404, including links adjacent to required consent.
5. **Consent is recorded too early.** The owner-account request sends required consent flags before the user reaches or selects the consent controls on step 5. This makes the recorded consent chronology unreliable.

## High-severity findings

- Account copy says the workspace login is issued after approval, but the account and workspace are created immediately and the user is logged in. Evidence: [01-register-owner-account.png](01-register-owner-account.png).
- Validation alerts remain visible after fields or required checkboxes are corrected. Evidence: [03-register-account-filled.png](03-register-account-filled.png) and [11-register-review-ready.png](11-register-review-ready.png).
- Setup overview says `0 of 5 required sections`, while review says `0 of 6 sections`; staff is marked complete with zero team members (`0 of 0 ready`). Evidence: [13-setup-overview.png](13-setup-overview.png), [18-setup-staff.png](18-setup-staff.png), and [20-setup-review.png](20-setup-review.png).
- The authenticated experience emits three failed API responses: credit wallet 404, reviews 403, and direct payments 403. These produce browser console errors and can leave dashboard/setup data incomplete.
- Existing-account recovery can advance without a registration ID, leaving the browser in an unrecoverable intermediate state.
- Document upload validation does not verify file signatures, so extension/MIME checks alone can be bypassed.

## Flow health

| Step | Health | Finding |
|---|---|---|
| Owner account | At risk | Clear layout, but misleading approval copy, stale validation, premature consent, and duplicate keyboard focus on Sign in. |
| Verify contact | Blocked | No delivered or visible development OTP; contract mismatch requires intervention. |
| Business identity | At risk | Visually usable, but the collected profile data is not reused by setup. |
| Select vertical | Usable | Choice is clear; cards use emoji instead of the product icon system. |
| Review and consent | Blocked for release | Dead legal routes, stale alert, inaccurate `Submit for review` wording, and unreliable consent timing. |
| Workspace handoff | Broken | Redirects to `/dashboard`, not the selected vertical's setup. |
| Setup overview | At risk | Strong lifecycle model; required-section counts and staff status are inconsistent. |
| Business profile | Broken continuity | Contact fields survive; city/address/description do not. Two selects lack accessible names. |
| Documents | Correctly gated | Explains the dependency on business profile clearly; page has no H1. |
| Services and pricing | At risk | Clear hierarchy, but one unlabeled control and unclear `Publish now` action during pre-review setup. |
| Coverage and availability | At risk | Useful readiness feedback, but eight controls are unlabeled for assistive technology. |
| Staff and technicians | Incorrect status | Empty state is clear, but zero staff is treated as complete elsewhere. |
| Finance readiness | At risk | Policy explanation is useful; two unnamed buttons, two unlabeled controls, and a failed wallet request. |
| Review and submit | Correctly blocked, inconsistent | Blockers are easy to scan, but the six-section count conflicts with overview's five-section model. |
| Mobile | At risk | No document-level horizontal scroll was measured, but signup stays two-column and clips content, while the lifecycle tracker hides later stages. The signup step rail also pushes the form far below the fold. |

## Accessibility audit

Automated axe checks were run on 12 representative states. This is not a complete WCAG conformance assessment.

- Serious color-contrast failures appear on every audited page (4 to 26 nodes per state).
- Registration states lack a `main` landmark and H1, with 16 to 20 content regions outside landmarks.
- Setup overview has an unnamed ARIA progressbar.
- Business profile has two critical unnamed selects.
- Services/pricing has one critical unlabeled control; coverage has eight.
- Finance has two critical unnamed buttons and two critical unlabeled controls.
- Keyboard inspection found two successive `Sign in` tab stops because a link wraps a button.

## Test evidence

- Signup backend tests: **15 passed**.
- Combined login/handoff tests: **15 passed, 11 failed**.
- Setup-focused regression tests: **98 passed, 6 failed**.
- TypeScript compilation: **passed**.
- Frontend Vitest: runner hung even on a single onboarding test, so frontend unit-test reliability is itself unresolved.
- Playwright audit: **22 screenshots captured and individually inspected**, 12 axe states, desktop and mobile coverage, legal-link checks, failed-response capture, and console-error capture.
- Database/services: PostgreSQL and Redis healthy; live API created the tenant, owner, vertical enrollment, consent rows and authenticated session.

## What works well

- The visual system is consistent and professional across signup and setup.
- Progress, verification success, lifecycle state, blockers, and dependencies are generally easy to scan.
- Setup screens use strong progressive disclosure and explain why information is needed.
- Desktop spacing and hierarchy are good, and the mobile pages do not create document-level horizontal scrolling.

## Recommended implementation order

1. Repair OTP and completion response contracts, then redirect directly to `/tenant/{vertical}/setup/overview`.
2. Define one canonical business-profile persistence model and prefill setup with signup data.
3. Move consent writes to the final consent action and ship real legal pages/routes.
4. Reconcile required-section/status rules, especially staff and the 5-versus-6 count.
5. Fix critical/serious accessibility findings and mobile clipping.
6. Repair failed authenticated API calls and stabilize the frontend test runner; then add a clean-room Playwright happy path plus negative and resume paths.

## Artifacts

- Raw browser/a11y/API results: [audit-results.json](audit-results.json)
- Reproducible Playwright audit: [run-audit.mjs](run-audit.mjs)
- Screenshots: `01` through `22` in this directory

The audit created local test tenant `visual.audit.1786458844768@example.com`. It was retained because this was an audit-only pass and no destructive cleanup was authorized.
