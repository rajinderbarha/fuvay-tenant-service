# Provider team skills and login access

## Delivered

- Migration 349 backfills only empty active Home Services skill catalogs. Existing custom skills and retired skills are preserved.
- Admin Categories → Technician Skills offers an idempotent starter-skill action. Providers select from the same active catalog and can refresh it without closing the editor.
- Optional skill loading errors do not block service assignment or erase existing saved skill selections.
- Add Team Member can generate a temporary password after the member is saved. Edit/Manage login can generate or regenerate credentials without resaving unrelated profile fields.
- The one-time result includes the staff login URL, email, and password. It stays in component memory, supports manual copy on HTTP, and is never persisted in browser storage.
- Passwords use the existing audited auth hashing/rotation service. First-login password change is mandatory. Regeneration revokes sessions and old activation/reset tokens.
- Owner-managed enable/disable now updates linked login access as well as the roster. Reactivation retains the existing seat/credit checks; it does not undo administrator account restrictions.
- Offboarding blocks login; generic profile updates cannot bypass access controls. Role changes synchronize the auth role and revoke old sessions.
- Staff login handles temporary-password sessions and returns to staff login after changing the password. The owner login directs team members to their staff app.

## Verification

- 30 targeted Python behavior/contract tests passed.
- Local PostgreSQL integration passed: create linked login, verify real password hash, change password, regenerate, revoke an existing session, disable and restore. The test rolls back all its writes.
- 12 existing tenant login tests passed in the broader run.
- 8 frontend tests passed for creation, regeneration, enable/disable, failure handling, independent skill loading, HTTP copy fallback, and staff login routing.
- Admin and tenant TypeScript checks passed, including the final tenant recheck.
- Migration 349 applied successfully to the local development database.
- A broader legacy static suite still contains five pre-existing assertions for old page wrapper paths, copied technician hours, and outdated readiness expressions. These are not end-to-end failures of this implementation and were not rewritten as part of this task.

## Release

Deploy backend and both frontend changes together and run `alembic upgrade head` on the target server. Live-server browser acceptance is still required after deployment. No live provider password was changed during this task.
