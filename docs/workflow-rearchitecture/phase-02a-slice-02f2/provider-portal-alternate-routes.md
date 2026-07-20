# Provider Portal Alternate Route Audit — Workstream 11

## Candidate found: `tenant_engine.portal_router`'s `/v1/tenant/staff/*`
`app.engines.tenant_engine.portal_router` exposes `POST /staff`,
`POST /staff/{id}/deactivate`, `PATCH /staff/{id}/photo`,
`POST /staff/{user_id}/lock`, `/unlock`, `/sessions/revoke-all` — a
DIFFERENT capability from `provider_portal.router`'s `/v1/provider/team-members/*`:

- `tenant_engine.portal_router`'s `/staff/*` operates on real `users` rows
  (`role='staff'`) — actual login/authentication accounts, with session
  lock/unlock/revoke semantics.
- `provider_portal.router`'s `/team-members/*` operates on
  `provider_team_members` rows — a team/technician roster entry with an
  OPTIONAL nullable `user_id` link (confirmed via
  `app/engines/home_service_assignment/staff_model.py`); most roster
  entries likely have no linked login at all (`create_member_login` is an
  unimplemented stub, so no login is ever actually created through this
  router today).

**Disposition: DISCONNECTED** (not a duplicate, not a bypass) — these are
two different data models serving different purposes. No closure action
required. `tenant_engine.portal_router` itself remains globally unprotected
(0/10 access-scope-aware, per Slice 2F's inventory) but is **explicitly out
of scope for this slice** (not `provider_portal.router`) and was not
touched.

## Candidate checked: admin_catalog / service_setup routers
Own platform-wide `master_services` / catalog definitions, not a tenant's
enablement selection — confirmed different capability (see
`offerings-ownership-decision.md`). **Disposition: DISCONNECTED** (different
capability, not an alternate path to the same mutation).

## No immediately exploitable weaker alternate route found
Every capability this module owns (team-member roster, availability,
offerings enablement, per-area coverage, status/onboarding refresh) has
exactly one mounted route family (`provider_portal.router`'s own), with no
other router exposing an equivalent, weaker-guarded path. This module's
approval is not blocked by any alternate-route finding.
