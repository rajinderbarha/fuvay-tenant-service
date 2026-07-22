"""Phase 2A Slice 2C/2D — controlled remediation for users.role values that
are not in the canonical RBAC set (app.core.permissions.ROLE_PERMISSIONS).

Confirmed affected accounts (Slice 2B/2C, live read-only audit):
  - manager@demo-ac-services.local  (role='tenant_manager')  — zero logins,
    zero sessions, zero audit activity ever. Slice 2D's tenant-access-model
    investigation found no safe way to grant this account manager-shaped
    elevated permissions today (StaffPermission per-user overrides are
    schema-complete but never populated into UserContext — see
    docs/workflow-rearchitecture/phase-02a-slice-02d/tenant-access-model.md).
    Disposition: DISABLE_DEMO_ACCOUNT (not a role-capability grant).
  - readonly@demo-ac-services.local (role='tenant_readonly') — 7 real logins,
    7 unrevoked sessions. No safe genuine read-only enforcement exists
    platform-wide today (require_tenant_mutation_permission's access_scope
    guard is only wired into 2 of ~16 tenant mutation routers). Remains
    RETAIN_BLOCKED_PENDING_PRODUCT_DECISION — not touched by this script.

This tool does NOT infer a mapping from role-name similarity. It requires an
explicit --mapping argument naming exactly which user id maps to exactly
which canonical role, and refuses to run if the database contains any
invalid-role account not named in that mapping (so a partial/incomplete
mapping can't silently leave other accounts un-remediated without the
operator noticing).

Usage (dry-run is always the default — this is the safe way to inspect):
    python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
        --mapping <user_id>=<canonical_role> [--mapping <user_id>=<canonical_role> ...]

To actually mutate data, both --apply and --confirm must be passed:
    python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
        --mapping <user_id>=<canonical_role> --apply --confirm

Optional:
    --allow <user_id>    Restrict remediation to only these ids even if other
                         invalid-role accounts exist (still requires --mapping
                         to cover every allowed id).
    --disable <user_id>  Additionally set is_active=false for this user id
                         (must also appear in --mapping, since the DB column
                         still requires a canonical role value regardless of
                         active status). Use for accounts being deactivated
                         rather than granted the mapped role's capabilities —
                         the audit metadata records this distinction
                         explicitly (disabled=true) so it is never confused
                         with an active capability grant.
    --reason "..."       Free-text reason recorded in the audit trail.

Safety properties:
  - Dry-run by default; --apply requires --confirm as a second, independent
    flag (protects against a single flag being set by accident/automation).
  - Every --mapping target is validated against the canonical role list.
  - Platform-scoped roles (super_admin, admin_operations, admin_finance,
    admin_security, admin_readonly) may not be assigned to a tenant-scoped
    account (one with a non-null tenant_id) — this tool refuses that
    combination outright, it is never "explicitly valid" for this script.
  - Refuses to run (in --apply mode) if the database contains an
    invalid-role account not covered by --mapping/--allow, unless that
    account is outside --allow.
  - Wrapped in a single DB transaction; any error rolls back everything.
  - Idempotent: re-running after a successful apply finds zero remaining
    invalid-role accounts for the mapped ids and reports "nothing to do".
  - Revokes every unrevoked session for each changed account (user_sessions
    .revoked_at = now()), forcing reauthentication so a stale JWT (which
    embeds role at issue-time, per Slice 2C's finding) cannot retain the
    old/invalid role after remediation.
  - Writes one auth_audit_logs row per changed account (action_type
    'role.remediation', metadata carries before/after role, disabled flag,
    sessions_revoked count, reason, script version) — the existing,
    canonical audit mechanism, not a new one.
  - Never prints hashed_password, tokens, or session ids.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

SCRIPT_VERSION = "slice-2d-v2"

CANONICAL_ROLES = {
    "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
    "admin_operations", "admin_finance", "admin_security", "admin_readonly",
}
PLATFORM_ROLES = {
    "super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly",
}

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos"
)


def _parse_mapping(raw: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            raise SystemExit(f"Invalid --mapping entry (expected user_id=role): {item!r}")
        user_id, role = item.split("=", 1)
        user_id = user_id.strip()
        role = role.strip()
        try:
            uuid.UUID(user_id)
        except ValueError:
            raise SystemExit(f"Invalid --mapping user id (not a UUID): {user_id!r}")
        if role not in CANONICAL_ROLES:
            raise SystemExit(
                f"Refusing mapping to non-canonical role {role!r} for user {user_id}. "
                f"Canonical roles are: {sorted(CANONICAL_ROLES)}"
            )
        mapping[user_id] = role
    return mapping


async def _find_invalid_role_accounts(conn) -> list[dict]:
    placeholders = ", ".join(f"'{r}'" for r in CANONICAL_ROLES)
    rows = await conn.exec_driver_sql(
        f"SELECT id, email, role, tenant_id, is_active, last_login_at, created_at "
        f"FROM users WHERE role NOT IN ({placeholders})"
    )
    return [
        {
            "id": str(r[0]), "email": r[1], "role": r[2],
            "tenant_id": str(r[3]) if r[3] else None,
            "is_active": r[4],
            "has_logged_in": r[5] is not None,
            "created_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mapping", action="append", default=[], metavar="USER_ID=ROLE",
                         help="Explicit user_id -> canonical role mapping. Repeatable.")
    parser.add_argument("--allow", action="append", default=[], metavar="USER_ID",
                         help="Restrict remediation to these user ids even if other invalid-role accounts exist.")
    parser.add_argument("--disable", action="append", default=[], metavar="USER_ID",
                         help="Additionally deactivate this account (is_active=false). Must also be present in --mapping.")
    parser.add_argument("--apply", action="store_true", help="Mutate data. Requires --confirm too.")
    parser.add_argument("--confirm", action="store_true", help="Second, independent confirmation flag required alongside --apply.")
    parser.add_argument("--reason", default="Phase 2A Slice 2C remediation", help="Reason recorded in the audit trail.")
    args = parser.parse_args()

    mapping = _parse_mapping(args.mapping)
    allowlist = set(args.allow) if args.allow else set(mapping.keys())

    apply_mode = args.apply and args.confirm
    if args.apply and not args.confirm:
        print(json.dumps({"error": "--apply requires --confirm as well; refusing to mutate data with only one flag set."}))
        sys.exit(2)

    engine = create_async_engine(DATABASE_URL)
    result: dict = {
        "mode": "apply" if apply_mode else "dry_run",
        "script_version": SCRIPT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mapping_provided": mapping,
        "changes": [],
        "unmapped_invalid_accounts": [],
        "errors": [],
    }

    async with engine.connect() as conn:
        invalid_accounts = await _find_invalid_role_accounts(conn)
        invalid_by_id = {a["id"]: a for a in invalid_accounts}

        unmapped = [a for a in invalid_accounts if a["id"] not in mapping and a["id"] in allowlist or (a["id"] not in mapping and not args.allow)]
        # Any invalid account not explicitly covered by --mapping is "unmapped".
        # If --allow was given, only report unmapped accounts that are also
        # inside the allowlist scope (accounts outside --allow are
        # deliberately out of scope for this run and not an error).
        if args.allow:
            unmapped = [a for a in invalid_accounts if a["id"] not in mapping and a["id"] in allowlist]
        else:
            unmapped = [a for a in invalid_accounts if a["id"] not in mapping]

        result["unmapped_invalid_accounts"] = unmapped

        if apply_mode and unmapped:
            result["errors"].append(
                "Refusing to apply: invalid-role accounts exist that are not covered by --mapping "
                "(and are within scope). Fails closed on ambiguous/unexpected records per policy."
            )
            print(json.dumps(result, indent=2, default=str))
            await engine.dispose()
            sys.exit(1)

        for user_id, target_role in mapping.items():
            account = invalid_by_id.get(user_id)
            if account is None:
                result["errors"].append(f"user_id {user_id} in --mapping was not found among current invalid-role accounts (already remediated, or never invalid, or does not exist) — skipping (idempotent no-op).")
                continue

            if target_role in PLATFORM_ROLES and account["tenant_id"] is not None:
                result["errors"].append(
                    f"Refusing mapping for {user_id}: target role {target_role!r} is a platform-scoped "
                    f"role but this account has tenant_id={account['tenant_id']} (tenant-scoped). "
                    f"Platform roles must not be assigned to tenant-scoped accounts."
                )
                continue

            if user_id in args.disable and user_id not in mapping:
                result["errors"].append(f"--disable given for {user_id} but it has no --mapping entry; a canonical role is still required even for a disabled account.")
                continue

            result["changes"].append({
                "user_id": user_id,
                "email": account["email"],
                "tenant_id": account["tenant_id"],
                "previous_role": account["role"],
                "new_role": target_role,
                "disable": user_id in args.disable,
                "reason": args.reason,
            })

        if result["errors"] and apply_mode:
            print(json.dumps(result, indent=2, default=str))
            await engine.dispose()
            sys.exit(1)

        if not apply_mode:
            print(json.dumps(result, indent=2, default=str))
            await engine.dispose()
            return

        # ── APPLY: single transaction, audit row per change, rollback on any failure ──
        # (AsyncConnection auto-begins a transaction on the first statement
        # executed above in this same `conn` -- calling conn.begin() again
        # here would conflict with that already-open transaction, so this
        # explicitly commits/rolls back the one autobegun transaction
        # instead of opening a second one.)
        try:
            for change in result["changes"]:
                if change["disable"]:
                    await conn.execute(text(
                        "UPDATE users SET role = :new_role, is_active = false, "
                        "deactivated_at = now(), deactivation_reason = :reason, updated_at = now() "
                        "WHERE id = :id AND role = :prev_role"
                    ), {"new_role": change["new_role"], "id": change["user_id"],
                        "prev_role": change["previous_role"], "reason": change["reason"]})
                else:
                    await conn.execute(text(
                        "UPDATE users SET role = :new_role, updated_at = now() WHERE id = :id AND role = :prev_role"
                    ), {"new_role": change["new_role"], "id": change["user_id"], "prev_role": change["previous_role"]})

                # Session revocation — forces reauthentication so a stale JWT
                # (which embeds role at issue-time) cannot retain the old
                # role/access. Applies regardless of --disable.
                sessions_result = await conn.execute(text(
                    "UPDATE user_sessions SET revoked_at = now() WHERE user_id = :id AND revoked_at IS NULL"
                ), {"id": change["user_id"]})
                change["sessions_revoked"] = sessions_result.rowcount

                await conn.execute(text(
                    "INSERT INTO auth_audit_logs "
                    "(id, actor_id, actor_role, tenant_id, action_type, target_id, target_type, outcome, metadata, created_at, updated_at) "
                    "VALUES (:id, NULL, 'system', :tenant_id, 'role.remediation', :target_id, 'user', 'success', :metadata, now(), now())"
                ), {
                    "id": str(uuid.uuid4()),
                    "tenant_id": change["tenant_id"],
                    "target_id": change["user_id"],
                    "metadata": json.dumps({
                        "previous_role": change["previous_role"],
                        "new_role": change["new_role"],
                        "disabled": change["disable"],
                        "sessions_revoked": change["sessions_revoked"],
                        "reason": change["reason"],
                        "script_version": SCRIPT_VERSION,
                    }),
                })
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

        result["applied"] = True
        print(json.dumps(result, indent=2, default=str))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
