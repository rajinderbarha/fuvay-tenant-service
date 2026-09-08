# Application correction navigation — 2026-09-08

## Confirmed issue

The public tenant had status `changes_requested` with the note asking for a GST certificate. Continue corrections opened Setup Overview, but the overview rejected the `HOME_SERVICES_CHANGES_REQUESTED` routing destination and redirected to Application Status. The existing Documents URL was accessible, including the GST certificate upload panel.

## Repair

- Allow the changes-requested destination to render the editable overview. Submitted/under-review, activation and active destinations keep their original redirects.
- Add shared correction links to Application Status, Messages & Requests and Setup Overview: documents, setup and review/resubmit.
- Show the admin correction note on Documents, explain the distinction between standard-document progress and requested evidence, and route corrected applications back to Review after uploading.
- Successful document linking refreshes setup progress and shows explicit save feedback. Uploading does not automatically submit the application.
- No backend permissions, lifecycle transitions, required-document policy or migration changes.

## Checks

- Live browser: reproduced the redirect loop and opened Documents → GST registration certificate. No certificate was uploaded and no application was resubmitted.
- Full tenant component suite: 123 passed, including 10 new correction-flow tests.
- Document and admin-handoff backend regressions: 40 passed. Updated the existing handoff test's SQL-result mock and covered `changes_requested` resubmission as well as the initial draft submission.
- New frontend changes require deployment; the existing direct document-upload route is usable now.
