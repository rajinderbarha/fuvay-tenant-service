"""Owner-managed team credentials. Plaintext passwords only leave the generate call."""
import secrets
import uuid

from sqlalchemy import select, text, update

from app.engines.auth.models import PasswordResetToken, User
from app.engines.auth.service import AuthService
from app.engines.auth.utils import hash_password
from app.exceptions import ServiceOSException


def assert_managed_account(account, tenant_id, actor_id):
    if (str(account.tenant_id) != str(tenant_id)
            or account.role not in {"staff", "technician"}
            or str(account.id) == str(actor_id)):
        raise ServiceOSException("TEAM_LOGIN_SCOPE_INVALID", "This login cannot be managed through the team roster.", status_code=403)


async def linked_account(db, member_id, tenant_id, actor_id):
    uid = (await db.execute(text(
        "SELECT user_id FROM provider_team_members "
        "WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL FOR UPDATE"
    ), {"id": str(member_id), "tid": str(tenant_id)})).scalar()
    if not uid:
        return None
    account = (await db.execute(select(User).where(User.id == uid).with_for_update())).scalar_one_or_none()
    if account:
        assert_managed_account(account, tenant_id, actor_id)
    return account


async def set_login_enabled(db, member_id, tenant_id, actor_id, enabled):
    account = await linked_account(db, member_id, tenant_id, actor_id)
    if not account:
        return
    meta = dict(account.meta or {})
    if enabled:
        # Only undo OUR disable. Never reactivate an admin-suspended account
        # or an invitation that has not yet been accepted.
        if meta.get("provider_access_disabled") and account.account_status == "active":
            account.is_active = True
            meta.pop("provider_access_disabled", None)
    else:
        pending_invitation = None
        if not account.is_active and account.account_status == "active":
            pending_invitation = (await db.execute(select(PasswordResetToken.id).where(
                PasswordResetToken.user_id == account.id,
                PasswordResetToken.purpose == "team_member_activation",
                PasswordResetToken.status == "active",
            ).limit(1))).scalar()
        if account.is_active or pending_invitation:
            meta["provider_access_disabled"] = True
        account.is_active = False
        await db.execute(update(PasswordResetToken).where(
            PasswordResetToken.user_id == account.id,
            PasswordResetToken.status == "active",
        ).values(status="revoked"))
        await AuthService(db)._revoke_all_user_sessions(account.id)
    account.meta = meta


async def generate_team_password(db, member_id, tenant_id, actor, request_id, ip_address):
    member = (await db.execute(text(
        "SELECT id, full_name, email, phone, member_type, user_id, status "
        "FROM provider_team_members WHERE id=:id AND tenant_id=:tid "
        "AND deleted_at IS NULL FOR UPDATE"
    ), {"id": str(member_id), "tid": str(tenant_id)})).fetchone()
    if not member:
        raise ServiceOSException("TEAM_MEMBER_NOT_FOUND", "Team member not found.", status_code=404)
    if member.status != "active":
        raise ServiceOSException("TEAM_MEMBER_DISABLED", "Enable this team member before generating a password.", status_code=409)
    email = (member.email or "").strip().lower()
    if not email:
        raise ServiceOSException("TEAM_MEMBER_EMAIL_REQUIRED", "Add an email to use as this member's login ID. No email delivery is needed.", status_code=422)
    account = await linked_account(db, member_id, tenant_id, actor.user_id)
    duplicate = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if duplicate and (not account or duplicate.id != account.id):
        raise ServiceOSException("TEAM_MEMBER_EMAIL_IN_USE", "This email already belongs to another login. Use a unique team member email.", status_code=409)
    if account:
        # Existing login IDs are immutable here: editing a roster email must
        # not silently change the identity of a verified account.
        if account.email.lower() != email:
            raise ServiceOSException("TEAM_LOGIN_EMAIL_MISMATCH", "The profile email differs from the existing login. Restore the login email before resetting its password.", status_code=409)
        if account.account_status != "active" or (account.meta or {}).get("provider_access_disabled"):
            raise ServiceOSException("TEAM_LOGIN_DISABLED", "Restore account access before generating a password. Admin restrictions must be resolved by an administrator.", status_code=409)
        if not account.is_active:
            invitation = (await db.execute(select(PasswordResetToken.id).where(
                PasswordResetToken.user_id == account.id,
                PasswordResetToken.purpose == "team_member_activation",
                PasswordResetToken.status == "active",
            ).limit(1))).scalar()
            if not invitation:
                raise ServiceOSException("TEAM_LOGIN_DISABLED", "An administrator has disabled this login. Ask them to restore access first.", status_code=409)
    else:
        account = User(
            id=uuid.uuid4(), email=email, full_name=member.full_name, phone=member.phone,
            tenant_id=tenant_id, role="technician" if member.member_type == "technician" else "staff",
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            is_active=True, is_verified=False, onboarding_complete=True,
        )
        db.add(account)
        await db.flush()
    account.is_active = True
    account.role = "technician" if member.member_type == "technician" else "staff"
    await db.execute(update(PasswordResetToken).where(
        PasswordResetToken.user_id == account.id, PasswordResetToken.status == "active",
    ).values(status="revoked"))
    result = await AuthService(db, request_id=request_id, ip_address=ip_address).admin_generate_temporary_password(
        actor, account.id, reason="Provider generated team login password", revoke_sessions=True,
    )
    await db.execute(text(
        "UPDATE provider_team_members SET user_id=:uid, username=:email, "
        "password_generated=true, updated_at=now() WHERE id=:id AND tenant_id=:tid"
    ), {"uid": str(account.id), "email": email, "id": str(member_id), "tid": str(tenant_id)})
    await db.commit()
    return {**result, "member_id": str(member_id), "username": email, "access_active": True}
